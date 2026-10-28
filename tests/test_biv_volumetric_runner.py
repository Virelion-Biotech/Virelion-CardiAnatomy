from __future__ import annotations

import hashlib
import json
from pathlib import Path

import meshio
import nibabel as nib
import numpy as np
import pytest

from cardianatomy.biv_volumetric import run_biv_volumetric_pipeline
from cardianatomy.biv_volumetric_cli import main as biv_volumetric_cli_main
from cardianatomy.integrations.commands import CommandResult, biv_volumetric_command


def make_inputs(root: Path) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    views = {}
    for key in ("SAX", "LAX_2CH", "LAX_3CH", "LAX_4CH"):
        path = root / f"{key}.nii.gz"
        nib.save(nib.Nifti1Image(np.zeros((6, 7, 8, 3), dtype=np.uint8), np.eye(4)), path)
        views[key] = path
    return views


def make_upstream(root: Path) -> Path:
    source = root / "upstream"
    (source / "src").mkdir(parents=True)
    (source / "src" / "run.py").write_text("# upstream test stub\n", encoding="utf-8")
    return source


def write_mesh(path: Path, *, tiny: bool = False) -> None:
    if tiny:
        points = np.array(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        )
        tetrahedra = np.array([[0, 1, 2, 3]], dtype=int)
    else:
        size = 10
        coords = np.stack(
            np.meshgrid(
                np.arange(size), np.arange(size), np.arange(size), indexing="ij"
            ),
            axis=-1,
        )
        points = coords.reshape(-1, 3).astype(float)

        def node(i, j, k):
            return (i * size + j) * size + k

        pattern = (
            (0, 1, 3, 7),
            (0, 3, 2, 7),
            (0, 2, 6, 7),
            (0, 6, 4, 7),
            (0, 4, 5, 7),
            (0, 5, 1, 7),
        )
        tetrahedra_list = []
        for i in range(size - 1):
            for j in range(size - 1):
                for k in range(size - 1):
                    cube = (
                        node(i, j, k),
                        node(i + 1, j, k),
                        node(i, j + 1, k),
                        node(i + 1, j + 1, k),
                        node(i, j, k + 1),
                        node(i + 1, j, k + 1),
                        node(i, j + 1, k + 1),
                        node(i + 1, j + 1, k + 1),
                    )
                    tetrahedra_list.extend(
                        tuple(cube[index] for index in tetra) for tetra in pattern
                    )
        tetrahedra = np.asarray(tetrahedra_list, dtype=int)
        cell_points = points[tetrahedra]
        signed_six_volumes = np.einsum(
            "ij,ij->i",
            np.cross(
                cell_points[:, 1] - cell_points[:, 0],
                cell_points[:, 2] - cell_points[:, 0],
            ),
            cell_points[:, 3] - cell_points[:, 0],
        )
        negative = signed_six_volumes < 0
        saved = tetrahedra[negative, 2].copy()
        tetrahedra[negative, 2] = tetrahedra[negative, 3]
        tetrahedra[negative, 3] = saved

    meshio.write(
        path,
        meshio.Mesh(points=points, cells=[("tetra", tetrahedra)]),
    )


def make_runner(monkeypatch, *, tiny_mesh: bool = False):
    stages_seen = []

    def fake_run(command, *, timeout, cwd):
        stage_flags = {
            "--segmentation": "segmentation",
            "--contour": "contour",
            "--surface": "surface",
            "--volumetric": "volumetric",
            "--uvc-fiber": "uvc-fiber",
        }
        stage = next(name for flag, name in stage_flags.items() if flag in command)
        stages_seen.append(stage)
        data_root = Path(command[command.index("--data-dir") + 1])
        subject = command[command.index("--subject") + 1]
        instance = command[command.index("--instance") + 1]
        case_dir = data_root / subject / f"Instance_{instance}"
        case_dir.mkdir(parents=True, exist_ok=True)
        if stage == "volumetric":
            write_mesh(case_dir / "mesh_all.vtk", tiny=tiny_mesh)
        elif stage == "uvc-fiber":
            subdir = case_dir / "UVC_i"
            subdir.mkdir()
            (subdir / "fiber.lon").write_text("fixture\n", encoding="utf-8")
        else:
            (case_dir / f"{stage}-result.json").write_text("fixture\n", encoding="utf-8")
        return CommandResult(
            command=tuple(command),
            returncode=0,
            stdout="fixture stdout",
            stderr="",
            duration_seconds=0.01,
            executable=command[0],
        )

    monkeypatch.setattr("cardianatomy.biv_volumetric.run_command", fake_run)
    return stages_seen


