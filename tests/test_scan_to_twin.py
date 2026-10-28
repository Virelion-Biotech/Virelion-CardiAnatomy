from __future__ import annotations

import hashlib
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
            for surface_name in (
                "case_LV_ENDOCARDIAL_000.vtk",
                "case_RV_ENDOCARDIAL_000.obj",
                "case_EPICARDIAL_000.vtk",
            ):
                (case_root / surface_name).write_text(
                    "synthetic surface fixture\n", encoding="utf-8"
                )
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
    assert result["execution"]["surface_mesh_count"] == 3
    assert result["execution"]["missing_surface_types"] == []
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
    assert scan_to_twin._toml_string(
        str((tmp_path / "staging").resolve())
    ) in content
    assert 'correct_mode = "adaptive"' in content
    assert "workers = 2" in content
    assert scan_to_twin._toml_string(
        str((tmp_path / "result" / "fitted-models").resolve())
    ) in content


def _write_mr_dicom(
    path: Path,
    *,
    patient_id: str = "PT-001",
    study_uid: str | None = None,
    series_uid: str | None = None,
) -> None:
    import numpy as np
    from pydicom.dataset import FileDataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, MRImageStorage, generate_uid

    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = MRImageStorage
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    dataset = FileDataset(str(path), {}, file_meta=meta, preamble=b"\0" * 128)
    dataset.SOPClassUID = MRImageStorage
    dataset.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    dataset.Modality = "MR"
    dataset.PatientID = patient_id
    dataset.PatientName = "Test^Patient"
    dataset.StudyInstanceUID = study_uid or generate_uid()
    dataset.SeriesInstanceUID = series_uid or generate_uid()
    dataset.Rows = 2
    dataset.Columns = 2
    dataset.SamplesPerPixel = 1
    dataset.PhotometricInterpretation = "MONOCHROME2"
    dataset.BitsAllocated = 16
    dataset.BitsStored = 16
    dataset.HighBit = 15
    dataset.PixelRepresentation = 0
    dataset.PixelData = np.array([1, 2, 3, 4], dtype=np.uint16).tobytes()
    dataset.save_as(path, enforce_file_format=True)


def test_basic_hash_and_toml_escaping(tmp_path):
    path = tmp_path / "payload.bin"
    path.write_bytes(b"cardiac")
    assert scan_to_twin._sha256_file(path) == hashlib.sha256(b"cardiac").hexdigest()
    assert scan_to_twin._toml_string('path with "quote"') == '"path with \\"quote\\""'
    assert scan_to_twin._utc_now().endswith("+00:00")


def test_replace_toml_value_is_section_scoped(tmp_path):
    template = tmp_path / "template.toml"
    _write_config_template(template)
    source = scan_to_twin._replace_toml_value(
        template.read_text(encoding="utf-8"),
        "input_pp",
        "source",
        scan_to_twin._toml_string("/secure/input"),
    )
    assert 'source = "/secure/input"' in source
    assert 'source = "source"' not in source
    try:
        scan_to_twin._replace_toml_value(source, "input_pp", "missing", '"x"')
    except ValueError as exc:
        assert "Expected exactly one missing" in str(exc)
    else:
        raise AssertionError("Missing configuration key was accepted")


def test_probe_python_version_parses_and_rejects(monkeypatch):
    monkeypatch.setattr(
        scan_to_twin.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args, returncode=0, stdout="Python 3.11.9\n", stderr=""
        ),
    )
    assert scan_to_twin._probe_python_version("python") == (
        3, 11, 9, "Python 3.11.9"
    )
    monkeypatch.setattr(
        scan_to_twin.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args, returncode=2, stdout="", stderr="not runnable"
        ),
    )
    try:
        scan_to_twin._probe_python_version("missing-python")
    except ValueError as exc:
        assert "probe failed" in str(exc)
    else:
        raise AssertionError("Failed Python version probe was accepted")


def test_importability_check_reports_install_instructions(monkeypatch, tmp_path):
    monkeypatch.setattr(
        scan_to_twin.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args, returncode=1, stdout="", stderr="ModuleNotFoundError: bivme"
        ),
    )
    try:
        scan_to_twin._check_importable_bivme("python", tmp_path)
    except ValueError as exc:
        assert "pip install -e" in str(exc)
        assert "ModuleNotFoundError" in str(exc)
    else:
        raise AssertionError("Non-importable upstream module was accepted")


