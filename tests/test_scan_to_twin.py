from __future__ import annotations

import subprocess
from pathlib import Path

from cardianatomy import scan_to_twin


def _write_config_template(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """[modules]
preprocessing = true
fitting = true

[multiprocessing]
workers = 4

[plotting]
generate_plots_fitting = true
include_images = true
export_images = false

[input_pp]
source = "source"
batch_ID = "batch"
analyst_id = "analyst"
processing = "processing"
states = "states"

[view-selection]
correct_mode = "manual"
show_videos = true

[output_pp]
overwrite = false
output_directory = "guidepoints"

[input_fitting]
gp_directory = "guidepoints"

[output_fitting]
output_directory = "fitted"
overwrite = false
mesh_format = ".vtk"
output_meshes = ["LV_ENDOCARDIAL"]
closed_mesh = false
""",
        encoding="utf-8",
    )


def test_run_adapter_creates_hashed_manifest_and_surface_inventory(tmp_path, monkeypatch):
    scan_dir = tmp_path / "source-scan"
    scan_dir.mkdir()
    (scan_dir / "study.bin").write_bytes(b"synthetic scan fixture")

    upstream = tmp_path / "upstream"
    main_script = upstream / "src" / "bivme" / "main.py"
    template = upstream / "src" / "bivme" / "configs" / "config.toml"
    main_script.parent.mkdir(parents=True)
    main_script.write_text("# stub for mocked subprocess integration test\n", encoding="utf-8")
    _write_config_template(template)
    for name in ("Segmentation", "ViewSelection"):
        model_dir = upstream / "src" / "bivme" / "preprocessing" / "dicom" / "models" / name
        model_dir.mkdir(parents=True)
        (model_dir / "weights.bin").write_bytes(b"x" * 2048)

    output_root = tmp_path / "outputs"
    monkeypatch.setattr(
        scan_to_twin,
        "_summarize_cine_cmr",
        lambda _: {
            "modality": "MR",
            "file_count": 1,
            "mr_image_instance_count": 1,
            "series_count": 1,
            "bytes": 21,
            "source_sha256": "a" * 64,
            "modalities_present": ["MR"],
            "patient_identifiers_recorded": False,
        },
    )
    monkeypatch.setattr(
        scan_to_twin,
        "_probe_python_version",
        lambda _: (3, 11, 8, "Python 3.11.8"),
    )
    monkeypatch.setattr(scan_to_twin, "_check_importable_bivme", lambda *_: None)
    monkeypatch.setattr(
        scan_to_twin,
        "_model_assets",
        lambda _: {
            "Segmentation": {"file_count": 1, "bytes": 2048},
            "ViewSelection": {"file_count": 1, "bytes": 2048},
        },
    )
    monkeypatch.setattr(
        scan_to_twin.subprocess,
        "run",
        lambda argv, **kwargs: subprocess.CompletedProcess(
            args=argv, returncode=0, stdout="unit-test-commit\n", stderr=""
        ),
    )

    def fake_run_logged(argv, *, cwd, log_path, timeout_seconds):
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("synthetic test output\n", encoding="utf-8")
        if log_path.name == "biv-me.log":
            case_id = argv[argv.index("-case") + 1]
            case_root = output_root / "fitted-models" / case_id
            case_root.mkdir(parents=True)
            (case_root / "LV.vtk").write_text("synthetic surface fixture\n", encoding="utf-8")
            (case_root / "RV.obj").write_text("synthetic surface fixture\n", encoding="utf-8")
            (case_root / "fit.html").write_text("<html>synthetic fixture</html>", encoding="utf-8")
        return {
            "returncode": 0,
            "timed_out": False,
            "duration_seconds": 0.1,
            "log": str(log_path),
        }

    monkeypatch.setattr(scan_to_twin, "_run_logged", fake_run_logged)
    result = scan_to_twin.run_biv_me_scan_to_twin(
        scan_dir,
        biv_me_root=upstream,
        output_root=output_root,
        python_executable="python311",
        calculate_metrics=False,
    )

    assert result["workflow_status"] == "completed"
    assert result["execution"]["surface_mesh_count"] == 2
    assert result["input"]["patient_identifiers_recorded"] is False
    manifest_text = (output_root / "scan-to-twin-manifest.json").read_text(encoding="utf-8")
    assert str(scan_dir) not in manifest_text
    assert result["privacy"]["raw_pixels_copied_to_output"] is False
    assert result["artifacts"]
    assert (output_root / "config" / "bivme-generated.toml").is_file()


def test_adapter_refuses_nonempty_output_directory(tmp_path):
    scan_dir = tmp_path / "source-scan"
    scan_dir.mkdir()
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    output_root = tmp_path / "already-has-work"
    output_root.mkdir()
    sentinel = output_root / "preserve.txt"
    sentinel.write_text("preserve existing content", encoding="utf-8")

    try:
        scan_to_twin.run_biv_me_scan_to_twin(
            scan_dir,
            biv_me_root=upstream,
            output_root=output_root,
        )
    except ValueError as exc:
        assert "not empty" in str(exc)
    else:
        raise AssertionError("Existing output directory was accepted")
    assert sentinel.read_text(encoding="utf-8") == "preserve existing content"


def test_generated_configuration_points_into_workspace(tmp_path):
    template = tmp_path / "config.toml"
    output = tmp_path / "generated.toml"
    _write_config_template(template)
    scan_to_twin._build_bivme_config(
        template=template,
        output_path=output,
        input_root=tmp_path / "staging",
        output_root=tmp_path / "result",
        review_mode="adaptive",
        workers=2,
    )
    content = output.read_text(encoding="utf-8")
    assert str((tmp_path / "staging").resolve()) in content
    assert 'correct_mode = "adaptive"' in content
    assert "workers = 2" in content
    assert str((tmp_path / "result" / "fitted-models").resolve()) in content