def test_surface_runner_preserves_sources_and_writes_auditable_manifest(tmp_path, monkeypatch):
    inputs = make_inputs(tmp_path / "inputs")
    source_hashes = {
        key: hashlib.sha256(path.read_bytes()).hexdigest()
        for key, path in inputs.items()
    }
    upstream = make_upstream(tmp_path)
    workspace = tmp_path / "nnunet"
    workspace.mkdir()
    stages_seen = make_runner(monkeypatch)

    result = run_biv_volumetric_pipeline(
        inputs,
        upstream_root=upstream,
        output_root=tmp_path / "output",
        stages=("segmentation", "contour", "surface"),
        workspace_dir=workspace,
        subject_id="demo_case",
    )

    assert result["status"] == "completed_surface_pipeline_only"
    assert stages_seen == ["segmentation", "contour", "surface"]
    assert result["checks"]["input_views_registered"] is False
    assert result["checks"]["clinical_validity_established"] is False
    assert result["upstream"]["project"] == "cdttk/biv-volumetric-meshing"
    assert len(result["inputs"]) == 4
    assert all(item["staged_sha256"] for item in result["inputs"].values())
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == source_hashes[key]
               for key, path in inputs.items())
    saved = json.loads((tmp_path / "output" / "run-manifest.json").read_text())
    assert saved["status"] == result["status"]
    assert all(stage["status"] == "completed" for stage in saved["stages"])
    assert (tmp_path / "output" / "logs" / "surface.log").is_file()


def test_volumetric_stage_requires_explicit_runtime_licensing_acknowledgement(tmp_path):
    inputs = make_inputs(tmp_path / "inputs")
    upstream = make_upstream(tmp_path)
    workspace = tmp_path / "nnunet"
    workspace.mkdir()
    carp = tmp_path / "carp"
    carp.mkdir()
    with pytest.raises(PermissionError, match="openCARP"):
        run_biv_volumetric_pipeline(
            inputs,
            upstream_root=upstream,
            output_root=tmp_path / "output",
            stages=("segmentation", "contour", "surface", "volumetric"),
            workspace_dir=workspace,
            carp_bin_dir=carp,
        )
    assert not (tmp_path / "output").exists()


def test_volume_mesh_is_inspected_and_qc_recorded(tmp_path, monkeypatch):
    inputs = make_inputs(tmp_path / "inputs")
    upstream = make_upstream(tmp_path)
    workspace = tmp_path / "nnunet"
    workspace.mkdir()
    carp = tmp_path / "carp"
    carp.mkdir()
    stages_seen = make_runner(monkeypatch)

    result = run_biv_volumetric_pipeline(
        inputs,
        upstream_root=upstream,
        output_root=tmp_path / "output",
        stages=("segmentation", "contour", "surface", "volumetric", "uvc-fiber"),
        workspace_dir=workspace,
        carp_bin_dir=carp,
        allow_restricted_runtime=True,
        subject_id="demo_case",
    )

    assert stages_seen == ["segmentation", "contour", "surface", "volumetric", "uvc-fiber"]
    assert result["status"] == "completed_volume_mesh_qc_passed_uvc_fiber_quality_unverified"
    assert result["checks"]["volume_mesh_qc_passed"] is True
    assert result["checks"]["fiber_quality_verified"] is False
    accepted_mesh = result["geometry_qc_passed_volume_mesh"]
    assert accepted_mesh["tetra_count"] >= 1000
    assert accepted_mesh["point_count"] >= 500
    assert accepted_mesh["qc"]["passed"] is True
    assert accepted_mesh["qc"]["checks"]["minimum_tetra_count"] is True
    assert result["mesh_acceptance_policy"]["minimum_shape_quality"] == 0.05
    assert result["stages"][-1]["uvc_fiber_named_outputs"]




