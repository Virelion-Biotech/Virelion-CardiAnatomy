import gzip
import json
from pathlib import Path

import meshio
import nibabel as nib
import numpy as np
import pytest

from cardianatomy.cli import main
from cardianatomy.models import AnatomyBundle
from cardianatomy.serialization import read_json, write_json_atomic

ROOT = Path(__file__).resolve().parents[1]


def test_complete_native_pipeline_and_resume(tmp_path, capsys):
    points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    volume = tmp_path / "volume.vtu"
    meshio.write_points_cells(volume, points, [("tetra", np.array([[0, 1, 2, 3]]))])
    request = {
        "subject_id": "synthetic",
        "acquisition": {
            "subject_id": "synthetic",
            "study_id": "fixture",
            "acquisition_id": "A1",
            "modality": "OTHER",
            "source": {"artifact_id": "volume", "kind": "volume_mesh", "uri": str(volume)},
        },
        "requested_outputs": ["volume_mesh", "qc_report", "report"],
        "output_root": str(tmp_path / "work"),
        "plan": {
            "stages": ["ingest", "qc", "export"],
            "backends": {"ingest": "native", "qc": "native", "export": "native"},
        },
    }
    input_path, output_path = tmp_path / "request.json", tmp_path / "bundle.json"
    write_json_atomic(input_path, request)
    args = ["build", str(input_path), "--output", str(output_path), "--target", "mechanics"]
    assert main(args) == 0
    first = AnatomyBundle.model_validate(read_json(output_path))
    assert first.mechanics_ready
    assert [s.stage for s in first.stages] == ["ingest", "qc", "export"]
    assert main(args) == 0
    second = AnatomyBundle.model_validate(read_json(output_path))
    assert first.bundle_fingerprint == second.bundle_fingerprint
    assert main(["validate", str(output_path), "--target", "mechanics"]) == 0
    assert main(["report", str(output_path), str(tmp_path / "nested/report.html")]) == 0
    assert "<html" in (tmp_path / "nested/report.html").read_text()
    assert main(["inspect-mesh", str(volume)]) == 0
    assert main(["hash", str(volume)]) == 0
    for name in ("doctor", "tools", "presets"):
        assert main([name]) == 0
    capsys.readouterr()


def test_public_negative_mesh_qc_has_failure_exit(tmp_path, capsys):
    source = ROOT / "validation/data/lv.vtk.gz"
    path = tmp_path / "lv.vtk"
    path.write_bytes(gzip.decompress(source.read_bytes()))
    assert main(["inspect-mesh", str(path), "--require-watertight"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert not payload["qc"]["passed"]
    assert "no_duplicate_cells" in payload["qc"]["errors"]


def test_cli_numeric_and_reference_operations(tmp_path, capsys):
    for command, fixture in [
        ("cine-phases", "volume_curve.json"),
        ("compose-affines", "affine_chain.json"),
        ("compare-correspondence", "correspondence_payload.json"),
        ("summarize-motion", "motion_payload.json"),
    ]:
        assert main([command, str(ROOT / "examples" / fixture)]) == 0
    matrix = tmp_path / "matrix.json"
    write_json_atomic(matrix, np.eye(4).tolist())
    assert main(["invert-affine", str(matrix)]) == 0
    landmarks = tmp_path / "points.json"
    write_json_atomic(landmarks, [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
    assert main(["register-rigid", str(landmarks), str(landmarks)]) == 0
    assert main(["audit-manifest", str(ROOT / "examples/toolchain_manifest.json")]) == 0
    cases = {
        "validation_points": {"reference_points": [[0, 0, 0]], "prediction_points": [[1, 0, 0]]},
        "validation_segmentation": {"reference_labels": [1, 1, 0], "prediction_labels": [1, 0, 1]},
        "geometry_measure": {
            "points": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
            "tetrahedra": [[0, 1, 2, 3]],
        },
        "segmentation_qc": {"labels": [[[0, 1], [1, 0]]]},
        "series_rank": {"series": []},
        "reference_microstructure": {
            "circumferential": [[1, 0, 0]],
            "longitudinal": [[0, 1, 0]],
            "transmural_coordinate": [0.5],
        },
        "scar_classify": {
            "values": [0, 1, 2],
            "spec": {"border_threshold": 0.5, "core_threshold": 1.5},
        },
    }
    for operation, payload in cases.items():
        path = tmp_path / "payload.json"
        write_json_atomic(path, payload)
        assert main(["evaluate", operation, str(path)]) == 0
    capsys.readouterr()


def test_nifti_and_dicom_file_cli(tmp_path, capsys):
    path = tmp_path / "image.nii.gz"
    nib.save(
        nib.Nifti1Image(np.zeros((3, 4, 5), dtype=np.uint8), np.diag([2.0, 3.0, 4.0, 1.0])), path
    )
    assert main(["inspect-nifti", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["voxel_spacing"] == [2.0, 3.0, 4.0]
    # An empty directory is not represented as a discovered clinical series.
    folder = tmp_path / "empty-dicom"
    folder.mkdir()
    assert main(["inspect-dicom", str(folder)]) == 0
    assert json.loads(capsys.readouterr().out) == []


@pytest.mark.parametrize("raw", ['{"a":1,"a":2}', '{"a":NaN}', "[]"])
def test_invalid_cli_input_is_structured_error(tmp_path, capsys, raw):
    path = tmp_path / "bad.json"
    path.write_text(raw)
    assert main(["build", str(path), "--output", str(tmp_path / "out.json")]) == 2
    assert "error" in json.loads(capsys.readouterr().err)
    assert not (tmp_path / "out.json").exists()