def test_model_asset_inventory_pins_weight_hashes(tmp_path):
    model_root = (
        tmp_path / "src" / "bivme" / "preprocessing" / "dicom" / "models"
    )
    for component in ("Segmentation", "ViewSelection"):
        folder = model_root / component
        folder.mkdir(parents=True)
        (folder / "weights.pth").write_bytes((component * 500).encode())
    inventory = scan_to_twin._model_assets(tmp_path)
    for component in ("Segmentation", "ViewSelection"):
        assert inventory[component]["file_count"] == 1
        assert inventory[component]["files"][0]["path"].endswith("weights.pth")
        assert len(inventory[component]["files"][0]["sha256"]) == 64
    (model_root / "Segmentation" / "weights.pth").unlink()
    try:
        scan_to_twin._model_assets(tmp_path)
    except ValueError as exc:
        assert "No non-placeholder weights" in str(exc)
    else:
        raise AssertionError("Missing model weights were accepted")


def test_scan_summary_rejects_non_dicom_and_different_patients(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "note.txt").write_text("not a DICOM file", encoding="utf-8")
    try:
        scan_to_twin._summarize_cine_cmr(empty)
    except ValueError as exc:
        assert "No readable DICOM files" in str(exc)
    else:
        raise AssertionError("Non-DICOM input was accepted")

    scan_dir = tmp_path / "mixed"
    scan_dir.mkdir()
    _write_mr_dicom(scan_dir / "one.dcm", patient_id="P1")
    _write_mr_dicom(scan_dir / "two.dcm", patient_id="P2")
    try:
        scan_to_twin._summarize_cine_cmr(scan_dir)
    except ValueError as exc:
        assert "multiple PatientID" in str(exc)
    else:
        raise AssertionError("Multiple-patient input was accepted")


def test_scan_summary_rejects_mixed_studies_and_excludes_identifiers(tmp_path):
    scan_dir = tmp_path / "mixed-studies"
    scan_dir.mkdir()
    _write_mr_dicom(
        scan_dir / "one.dcm", patient_id="PRIVATE-42", study_uid="1.2.3.4"
    )
    _write_mr_dicom(
        scan_dir / "two.dcm", patient_id="PRIVATE-42", study_uid="1.2.3.5"
    )
    try:
        scan_to_twin._summarize_cine_cmr(scan_dir)
    except ValueError as exc:
        assert "multiple study UIDs" in str(exc)
    else:
        raise AssertionError("Multiple-study input was accepted")

    single = tmp_path / "single"
    single.mkdir()
    _write_mr_dicom(single / "one.dcm", patient_id="PRIVATE-42", study_uid="1.2.3.4")
    summary = scan_to_twin._summarize_cine_cmr(single)
    assert summary["modality"] == "MR"
    assert summary["mr_image_instance_count"] == 1
    assert summary["patient_identifiers_recorded"] is False
    assert "PRIVATE-42" not in str(summary)
    assert str(single) not in str(summary)


def test_artifact_inventory_uses_compound_nifti_extension(tmp_path):
    fitted = tmp_path / "fitted"
    metrics = tmp_path / "metrics"
    fitted.mkdir()
    metrics.mkdir()
    (fitted / "labels.nii.gz").write_bytes(b"nifti-data")
    (fitted / "surface.vtk").write_bytes(b"surface")
    artifacts = scan_to_twin._artifact_inventory(tmp_path, fitted, metrics)
    formats = {item["path"]: item["format"] for item in artifacts}
    assert formats["fitted/labels.nii.gz"] == "nii.gz"
    assert formats["fitted/surface.vtk"] == "vtk"
    assert all(len(item["sha256"]) == 64 for item in artifacts)


def test_logged_subprocess_records_success_and_timeout(monkeypatch, tmp_path):
    log = tmp_path / "run.log"

    def success(argv, **kwargs):
        kwargs["stdout"].write("expected output\n")
        return subprocess.CompletedProcess(args=argv, returncode=0)

    monkeypatch.setattr(scan_to_twin.subprocess, "run", success)
    result = scan_to_twin._run_logged(
        ["tool", "arg"], cwd=tmp_path, log_path=log, timeout_seconds=4
    )
    assert result["returncode"] == 0
    assert "expected output" in log.read_text(encoding="utf-8")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])

    monkeypatch.setattr(scan_to_twin.subprocess, "run", timeout)
    result = scan_to_twin._run_logged(
        ["tool"], cwd=tmp_path, log_path=log, timeout_seconds=1
    )
    assert result["timed_out"] is True
    assert result["returncode"] == 124
    assert "Timed out" in log.read_text(encoding="utf-8")