def test_tiny_mesh_is_rejected_by_minimum_size_guard(tmp_path, monkeypatch):
    inputs = make_inputs(tmp_path / "inputs")
    upstream = make_upstream(tmp_path)
    workspace = tmp_path / "nnunet"
    workspace.mkdir()
    carp = tmp_path / "carp"
    carp.mkdir()
    stages_seen = make_runner(monkeypatch, tiny_mesh=True)

    with pytest.raises(RuntimeError, match="outputs and run manifest were preserved"):
        run_biv_volumetric_pipeline(
            inputs,
            upstream_root=upstream,
            output_root=tmp_path / "output",
            stages=("segmentation", "contour", "surface", "volumetric"),
            workspace_dir=workspace,
            carp_bin_dir=carp,
            allow_restricted_runtime=True,
            subject_id="tiny_case",
        )

    saved = json.loads((tmp_path / "output" / "run-manifest.json").read_text())
    assert saved["status"] == "failed"
    assert saved["checks"]["volume_mesh_qc_passed"] is False
    assert saved["volume_mesh_candidates"][0]["tetra_count"] == 1
    assert saved["volume_mesh_candidates"][0]["qc"]["checks"]["minimum_tetra_count"] is False
    assert "size and geometry-QC screening" in saved["stages"][-1]["error"]
    assert stages_seen[-1] == "volumetric"

def test_runner_rejects_3d_views_before_creating_output(tmp_path):
    inputs = make_inputs(tmp_path / "inputs")
    path = inputs["SAX"]
    nib.save(nib.Nifti1Image(np.zeros((6, 7, 8), dtype=np.uint8), np.eye(4)), path)
    upstream = make_upstream(tmp_path)
    output = tmp_path / "output"

    with pytest.raises(ValueError, match="4D cine NIfTI"):
        run_biv_volumetric_pipeline(
            inputs,
            upstream_root=upstream,
            output_root=output,
        )
    assert not output.exists()

def test_runner_refuses_nonempty_output_and_invalid_stage_order(tmp_path, monkeypatch):
    inputs = make_inputs(tmp_path / "inputs")
    upstream = make_upstream(tmp_path)
    workspace = tmp_path / "nnunet"
    workspace.mkdir()
    output = tmp_path / "output"
    output.mkdir()
    (output / "keep.txt").write_text("preserve", encoding="utf-8")

    with pytest.raises(ValueError, match="non-empty"):
        run_biv_volumetric_pipeline(
            inputs,
            upstream_root=upstream,
            output_root=output,
            workspace_dir=workspace,
        )
    assert (output / "keep.txt").read_text(encoding="utf-8") == "preserve"

    with pytest.raises(ValueError, match="prefix in order"):
        run_biv_volumetric_pipeline(
            inputs,
            upstream_root=upstream,
            output_root=tmp_path / "other",
            stages=("surface",),
            workspace_dir=workspace,
        )


def test_volume_stage_fails_closed_if_mesh_is_missing_and_preserves_manifest(tmp_path, monkeypatch):
    inputs = make_inputs(tmp_path / "inputs")
    upstream = make_upstream(tmp_path)
    workspace = tmp_path / "nnunet"
    workspace.mkdir()
    carp = tmp_path / "carp"
    carp.mkdir()

    def fake_run(command, *, timeout, cwd):
        stage = next(
            name for flag, name in (
                ("--segmentation", "segmentation"),
                ("--contour", "contour"),
                ("--surface", "surface"),
                ("--volumetric", "volumetric"),
            ) if flag in command
        )
        data_root = Path(command[command.index("--data-dir") + 1])
        case_dir = data_root / command[command.index("--subject") + 1] / (
            f"Instance_{command[command.index('--instance') + 1]}"
        )
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / f"{stage}.txt").write_text("no mesh", encoding="utf-8")
        return CommandResult(tuple(command), 0, "ok", "", 0.01, command[0])

    monkeypatch.setattr("cardianatomy.biv_volumetric.run_command", fake_run)
    with pytest.raises(RuntimeError, match="outputs and run manifest were preserved"):
        run_biv_volumetric_pipeline(
            inputs,
            upstream_root=upstream,
            output_root=tmp_path / "output",
            stages=("segmentation", "contour", "surface", "volumetric"),
            workspace_dir=workspace,
            carp_bin_dir=carp,
            allow_restricted_runtime=True,
        )
    saved = json.loads((tmp_path / "output" / "run-manifest.json").read_text())
    assert saved["status"] == "failed"
    assert saved["failed_stage"] == "volumetric"
    assert saved["volume_mesh_candidates"] == []


def test_command_builder_rejects_restricted_runtime_without_explicit_permission():
    with pytest.raises(PermissionError, match="openCARP"):
        biv_volumetric_command(
            run_script="run.py",
            data_dir="/data",
            components=("surface", "volumetric"),
        )
    command = biv_volumetric_command(
        run_script="run.py",
        data_dir="/data",
        components=("segmentation", "contour"),
        gpu=True,
    )
    assert "--gpu" in command


