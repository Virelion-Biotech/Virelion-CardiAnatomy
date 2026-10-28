"""Fail-closed preflight for cardiac views before volumetric meshing."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REQUIRED = ("SAX", "LAX_2CH", "LAX_3CH", "LAX_4CH")


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_volume_mesh_inputs(
    views: dict[str, str | Path],
    *,
    output_manifest: str | Path | None = None,
    max_voxels: int = 2_000_000_000,
) -> dict[str, Any]:
    """Check four prepared NIfTI views; this does not register, segment, or mesh them."""
    missing = sorted(set(_REQUIRED) - set(views))
    extra = sorted(set(views) - set(_REQUIRED))
    if missing or extra:
        raise ValueError(
            f"Expected exactly {_REQUIRED}; missing={missing}, unexpected={extra}"
        )
    if max_voxels < 1:
        raise ValueError("max_voxels must be positive")

    try:
        import nibabel as nib
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            'Install optional I/O dependencies with python -m pip install -e ".[io]".'
        ) from exc

    records = {}
    orientations = {}
    total = 0
    for view in _REQUIRED:
        path = Path(views[view]).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"{view} input is not a readable file")
        if not path.name.lower().endswith((".nii", ".nii.gz")):
            raise ValueError(f"{view} must be a .nii or .nii.gz file")
        try:
            image = nib.load(str(path))
            shape = tuple(int(x) for x in image.shape)
            affine = image.affine
        except Exception as exc:
            raise ValueError(f"{view} is not a readable NIfTI image") from exc

        if len(shape) not in (3, 4) or any(x < 1 for x in shape):
            raise ValueError(f"{view} must have a non-empty 3D or 4D array")
        count = math.prod(shape)
        total += count
        if total > max_voxels:
            raise ValueError(
                f"Combined input voxel count exceeds safety limit {max_voxels}"
            )
        if not all(math.isfinite(float(x)) for x in affine.flat):
            raise ValueError(f"{view} affine contains non-finite values")

        determinant = float(np.linalg.det(affine[:3, :3]))
        spacing = tuple(float(x) for x in nib.affines.voxel_sizes(affine)[:3])
        if not math.isfinite(determinant) or abs(determinant) < 1e-10:
            raise ValueError(f"{view} affine is singular or degenerate")
        if any(not math.isfinite(x) or x <= 0 for x in spacing):
            raise ValueError(f"{view} has invalid voxel spacing")

        codes = tuple(str(x or "") for x in nib.aff2axcodes(affine))
        if len(codes) != 3 or any(not x for x in codes):
            raise ValueError(f"{view} orientation could not be inferred from affine")
        orientations[view] = codes
        records[view] = {
            "file_name": path.name,
            "sha256": _hash(path),
            "format": "NIfTI",
            "shape": list(shape),
            "voxel_spacing_mm": [round(x, 8) for x in spacing],
            "axis_codes": list(codes),
            "affine_ras": [
                [round(float(x), 10) for x in row] for row in affine
            ],
            "voxel_count": count,
        }

    if len(set(orientations.values())) != 1:
        observed = json.dumps(
            {key: list(value) for key, value in orientations.items()},
            sort_keys=True,
        )
        raise ValueError(
            "Cardiac views use inconsistent affine axis-code conventions; "
            f"explicitly reorient/register them first. Observed: {observed}"
        )

    manifest = {
        "schema_version": "cardianatomy.volume-mesh-preflight/1.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "preflight_passed_registration_unverified",
        "backend": {
            "name": "not_run",
            "note": "No meshing backend invoked; no mesh generated.",
        },
        "inputs": records,
        "checks": {
            "required_views_present": True,
            "nifti_readable": True,
            "affines_finite_and_nonsingular": True,
            "positive_voxel_spacing": True,
            "axis_code_conventions_consistent": True,
            "spatial_registration_verified": False,
            "segmentation_labels_verified": False,
            "mesh_quality_verified": False,
        },
        "total_input_voxels": total,
        "limitations": [
            "Matching axis codes do not prove spatial registration.",
            (
                "No segmentation, meshing, topology, element-quality, or "
                "anatomical-accuracy claim is made."
            ),
            "Review image overlays and registration transforms before meshing.",
            "Manifest records basenames and hashes, not absolute paths or DICOM identifiers.",
        ],
    }

    if output_manifest is not None:
        dest = Path(output_manifest).expanduser()
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            raise ValueError(f"Refusing to overwrite existing manifest: {dest}")
        temp = dest.with_name(dest.name + ".tmp")
        try:
            serialized = json.dumps(
                manifest, indent=2, sort_keys=True, allow_nan=False
            ) + "\n"
            temp.write_text(serialized, encoding="utf-8")
            temp.replace(dest)
        finally:
            if temp.exists():
                temp.unlink()
        manifest["manifest_written_to"] = dest.name

    return manifest
