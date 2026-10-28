"""Auditable adapter for the upstream BiV volumetric-meshing pipeline.

This module orchestrates the external Apache-2.0 project; it does not copy its
algorithms, model weights, datasets, or openCARP runtime into CardiAnatomy.
Prepared input views are copied into a fresh case workspace and never modified.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .integrations.catalog import require_tool_policy
from .integrations.commands import biv_volumetric_command, run_command
from .io import inspect_mesh_file
from .qc import qc_from_inspection
from .volume_mesh_preflight import validate_volume_mesh_inputs

UPSTREAM_URL = "https://github.com/cdttk/biv-volumetric-meshing"
_VIEW_FILES = {
    "SAX": "SAX.nii.gz",
    "LAX_2CH": "LAX_2Ch.nii.gz",
    "LAX_3CH": "LAX_3Ch.nii.gz",
    "LAX_4CH": "LAX_4Ch.nii.gz",
}
_STAGES = ("segmentation", "contour", "surface", "volumetric", "uvc-fiber")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
_MESH_SUFFIXES = {".vtk", ".vtu", ".msh", ".xdmf", ".xmf", ".inp", ".mesh"}
_MAX_STAGE_ARTIFACTS = 20_000


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _safe_empty_root(path: Path) -> None:
    if path.is_symlink():
        raise ValueError("Output root must not be a symbolic link")
    if path.exists():
        if not path.is_dir():
            raise ValueError("Output root exists and is not a directory")
        if any(path.iterdir()):
            raise ValueError(f"Refusing to overwrite non-empty output root: {path}")
    else:
        path.mkdir(parents=True, exist_ok=False)


def _snapshot(data_root: Path, excluded_inputs: set[str]) -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    if not data_root.exists():
        return result
    for path in data_root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(data_root).as_posix()
        if relative in excluded_inputs:
            continue
        stat = path.stat()
        result[relative] = (stat.st_size, stat.st_mtime_ns)
    return result


def _is_log(relative_path: str) -> bool:
    lowered = relative_path.lower()
    return lowered.endswith((".log", ".log.txt")) or "/logs/" in f"/{lowered}/"


def _changed_artifacts(
    data_root: Path,
    before: dict[str, tuple[int, int]],
    excluded_inputs: set[str],
) -> list[dict[str, Any]]:
    after = _snapshot(data_root, excluded_inputs)
    changed = [
        path for path, stat in after.items()
        if before.get(path) != stat and not _is_log(path)
    ]
    if len(changed) > _MAX_STAGE_ARTIFACTS:
        raise ValueError(
            f"Stage produced more than {_MAX_STAGE_ARTIFACTS} changed artifacts; "
            "review the output layout before proceeding."
        )
    artifacts = []
    for relative in sorted(changed):
        path = data_root / relative
        artifacts.append({
            "path": relative,
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
        })
    return artifacts


def _upstream_revision(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = result.stdout.strip()
    if result.returncode != 0 or not re.fullmatch(r"[0-9a-fA-F]{40,64}", value):
        return None
    return value


def _prepare_view_images(
    views: dict[str, str | Path],
    destination: Path,
    preflight: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    try:
        import nibabel as nib
    except ImportError as exc:
        raise RuntimeError(
            'NIfTI handling requires the I/O extras; install with pip install -e ".[io]".'
        ) from exc

    destination.mkdir(parents=True, exist_ok=False)
    records: dict[str, dict[str, Any]] = {}
    for key, filename in _VIEW_FILES.items():
        source = Path(views[key]).expanduser().resolve()
        target = destination / filename
        image = nib.load(str(source))
        nib.save(image, str(target))
        staged = nib.load(str(target))
        if tuple(staged.shape) != tuple(image.shape):
            raise ValueError(f"Staged {key} image changed shape during NIfTI conversion")
        if not np.allclose(staged.affine, image.affine, rtol=0.0, atol=1e-5):
            raise ValueError(f"Staged {key} image changed affine during NIfTI conversion")
        records[key] = {
            "upstream_filename": filename,
            "source_sha256": preflight["inputs"][key]["sha256"],
            "staged_sha256": _sha256(target),
            "shape": [int(value) for value in staged.shape],
            "voxel_spacing_mm": [
                round(float(value), 8)
                for value in nib.affines.voxel_sizes(staged.affine)[:3]
            ],
            "affine_ras": [
                [round(float(value), 10) for value in row]
                for row in staged.affine
            ],
            "conversion": "NIfTI re-serialized by nibabel to upstream-required .nii.gz filename",
        }
    return records


def _inspect_volume_meshes(data_root: Path) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for path in sorted(data_root.rglob("*")):
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in _MESH_SUFFIXES:
            continue
        try:
            inspection = inspect_mesh_file(path)
        except Exception:
            # Some supported mesh extensions can still contain unsupported or
            # malformed datasets; one bad candidate must not hide other outputs.
            continue
        if not inspection.tetra_count:
            continue
        qc = qc_from_inspection(inspection)
        candidates.append({
            "path": path.relative_to(data_root).as_posix(),
            "sha256": _sha256(path),
            "size_bytes": path.stat().st_size,
            "point_count": inspection.point_count,
            "tetra_count": inspection.tetra_count,
            "connected_components": inspection.connected_components,
            "degenerate_fraction": inspection.degenerate_fraction,
            "minority_orientation_fraction": inspection.minority_orientation_fraction,
            "shape_metrics": {
                key: value
                for key, value in inspection.metadata.items()
                if key.startswith("tetra_") and isinstance(value, (int, float))
            },
            "qc": qc.model_dump(mode="json"),
        })
    return sorted(
        candidates,
        key=lambda item: (
            bool(item["qc"]["passed"]),
            int(item["tetra_count"]),
        ),
        reverse=True,
    )


def run_biv_volumetric_pipeline(
    views: dict[str, str | Path],
    *,
    upstream_root: str | Path,
    output_root: str | Path,
    stages: Sequence[str] = ("segmentation", "contour", "surface"),
    subject_id: str = "cardianatomy_case",
    instance: int = 2,
    timeframe: int | None = None,
    workspace_dir: str | Path | None = None,
    carp_bin_dir: str | Path | None = None,
    allow_restricted_runtime: bool = False,
    gpu: bool = False,
    python_executable: str = "python",
    timeout_seconds: float = 14_400,
) -> dict[str, Any]:
    """Run selected sequential stages with immutable inputs and an audit manifest.

    Volumetric and UVC/fiber stages require explicit acceptance of the upstream
    openCARP runtime's separate licensing requirements.
    """
    if not _SAFE_ID.fullmatch(subject_id):
        raise ValueError("subject_id must be a pseudonymous path-safe identifier")
    if isinstance(instance, bool) or not isinstance(instance, int) or instance < 1:
        raise ValueError("instance must be a positive integer")
    if timeframe is not None and (
        isinstance(timeframe, bool) or not isinstance(timeframe, int) or timeframe < 0
    ):
        raise ValueError("timeframe must be a non-negative integer")
    if not np.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be finite and strictly positive")
    selected = tuple(stages)
    if not selected or selected != _STAGES[:len(selected)] or len(selected) > len(_STAGES):
        raise ValueError("Stages must be a non-empty prefix in order: " + ", ".join(_STAGES))
    if gpu and "segmentation" not in selected:
        raise ValueError("gpu=True only applies when the segmentation stage is selected")

    upstream = Path(upstream_root).expanduser().resolve()
    run_script = upstream / "src" / "run.py"
    if not upstream.is_dir() or not run_script.is_file():
        raise ValueError(
            "upstream_root must be a checkout of cdttk/biv-volumetric-meshing "
            "containing src/run.py"
        )
    if "segmentation" in selected:
        if workspace_dir is None or not Path(workspace_dir).expanduser().is_dir():
            raise ValueError("segmentation requires an existing nnUNet workspace_dir")
    needs_carp = any(stage in selected for stage in ("volumetric", "uvc-fiber"))
    if needs_carp:
        require_tool_policy("opencarp", allow_restricted=allow_restricted_runtime)
        if carp_bin_dir is None or not Path(carp_bin_dir).expanduser().is_dir():
            raise ValueError(
                "volumetric/UVC/fiber stages require carp_bin_dir pointing to the "
                "separately installed openCARP binaries"
            )
    preflight = validate_volume_mesh_inputs(views)
    requested_root = Path(output_root).expanduser()
    if requested_root.is_symlink():
        raise ValueError("Output root must not be a symbolic link")
    root = requested_root.resolve()
    _safe_empty_root(root)
    data_root = root / "data"
    case_dir = data_root / subject_id / f"Instance_{instance}"
    excluded_inputs = {f"{subject_id}/Instance_{instance}/{name}" for name in _VIEW_FILES.values()}
    manifest_path = root / "run-manifest.json"
    log_root = root / "logs"
    log_root.mkdir(parents=True, exist_ok=True)

    try:
        staged_inputs = _prepare_view_images(views, case_dir, preflight)
        manifest: dict[str, Any] = {
            "schema_version": "cardianatomy.biv-volumetric-run/1.0",
            "created_utc": _utc_now(),
            "updated_utc": _utc_now(),
            "status": "running",
            "upstream": {
                "project": "cdttk/biv-volumetric-meshing",
                "url": UPSTREAM_URL,
                "commit_sha": _upstream_revision(upstream),
                "license": "Apache-2.0",
                "runtime_notes": [
                    "nnU-Net model weights and datasets have separate terms and are not bundled.",
                    "Volume/UVC/fiber stages require a separately installed openCARP runtime.",
                    "The openCARP runtime is not bundled and was not license-checked by this program.",
                ],
            },
            "case": {"subject_id": subject_id, "instance": instance, "timeframe": timeframe},
            "inputs": staged_inputs,
            "preflight": {
                "status": preflight["status"],
                "checks": preflight["checks"],
                "limitations": preflight["limitations"],
            },
            "selected_stages": list(selected),
            "stages": [],
            "checks": {
                "input_nifti_validated": True,
                "input_views_registered": False,
                "anatomical_labels_reviewed": False,
                "volume_mesh_qc_passed": False,
                "uvc_quality_verified": False,
                "fiber_quality_verified": False,
                "clinical_validity_established": False,
            },
            "warnings": [
                "Input axis-code agreement does not establish spatial registration.",
                "Review contour/surface overlays against source images before using the geometry.",
                "A passing mesh QC report is geometric evidence, not anatomical or clinical validation.",
                "Generated files and upstream logs may contain sensitive case information; keep this workspace private.",
            ],
        }
        _write_json_atomic(root / "preflight-manifest.json", preflight)
        _write_json_atomic(manifest_path, manifest)

        for stage in selected:
            manifest["current_stage"] = stage
            manifest["updated_utc"] = _utc_now()
            stage_record: dict[str, Any] = {
                "name": stage,
                "status": "running",
                "started_utc": _utc_now(),
            }
            manifest["stages"].append(stage_record)
            _write_json_atomic(manifest_path, manifest)
            before = _snapshot(data_root, excluded_inputs)
            command = biv_volumetric_command(
                run_script=run_script,
                data_dir=data_root,
                components=(stage,),
                subject=subject_id,
                instance=instance,
                timeframe=timeframe,
                workspace_dir=workspace_dir if stage == "segmentation" else None,
                carp_bin_dir=carp_bin_dir if stage in {"volumetric", "uvc-fiber"} else None,
                python_executable=python_executable,
                gpu=(gpu and stage == "segmentation"),
                allow_restricted_runtime=allow_restricted_runtime,
            )
            log_path = log_root / f"{stage}.log"
            try:
                result = run_command(command, timeout=timeout_seconds, cwd=upstream / "src")
                log_path.write_text(
                    "COMMAND: " + json.dumps(command) + "\n\nSTDOUT:\n" + result.stdout
                    + "\n\nSTDERR:\n" + result.stderr,
                    encoding="utf-8",
                )
                outputs = _changed_artifacts(data_root, before, excluded_inputs)
                if not outputs:
                    raise RuntimeError(
                        f"Upstream {stage} stage returned success but no new or modified "
                        "non-log artifacts were detected."
                    )
                stage_record.update({
                    "status": "completed",
                    "finished_utc": _utc_now(),
                    "duration_seconds": round(float(result.duration_seconds), 3),
                    "return_code": int(result.returncode),
                    "log_path": log_path.relative_to(root).as_posix(),
                    "log_sha256": _sha256(log_path),
                    "new_or_modified_artifacts": outputs,
                })
                if stage == "volumetric":
                    candidates = _inspect_volume_meshes(data_root)
                    manifest["volume_mesh_candidates"] = candidates
                    passed = [candidate for candidate in candidates if candidate["qc"]["passed"]]
                    if not passed:
                        raise RuntimeError(
                            "Upstream volumetric command returned success, but no tetrahedral "
                            "mesh passed CardiAnatomy's geometry QC. Outputs were preserved; "
                            "inspect volume_mesh_candidates and the stage log."
                        )
                    manifest["verified_volume_mesh"] = passed[0]
                    manifest["checks"]["volume_mesh_qc_passed"] = True
                if stage == "uvc-fiber":
                    names = [item["path"].lower() for item in outputs]
                    evidence = [
                        name for name in names
                        if "uvc" in name or "fiber" in name or name.endswith((".lon", ".igb"))
                    ]
                    stage_record["uvc_fiber_named_outputs"] = evidence
                    if not evidence:
                        manifest["warnings"].append(
                            "The UVC/fiber command returned success but changed files did not "
                            "include recognizable UVC/fiber names; review upstream outputs."
                        )
                stage_record["artifact_count"] = len(outputs)
                stage_record["finished_utc"] = _utc_now()
                _write_json_atomic(manifest_path, manifest)
            except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
                stage_record.update({
                    "status": "failed",
                    "finished_utc": _utc_now(),
                    "error": str(exc)[-4000:],
                    "log_path": log_path.relative_to(root).as_posix() if log_path.exists() else None,
                })
                manifest["status"] = "failed"
                manifest["failed_stage"] = stage
                manifest["updated_utc"] = _utc_now()
                _write_json_atomic(manifest_path, manifest)
                raise RuntimeError(
                    f"BiV volumetric stage {stage!r} failed; outputs and run manifest "
                    f"were preserved at {root}"
                ) from exc

        manifest["status"] = (
            "completed_volume_mesh_qc_passed"
            if "volumetric" in selected
            else "completed_surface_pipeline_only"
        )
        if "uvc-fiber" in selected:
            manifest["status"] = "completed_volume_mesh_qc_passed_uvc_fiber_quality_unverified"
        manifest["current_stage"] = None
        manifest["updated_utc"] = _utc_now()
        manifest["result_note"] = (
            "Automated software and geometry checks only. Spatial registration, labels, "
            "fiber/UVC validity, anatomical accuracy, and clinical utility require separate review."
        )
        _write_json_atomic(manifest_path, manifest)
        return manifest
    except Exception:
        # Preserve the workspace for debugging; never silently clean partial clinical workflows.
        raise