def test_cli_runs_adapter_and_prints_manifest(tmp_path, monkeypatch, capsys):
    captured = {}

    def fake_runner(views, **kwargs):
        captured["views"] = views
        captured["kwargs"] = kwargs
        return {
            "status": "completed_surface_pipeline_only",
            "selected_stages": ["segmentation", "contour", "surface"],
        }

    monkeypatch.setattr(
        "cardianatomy.biv_volumetric_cli.run_biv_volumetric_pipeline",
        fake_runner,
    )
    result = biv_volumetric_cli_main(
        [
            "--sax", "SAX.nii.gz",
            "--lax-2ch", "LAX_2Ch.nii.gz",
            "--lax-3ch", "LAX_3Ch.nii.gz",
            "--lax-4ch", "LAX_4Ch.nii.gz",
            "--upstream-root", str(tmp_path / "upstream"),
            "--output-root", str(tmp_path / "output"),
            "--nnunet-workspace", str(tmp_path / "workspace"),
            "--subject-id", "case_001",
            "--minimum-points", "100",
            "--minimum-tetrahedra", "200",
            "--minimum-shape-quality", "0.1",
        ]
    )
    output = json.loads(capsys.readouterr().out)
    assert result == 0
    assert output["status"] == "completed_surface_pipeline_only"
    assert captured["views"]["SAX"] == "SAX.nii.gz"
    assert captured["kwargs"]["subject_id"] == "case_001"
    assert captured["kwargs"]["minimum_points"] == 100
    assert captured["kwargs"]["minimum_tetrahedra"] == 200
    assert captured["kwargs"]["minimum_shape_quality"] == 0.1
    assert captured["kwargs"]["stages"] == [
        "segmentation", "contour", "surface"
    ]


def test_cli_reports_runner_errors_as_json(tmp_path, monkeypatch, capsys):
    def fake_runner(*args, **kwargs):
        raise ValueError("synthetic input error")

    monkeypatch.setattr(
        "cardianatomy.biv_volumetric_cli.run_biv_volumetric_pipeline",
        fake_runner,
    )
    result = biv_volumetric_cli_main(
        [
            "--sax", "SAX.nii.gz",
            "--lax-2ch", "LAX_2Ch.nii.gz",
            "--lax-3ch", "LAX_3Ch.nii.gz",
            "--lax-4ch", "LAX_4Ch.nii.gz",
            "--upstream-root", str(tmp_path / "upstream"),
            "--output-root", str(tmp_path / "output"),
        ]
    )
    captured = capsys.readouterr()
    assert result == 2
    assert json.loads(captured.err) == {"error": "synthetic input error"}


@pytest.mark.parametrize(
    ("thresholds", "error_message"),
    [
        ({"minimum_points": 0}, "minimum_points"),
        ({"minimum_tetrahedra": True}, "minimum_tetrahedra"),
        ({"minimum_shape_quality": 1.1}, "minimum_shape_quality"),
    ],
)
def test_mesh_acceptance_thresholds_are_validated(tmp_path, thresholds, error_message):
    inputs = make_inputs(tmp_path / "inputs")
    upstream = make_upstream(tmp_path)
    output = tmp_path / "output"

    with pytest.raises(ValueError, match=error_message):
        run_biv_volumetric_pipeline(
            inputs,
            upstream_root=upstream,
            output_root=output,
            **thresholds,
        )
    assert not output.exists()


def test_input_staging_failure_preserves_preflight_and_failure_manifest(
    tmp_path, monkeypatch
):
    inputs = make_inputs(tmp_path / "inputs")
    upstream = make_upstream(tmp_path)
    workspace = tmp_path / "nnunet"
    workspace.mkdir()
    output = tmp_path / "output"

    def fail_staging(*args, **kwargs):
        raise ValueError("synthetic staging failure")

    monkeypatch.setattr(
        "cardianatomy.biv_volumetric._prepare_view_images",
        fail_staging,
    )
    with pytest.raises(RuntimeError, match="preflight evidence"):
        run_biv_volumetric_pipeline(
            inputs,
            upstream_root=upstream,
            output_root=output,
            workspace_dir=workspace,
        )

    manifest = json.loads((output / "run-manifest.json").read_text())
    assert manifest["status"] == "failed"
    assert manifest["failed_stage"] == "input_staging"
    assert "synthetic staging failure" in manifest["error"]
    assert (output / "preflight-manifest.json").is_file()
