from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .models import DicomSeriesSummary, MeshInspection
from .provenance import sha256
from .qc import inspect_tetra_mesh, inspect_triangle_surface


def _positive_int_or_none(
    value: Any,
    name: str,
    warnings: list[str],
) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        warnings.append(f"invalid {name}")
        return None
    if parsed < 1:
        warnings.append(f"invalid {name}")
        return None
    return parsed


def _positive_float_or_none(
    value: Any,
    name: str,
    warnings: list[str],
) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        warnings.append(f"invalid {name}")
        return None
    if not np.isfinite(parsed) or parsed <= 0:
        warnings.append(f"invalid {name}")
        return None
    return parsed


def _float_tuple_or_none(
    value: Any,
    *,
    name: str,
    length: int,
    warnings: list[str],
    positive: bool = False,
) -> tuple[float, ...] | None:
    if value is None:
        return None
    try:
        parsed = tuple(float(item) for item in value)
    except (TypeError, ValueError, OverflowError):
        warnings.append(f"invalid {name}")
        return None
    if (
        len(parsed) != length
        or not np.all(np.isfinite(parsed))
        or (positive and any(item <= 0 for item in parsed))
    ):
        warnings.append(f"invalid {name}")
        return None
    return parsed


def inspect_dicom_directory(path: str | Path) -> list[DicomSeriesSummary]:
    """Inspect DICOM geometry metadata without returning direct patient identifiers."""
    try:
        import pydicom
    except ImportError as exc:
        raise RuntimeError("Install virelion-cardianatomy[io] for DICOM support") from exc

    root = Path(path)
    if not root.is_dir():
        raise ValueError(f"DICOM directory does not exist: {root}")
    series: dict[str, tuple[Any, int]] = {}
    for file in sorted(p for p in root.rglob("*") if p.is_file()):
        try:
            ds = pydicom.dcmread(str(file), stop_before_pixels=True, force=False)
        except Exception:
            continue
        uid = str(getattr(ds, "SeriesInstanceUID", ""))
        if uid:
            if uid in series:
                first, count = series[uid]
                series[uid] = (first, count + 1)
            else:
                series[uid] = (ds, 1)
    output: list[DicomSeriesSummary] = []
    for uid, (first, file_count) in series.items():
        warnings: list[str] = []
        spacing = _float_tuple_or_none(
            getattr(first, "PixelSpacing", None),
            name="PixelSpacing",
            length=2,
            warnings=warnings,
            positive=True,
        )
        orientation_raw = getattr(first, "ImageOrientationPatient", None)
        orientation = _float_tuple_or_none(
            orientation_raw,
            name="ImageOrientationPatient",
            length=6,
            warnings=warnings,
        )
        if orientation_raw is None:
            warnings.append("missing ImageOrientationPatient")
        output.append(
            DicomSeriesSummary(
                series_uid_sha256=sha256(uid),
                modality=str(getattr(first, "Modality", "")) or None,
                description=str(getattr(first, "SeriesDescription", "")) or None,
                file_count=file_count,
                rows=_positive_int_or_none(
                    getattr(first, "Rows", None),
                    "Rows",
                    warnings,
                ),
                columns=_positive_int_or_none(
                    getattr(first, "Columns", None),
                    "Columns",
                    warnings,
                ),
                pixel_spacing_mm=spacing,
                slice_thickness_mm=_positive_float_or_none(
                    getattr(first, "SliceThickness", None),
                    "SliceThickness",
                    warnings,
                ),
                temporal_positions=_positive_int_or_none(
                    getattr(first, "NumberOfTemporalPositions", None),
                    "NumberOfTemporalPositions",
                    warnings,
                ),
                image_orientation_patient=orientation,
                warnings=warnings,
            )
        )
    return sorted(output, key=lambda item: (-item.file_count, item.series_uid_sha256))


def inspect_nifti(path: str | Path) -> dict[str, Any]:
    try:
        import nibabel as nib
    except ImportError as exc:
        raise RuntimeError("Install virelion-cardianatomy[io] for NIfTI support") from exc
    image = nib.load(str(path))
    zooms = tuple(float(x) for x in image.header.get_zooms())
    return {
        "path": str(path),
        "shape": tuple(int(x) for x in image.shape),
        "voxel_spacing": zooms,
        "affine": np.asarray(image.affine, dtype=float).tolist(),
        "finite_affine": bool(np.all(np.isfinite(image.affine))),
    }


def inspect_mesh_file(path: str | Path) -> MeshInspection:
    try:
        import meshio
    except ImportError as exc:
        raise RuntimeError("Install virelion-cardianatomy[io] for mesh-file support") from exc
    mesh = meshio.read(str(path))
    points = np.asarray(mesh.points[:, :3], dtype=float)
    tetra_blocks = [block.data for block in mesh.cells if block.type in {"tetra", "tetra10"}]
    triangle_blocks = [
        block.data for block in mesh.cells if block.type in {"triangle", "triangle6"}
    ]
    if tetra_blocks:
        tetra = np.vstack([np.asarray(block)[:, :4] for block in tetra_blocks])
        inspection = inspect_tetra_mesh(points, tetra)
    elif triangle_blocks:
        triangles = np.vstack([np.asarray(block)[:, :3] for block in triangle_blocks])
        inspection = inspect_triangle_surface(points, triangles)
    else:
        inspection = MeshInspection(
            path=str(path),
            point_count=len(points),
            cell_count=sum(len(block.data) for block in mesh.cells),
            finite=bool(np.all(np.isfinite(points))),
            metadata={"cell_types": [block.type for block in mesh.cells]},
        )
    return inspection.model_copy(update={"path": str(path)})