def test_runner_rejects_bad_options_and_overlapping_paths(tmp_path):
    scan_dir = tmp_path / "scan"
    scan_dir.mkdir()
    common = {"biv_me_root": tmp_path / "upstream"}
    invalid_options = [
        {"review_mode": "unknown"},
        {"workers": 0},
        {"timeout_seconds": 0},
        {"analysis_timeout_seconds": -1},
    ]
    for index, overrides in enumerate(invalid_options):
        kwargs = {
            **common,
            "output_root": tmp_path / f"out-{index}",
            **overrides,
        }
        try:
            scan_to_twin.run_biv_me_scan_to_twin(scan_dir, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid options were accepted: {overrides}")

    try:
        scan_to_twin.run_biv_me_scan_to_twin(
            scan_dir,
            biv_me_root=tmp_path / "upstream",
            output_root=scan_dir / "nested-output",
        )
    except ValueError as exc:
        assert "must be disjoint" in str(exc)
    else:
        raise AssertionError("Nested output directory was accepted")


def test_metrics_pipeline_records_partial_failure_and_selects_ed(tmp_path, monkeypatch):
    upstream = tmp_path / "upstream"
    analysis = upstream / "src" / "bivme" / "analysis"
    analysis.mkdir(parents=True)
    for filename in (
        "compute_volume.py",
        "compute_global_circumferential_strain.py",
        "compute_global_longitudinal_strain.py",
        "compute_wall_thickness.py",
    ):
        (analysis / filename).write_text("# fake upstream script\n", encoding="utf-8")
    fitted = tmp_path / "fitted"
    fitted.mkdir()
    metrics = tmp_path / "metrics"
    case_id = "case-test"
    calls = []

    def fake_run_logged(argv, *, cwd, log_path, timeout_seconds):
        calls.append(log_path.name)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("fake command log\n", encoding="utf-8")
        if log_path.name == "volumes.log":
            (metrics / "lvrv_volumes.csv").write_text(
                "name,frame,lv_vol,lvm,rv_vol,rvm,lv_epivol,rv_epivol\n"
                "case-test,0,90,1,70,1,140,120\n"
                "case-test,1,120,1,80,1,170,130\n"
                "case-test,2,100,1,72,1,150,122\n",
                encoding="utf-8",
            )
        is_wall_fail = log_path.name == "wall-thickness.log"
        return {
            "returncode": 1 if is_wall_fail else 0,
            "timed_out": False,
            "duration_seconds": 0.1,
            "log": str(log_path),
        }

    monkeypatch.setattr(scan_to_twin, "_run_logged", fake_run_logged)
    result = scan_to_twin._run_metrics(
        python_executable="python",
        bivme_root=upstream,
        fitted_root=fitted,
        metrics_root=metrics,
        case_id=case_id,
        analysis_timeout_seconds=10,
    )
    assert result["volumes"]["status"] == "completed"
    assert result["volumes"]["end_diastolic_frame_selected_by_max_lv_volume"] == 1
    assert result["circumferential_strain"]["status"] == "completed"
    assert result["longitudinal_strain"]["status"] == "completed"
    assert result["wall_thickness"]["status"] == "failed"
    assert result["interpretation_note"]
    assert "wall-thickness.log" in calls


def test_metrics_skip_strain_when_volume_curve_is_unavailable(tmp_path, monkeypatch):
    upstream = tmp_path / "upstream"
    analysis = upstream / "src" / "bivme" / "analysis"
    analysis.mkdir(parents=True)
    for filename in (
        "compute_volume.py",
        "compute_global_circumferential_strain.py",
        "compute_global_longitudinal_strain.py",
        "compute_wall_thickness.py",
    ):
        (analysis / filename).write_text("# fake upstream script\n", encoding="utf-8")
    metrics = tmp_path / "metrics"
    calls = []

    def fake_run_logged(argv, *, cwd, log_path, timeout_seconds):
        calls.append(log_path.name)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("fake log\n", encoding="utf-8")
        return {
            "returncode": 1 if log_path.name == "volumes.log" else 0,
            "timed_out": False,
            "duration_seconds": 0.1,
            "log": str(log_path),
        }

    monkeypatch.setattr(scan_to_twin, "_run_logged", fake_run_logged)
    result = scan_to_twin._run_metrics(
        python_executable="python",
        bivme_root=upstream,
        fitted_root=tmp_path / "fitted",
        metrics_root=metrics,
        case_id="case-test",
        analysis_timeout_seconds=10,
    )
    assert result["circumferential_strain"]["status"] == "skipped"
    assert result["longitudinal_strain"]["status"] == "skipped"
    assert "circumferential-strain.log" not in calls
    assert result["wall_thickness"]["status"] == "completed"
