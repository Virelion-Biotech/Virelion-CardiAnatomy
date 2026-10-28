"""Launch the licensed biv-me scan-to-biventricular-surface workflow safely.

This module orchestrates the upstream application; it does not copy its model code
or weights. The result is a patient-specific biventricular surface model plus
optional functional measurements, not by itself a fully calibrated multiphysics twin.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_BIVME_URL = "https://github.com/UOA-Heart-Mechanics-Research/biv-me"
_BIVME_MODEL_URL = "https://github.com/UOA-Heart-Mechanics-Research/biv-me-dl-models"
_SAFE_CASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
_MAX_DICOM_FILES = 200_000
_MAX_MANIFEST_ARTIFACTS = 20_000


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _toml_string(value: str) -> str:
    # JSON basic strings are also valid TOML basic strings.
    return json.dumps(value, ensure_ascii=True)


def _replace_toml_value(text: str, section: str, key: str, value: str) -> str:
    """Replace exactly one existing value inside one TOML section."""
    lines = text.splitlines(keepends=True)
    section_header = f"[{section}]"
    starts = [i for i, line in enumerate(lines) if line.strip() == section_header]
    if len(starts) != 1:
        raise ValueError(f"Expected exactly one [{section}] section in biv-me config")
    start = starts[0] + 1
    end = next(
        (i for i in range(start, len(lines)) if lines[i].lstrip().startswith("[")),
        len(lines),
    )
    pattern = re.compile(rf"^(\s*{re.escape(key)}\s*=\s*).*$")
    matches = [i for i in range(start, end) if pattern.match(lines[i].rstrip("\r\n"))]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one {key}= entry in [{section}] of the upstream config"
        )
    index = matches[0]
    old_line = lines[index]
    newline = "\r\n" if old_line.endswith("\r\n") else "\n" if old_line.endswith("\n") else ""
    match = pattern.match(old_line.rstrip("\r\n"))
    assert match is not None
    lines[index] = f"{match.group(1)}{value}{newline}"
    return "".join(lines)


def _probe_python_version(executable: str | Path) -> tuple[int, int, int, str]:
    try:
        result = subprocess.run(
            [str(executable), "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"Cannot run the selected Python interpreter: {executable}") from exc
    output = (result.stdout or result.stderr).strip()
    if result.returncode != 0:
        raise ValueError(f"Python version probe failed: {output or result.returncode}")
    match = re.search(r"Python\s+(\d+)\.(\d+)\.(\d+)", output)
    if not match:
        raise ValueError(f"Could not parse Python version from {output!r}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3)), output


def _check_importable_bivme(executable: str | Path, root: Path) -> None:
    try:
        result = subprocess.run(
            [str(executable), "-c", "import bivme; print('biv-me import OK')"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Could not verify the biv-me Python environment") from exc
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()[-3000:]
        raise ValueError(
            "The selected Python environment cannot import bivme. Activate the dedicated "
            "Python 3.11 biv-me environment and install the upstream repository with "
            "'python -m pip install -e .', then run 'python src/pyezzi/setup.py build_ext "
            "--inplace'. " + details
        )


def _model_assets(root: Path) -> dict[str, Any]:
    model_root = root / "src" / "bivme" / "preprocessing" / "dicom" / "models"
    result: dict[str, Any] = {}
    for component in ("Segmentation", "ViewSelection"):
        folder = model_root / component
        if not folder.is_dir():
            raise ValueError(
                f"Missing biv-me {component} model directory: {folder}. "
                "Install the upstream model submodule with 'git submodule update --init' "
                "and retrieve its Git LFS files where used."
            )
        model_files = [
            path for path in folder.rglob("*")
            if path.is_file() and path.stat().st_size > 1024
        ]
        if not model_files:
            raise ValueError(
                f"No non-placeholder weights found in biv-me {component} models. "
                "Run 'git submodule update --init' and verify Git LFS model files are present."
            )
        model_files.sort(key=lambda path: path.relative_to(model_root).as_posix())
        result[component] = {
            "file_count": len(model_files),
            "bytes": sum(path.stat().st_size for path in model_files),
            "files": [
                {
                    "path": path.relative_to(model_root).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": _sha256_file(path),
                }
                for path in model_files
            ],
        }
    return result


def _summarize_cine_cmr(scan_dir: Path) -> dict[str, Any]:
    try:
        import pydicom
    except ImportError as exc:
        raise RuntimeError(
            "Scan ingestion requires DICOM support. Install CardiAnatomy's I/O dependencies "
            "with 'python -m pip install -e \".[io]\"'."
        ) from exc

    if not scan_dir.is_dir():
        raise ValueError(f"Input scan directory does not exist: {scan_dir}")
    files = sorted(path for path in scan_dir.rglob("*") if path.is_file())
    if not files:
        raise ValueError("Input scan directory contains no files")
    if len(files) > _MAX_DICOM_FILES:
        raise ValueError(f"Scan directory exceeds the {_MAX_DICOM_FILES} file safety limit")

    parsed: list[tuple[Path, Any]] = []
    total_bytes = 0
    for path in files:
        try:
            dataset = pydicom.dcmread(str(path), stop_before_pixels=True, force=False)
        except Exception:
            continue
        if not getattr(dataset, "SOPClassUID", None) and not getattr(dataset, "Modality", None):
            continue
        parsed.append((path, dataset))
        total_bytes += path.stat().st_size

    if not parsed:
        raise ValueError(
            "No readable DICOM files were found. This backend expects a single-patient "
            "cine-CMR DICOM folder, not NIfTI, PNG, or an already segmented mesh."
        )

    modalities = sorted({
        str(getattr(dataset, "Modality", "")).strip().upper()
        for _, dataset in parsed
        if str(getattr(dataset, "Modality", "")).strip()
    })
    mr_images = [
        (path, dataset) for path, dataset in parsed
        if str(getattr(dataset, "Modality", "")).strip().upper() == "MR"
        and int(getattr(dataset, "Rows", 0) or 0) > 0
        and int(getattr(dataset, "Columns", 0) or 0) > 0
    ]
    if not mr_images:
        raise ValueError(
            "No MR image instances were found. The direct scan backend uses biv-me for "
            "cine cardiovascular MRI; CT or other modalities need a separately qualified backend."
        )

    patient_ids = {
        str(getattr(dataset, "PatientID", "")).strip()
        for _, dataset in parsed
        if str(getattr(dataset, "PatientID", "")).strip()
    }
    study_uids = {
        str(getattr(dataset, "StudyInstanceUID", "")).strip()
        for _, dataset in parsed
        if str(getattr(dataset, "StudyInstanceUID", "")).strip()
    }
    series_uids = {
        str(getattr(dataset, "SeriesInstanceUID", "")).strip()
        for _, dataset in mr_images
        if str(getattr(dataset, "SeriesInstanceUID", "")).strip()
    }
    if len(patient_ids) > 1:
        raise ValueError(
            "The scan folder contains multiple PatientID values. Split it into one patient "
            "case before processing; identifiers are deliberately not written to the manifest."
        )
    if len(study_uids) > 1:
        raise ValueError(
            "The scan folder contains multiple study UIDs. Select one CMR study to prevent "
            "accidental mixing of acquisitions."
        )

    digest = hashlib.sha256()
    for path, _ in sorted(parsed, key=lambda item: item[0].relative_to(scan_dir).as_posix()):
        relative = path.relative_to(scan_dir).as_posix()
        digest.update(relative.encode("utf-8", errors="replace"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(_sha256_file(path)))

    return {
        "modality": "MR",
        "file_count": len(parsed),
        "mr_image_instance_count": len(mr_images),
        "series_count": len(series_uids),
        "bytes": total_bytes,
        "source_sha256": digest.hexdigest(),
        "modalities_present": modalities,
        "patient_identifiers_recorded": False,
        "note": (
            "Source paths, PatientID, patient name, accession number and study/series UIDs "
            "are not copied into this manifest."
        ),
    }


def _build_bivme_config(
    *,
    template: Path,
    output_path: Path,
    input_root: Path,
    output_root: Path,
    review_mode: str,
    workers: int,
) -> None:
    text = template.read_text(encoding="utf-8")
    path_values = {
        ("input_pp", "source"): str(input_root.resolve()),
        ("input_pp", "batch_ID"): "cardianatomy-scan",
        ("input_pp", "analyst_id"): "cardianatomy",
        ("input_pp", "processing"): str((output_root / "processing").resolve()),
        ("input_pp", "states"): str((output_root / "states").resolve()),
        ("output_pp", "output_directory"): str((output_root / "guidepoints").resolve()),
        ("input_fitting", "gp_directory"): str(
            (output_root / "guidepoints" / "cardianatomy-scan").resolve()
        ),
        ("output_fitting", "output_directory"): str((output_root / "fitted-models").resolve()),
    }
    for (section, key), value in path_values.items():
        text = _replace_toml_value(text, section, key, _toml_string(value))

    values = {
        ("modules", "preprocessing"): "true",
        ("modules", "fitting"): "true",
        ("view-selection", "correct_mode"): _toml_string(review_mode),
        ("view-selection", "show_videos"): "true",
        ("output_pp", "overwrite"): "false",
        ("output_fitting", "overwrite"): "false",
        ("output_fitting", "mesh_format"): _toml_string(".vtk"),
        ("output_fitting", "output_meshes"): '["LV_ENDOCARDIAL", "RV_ENDOCARDIAL", "EPICARDIAL"]',
        ("output_fitting", "closed_mesh"): "false",
        ("plotting", "generate_plots_fitting"): "true",
        ("plotting", "include_images"): "true",
        ("plotting", "export_images"): "false",
        ("multiprocessing", "workers"): str(workers),
    }
    for (section, key), value in values.items():
        text = _replace_toml_value(text, section, key, value)

    # Parse/shape checks are delegated to upstream biv-me itself. Only write the
    # generated config once all required path/value substitutions have succeeded.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")


def _run_logged(
    argv: list[str],
    *,
    cwd: Path,
    log_path: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    started = time.monotonic()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with log_path.open("w", encoding="utf-8", errors="replace") as log:
            log.write("Command: " + json.dumps(argv) + "\n")
            log.flush()
            completed = subprocess.run(
                argv,
                cwd=str(cwd),
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=timeout_seconds,
                check=False,
                shell=False,
            )
        return {
            "returncode": int(completed.returncode),
            "timed_out": False,
            "duration_seconds": round(time.monotonic() - started, 3),
            "log": str(log_path),
        }
    except subprocess.TimeoutExpired:
        with log_path.open("a", encoding="utf-8", errors="replace") as log:
            log.write(f"\nTimed out after {timeout_seconds} seconds.\n")
        return {
            "returncode": 124,
            "timed_out": True,
            "duration_seconds": round(time.monotonic() - started, 3),
            "log": str(log_path),
        }


def _artifact_inventory(root: Path, fitted_root: Path, metrics_root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    candidates: list[Path] = []
    for base in (fitted_root, metrics_root):
        if base.exists():
            candidates.extend(
                path for path in base.rglob("*")
                if path.is_file()
                and path.name.lower().endswith(
                    (".vtk", ".obj", ".html", ".csv", ".txt", ".nii", ".nii.gz", ".json")
                )
            )
    unique = sorted(set(candidates), key=lambda path: path.as_posix())
    output: list[dict[str, Any]] = []
    for path in unique[:_MAX_MANIFEST_ARTIFACTS]:
        try:
            output.append({
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
                "format": (
                    "nii.gz"
                    if path.name.lower().endswith(".nii.gz")
                    else path.suffix.lower().lstrip(".")
                ),
            })
        except OSError:
            continue
    return output


def _run_metrics(
    *,
    python_executable: str,
    bivme_root: Path,
    fitted_root: Path,
    metrics_root: Path,
    case_id: str,
    analysis_timeout_seconds: int,
) -> dict[str, Any]:
    """Run upstream quantitative volume and strain routines; choose ED from max LV volume."""
    metrics_root.mkdir(parents=True, exist_ok=True)
    analysis_root = bivme_root / "src" / "bivme" / "analysis"
    results: dict[str, Any] = {}

    def run_one(name: str, script: str, extra: list[str] | None = None) -> dict[str, Any]:
        path = analysis_root / script
        if not path.is_file():
            return {
                "status": "unavailable",
                "reason": f"Upstream analysis script missing: {script}",
            }
        argv = [
            python_executable,
            str(path),
            "-mdir", str(fitted_root),
            "-o", str(metrics_root),
            "-pat", case_id,
        ] + (extra or [])
        run_result = _run_logged(
            argv,
            cwd=bivme_root,
            log_path=metrics_root / "logs" / f"{name}.log",
            timeout_seconds=analysis_timeout_seconds,
        )
        return {
            "status": (
                "completed"
                if run_result["returncode"] == 0 and not run_result["timed_out"]
                else "failed"
            ),
            "returncode": run_result["returncode"],
            "timed_out": run_result["timed_out"],
            "duration_seconds": run_result["duration_seconds"],
            "log": str(Path(run_result["log"]).relative_to(metrics_root.parent)),
        }

    volume_result = run_one("volumes", "compute_volume.py", ["-p", "2"])
    volumes_file = metrics_root / "lvrv_volumes.csv"
    ed_frame: int | None = None
    usable_rows = 0
    if volume_result["status"] == "completed" and volumes_file.is_file():
        try:
            with volumes_file.open(newline="", encoding="utf-8") as handle:
                rows = [
                    row for row in csv.DictReader(handle)
                    if row.get("name") == case_id
                    and row.get("lv_vol") not in {"", None}
                    and row.get("frame") not in {"", None}
                ]
            parsed_rows = []
            for row in rows:
                try:
                    parsed_rows.append((int(float(row["frame"])), float(row["lv_vol"])))
                except (TypeError, ValueError, OverflowError):
                    continue
            usable_rows = len(parsed_rows)
            if parsed_rows:
                ed_frame = max(parsed_rows, key=lambda item: item[1])[0]
        except (OSError, csv.Error, UnicodeError):
            ed_frame = None
    volume_result["usable_frame_count"] = usable_rows
    volume_result["end_diastolic_frame_selected_by_max_lv_volume"] = ed_frame
    results["volumes"] = volume_result

    if ed_frame is None:
        results["circumferential_strain"] = {
            "status": "skipped",
            "reason": "A usable LV-volume curve was not available to select an ED reference frame.",
        }
        results["longitudinal_strain"] = {
            "status": "skipped",
            "reason": "A usable LV-volume curve was not available to select an ED reference frame.",
        }
    else:
        results["circumferential_strain"] = run_one(
            "circumferential-strain", "compute_global_circumferential_strain.py",
            ["-ed", str(ed_frame), "-p", "2"],
        )
        results["longitudinal_strain"] = run_one(
            "longitudinal-strain", "compute_global_longitudinal_strain.py",
            ["-ed", str(ed_frame), "-p", "2"],
        )

    results["wall_thickness"] = run_one(
        "wall-thickness", "compute_wall_thickness.py", ["-r", "1.0"]
    )
    results["interpretation_note"] = (
        "These are upstream model-derived measurements. The ED reference was selected from "
        "the maximum modeled LV cavity volume when available; review the frame choice and "
        "contour/model overlays before interpreting the values. The measurements are not "
        "independently clinically validated by this wrapper."
    )
    return results


def run_biv_me_scan_to_twin(
    dicom_case: str | Path,
    *,
    biv_me_root: str | Path,
    output_root: str | Path,
    python_executable: str | Path = "python",
    case_id: str | None = None,
    review_mode: str = "adaptive",
    workers: int = 4,
    timeout_seconds: int = 43_200,
    analysis_timeout_seconds: int = 1_800,
    calculate_metrics: bool = True,
) -> dict[str, Any]:
    """Build a biventricular patient-specific surface model from one cine-CMR DICOM case.

    The scan is processed locally. The generated bundle contains no raw DICOM pixels,
    DICOM patient identifiers, original source path, or study/series UIDs.
    """
    scan_arg = Path(dicom_case).expanduser()
    if not scan_arg.is_dir():
        raise ValueError(f"Input scan directory does not exist: {scan_arg}")
    scan_dir = scan_arg.absolute()
    root_arg = Path(output_root).expanduser()
    root = root_arg.absolute()
    try:
        scan_resolved = scan_dir.resolve(strict=True)
        root_resolved = root.resolve(strict=False)
    except OSError as exc:
        raise ValueError("Could not resolve input/output paths") from exc
    if (
        scan_resolved == root_resolved
        or scan_resolved in root_resolved.parents
        or root_resolved in scan_resolved.parents
    ):
        raise ValueError("Input scan directory and output directory must be disjoint")
    if root.exists() and any(root.iterdir()):
        raise ValueError(
            f"Output directory is not empty: {root}. "
            "Choose a new output directory to preserve existing work."
        )
    if review_mode not in {"manual", "adaptive", "automatic"}:
        raise ValueError("review_mode must be manual, adaptive, or automatic")
    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= 64:
        raise ValueError("workers must be an integer in [1, 64]")
    for name, value in (
        ("timeout_seconds", timeout_seconds),
        ("analysis_timeout_seconds", analysis_timeout_seconds),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")

    scan_summary = _summarize_cine_cmr(scan_resolved)
    if case_id is None:
        case_id = "case-" + scan_summary["source_sha256"][:12]
    if not _SAFE_CASE_ID.fullmatch(case_id):
        raise ValueError(
            "case_id must be a short pseudonymous identifier matching letters/numbers, dot, "
            "underscore or hyphen; use a neutral pseudonymous identifier only."
        )

    bime_root = Path(biv_me_root).expanduser().resolve()
    main_script = bime_root / "src" / "bivme" / "main.py"
    template = bime_root / "src" / "bivme" / "configs" / "config.toml"
    if not main_script.is_file() or not template.is_file():
        raise ValueError(
            f"biv-me checkout is incomplete at {bime_root}. Expected src/bivme/main.py and "
            "src/bivme/configs/config.toml."
        )
    version = _probe_python_version(python_executable)
    if version[:2] != (3, 11):
        raise ValueError(
            f"biv-me's current documented environment is Python 3.11; selected interpreter is "
            f"{version[3]}. Pass --python-executable for the Python 3.11 biv-me environment."
        )
    _check_importable_bivme(python_executable, bime_root)
    model_summary = _model_assets(bime_root)
    try:
        rev = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(bime_root),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            shell=False,
        )
        upstream_commit = rev.stdout.strip() if rev.returncode == 0 else "unknown"
    except (OSError, subprocess.TimeoutExpired):
        upstream_commit = "unknown"

    root.mkdir(parents=True, exist_ok=True)
    staging_root = root / "staging" / "dicoms"
    staging_root.mkdir(parents=True, exist_ok=True)
    case_link = staging_root / case_id
    try:
        os.symlink(str(scan_resolved), str(case_link), target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        raise ValueError(
            "Could not create a no-copy case alias for privacy-preserving processing. On this "
            "system, rename/copy the input directory to a pseudonymous case ID and ensure "
            "directory symlinks are permitted, or run this workflow in Linux/WSL."
        ) from exc

    for folder in (
        "config", "processing", "states", "guidepoints",
        "fitted-models", "metrics", "logs",
    ):
        (root / folder).mkdir(parents=True, exist_ok=True)
    config_path = root / "config" / "bivme-generated.toml"
    _build_bivme_config(
        template=template,
        output_path=config_path,
        input_root=staging_root,
        output_root=root,
        review_mode=review_mode,
        workers=workers,
    )

    command = [
        str(python_executable),
        str(main_script),
        "-config", str(config_path),
        "-case", case_id,
    ]
    start = time.monotonic()
    main_result = _run_logged(
        command,
        cwd=bime_root,
        log_path=root / "logs" / "biv-me.log",
        timeout_seconds=timeout_seconds,
    )
    fitted_root = root / "fitted-models"
    fitted_case = fitted_root / case_id
    surface_files = sorted(
        path for path in fitted_case.rglob("*")
        if path.is_file() and path.suffix.lower() in {".vtk", ".obj"}
    ) if fitted_case.exists() else []
    html_files = sorted(
        path for path in fitted_case.rglob("*.html") if path.is_file()
    ) if fitted_case.exists() else []
    expected_surface_types = {
        "LV_ENDOCARDIAL",
        "RV_ENDOCARDIAL",
        "EPICARDIAL",
    }
    observed_surface_types = {
        surface_type
        for path in surface_files
        for surface_type in expected_surface_types
        if surface_type in path.name.upper()
    }
    missing_surface_types = sorted(expected_surface_types - observed_surface_types)
    core_success = (
        main_result["returncode"] == 0
        and not main_result["timed_out"]
        and not missing_surface_types
    )

    metric_results: dict[str, Any] = {
        "status": "not_requested",
        "note": "Quantitative post-processing was not requested.",
    }
    if core_success and calculate_metrics:
        metric_results = _run_metrics(
            python_executable=str(python_executable),
            bivme_root=bime_root,
            fitted_root=fitted_root,
            metrics_root=root / "metrics",
            case_id=case_id,
            analysis_timeout_seconds=analysis_timeout_seconds,
        )
        individual = [
            value.get("status") for key, value in metric_results.items()
            if key != "interpretation_note" and isinstance(value, dict)
        ]
        metric_results["status"] = (
            "completed" if individual and all(status == "completed" for status in individual)
            else "partial"
        )

    artifacts = _artifact_inventory(root, fitted_root, root / "metrics")
    analysis_status = metric_results.get("status", "not_requested")
    if core_success:
        workflow_status = (
            "completed"
            if analysis_status in {"completed", "not_requested"}
            else "completed_with_analysis_warnings"
        )
    else:
        workflow_status = "failed_or_incomplete"

    manifest: dict[str, Any] = {
        "schema_version": "1.0.0",
        "workflow": "cardianatomy.scan-to-twin.biv-me",
        "workflow_status": workflow_status,
        "created_at_utc": _utc_now(),
        "case_id": case_id,
        "input": scan_summary,
        "engine": {
            "name": "biv-me",
            "repository": _BIVME_URL,
            "license": "Apache-2.0",
            "upstream_commit": upstream_commit,
            "python_version": version[3],
            "model_repository": _BIVME_MODEL_URL,
            "model_asset_check": model_summary,
            "review_mode": review_mode,
            "review_required_before_interpretation": True,
        },
        "execution": {
            "returncode": main_result["returncode"],
            "timed_out": main_result["timed_out"],
            "duration_seconds": round(time.monotonic() - start, 3),
            "log_path": "logs/biv-me.log",
            "config_path": "config/bivme-generated.toml",
            "config_sha256": _sha256_file(config_path),
            "surface_mesh_count": len(surface_files),
            "expected_surface_types": sorted(expected_surface_types),
            "observed_surface_types": sorted(observed_surface_types),
            "missing_surface_types": missing_surface_types,
            "html_report_count": len(html_files),
        },
        "quantitative_analysis": metric_results,
        "artifacts": artifacts,
        "scope": {
            "delivered": [
                "patient-specific moving biventricular surface meshes from cine-CMR DICOM",
                "upstream fit/contour visualizations for review",
                "model-derived LV/RV volumes and mass, strain, and wall-thickness "
                "outputs when their analyses succeed",
                "hashed manifest of generated research artifacts",
            ],
            "not_established": [
                "complete four-chamber (atria plus ventricles) simulation-ready volume mesh",
                "patient-specific fibre/sheet fields or LGE-derived scar mapping "
                "in the downstream solver mesh",
                "personalized electrophysiology with calibrated lead fields, "
                "Purkinje system and ECG fit",
                "calibrated three-dimensional active mechanics or patient-specific CFD/FSI",
                "cross-domain calibrated whole-heart digital twin",
                "clinical validation, diagnostic accuracy or treatment-planning suitability",
            ],
            "next_required_stages": [
                "review the fitted contours and all available model/image overlays",
                "create or import a simulation-grade labelled volumetric mesh "
                "with reviewed cavity faces",
                "derive/validate fibre fields and scar mapping where corresponding imaging exists",
                "bind patient ECG/electrode, pressure, flow, strain and volume "
                "observations to explicit solver inputs",
                "calibrate and independently validate electrical, mechanical "
                "and circulation models with held-out measurements",
            ],
        },
        "privacy": {
            "source_directory_path_stored": False,
            "patient_identifiers_stored": False,
            "raw_pixels_copied_to_output": False,
            "processing_mode": (
                "local subprocess; scan is exposed to upstream through a local directory symlink"
            ),
            "warning": (
                "Treat output folders, generated HTML, intermediates and logs as private "
                "research data. Review before sharing."
            ),
        },
    }
    manifest_path = root / "scan-to-twin-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return manifest
