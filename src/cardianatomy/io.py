from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .models import DicomSeriesSummary, MeshInspection
from .provenance import sha256
from .qc import inspect_tetra_mesh, inspect_triangle_surface
from .transforms import validate_affine


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


def inspect_dicom_directory(
    path: str | Path,
    *,
    include_free_text: bool = False,
    max_files: int = 100_000,
) -> list[DicomSeriesSummary]:
    """Inspect DICOM geometry metadata without returning direct patient identifiers.

    Free-text fields such as SeriesDescription are redacted by default because
    clinical systems may place patient identifiers in them.
    """
    try:
        import pydicom
    except ImportError as exc:
        raise RuntimeError("Install virelion-cardianatomy[io] for DICOM support") from exc

    root = Path(path)
    if not root.is_dir():
        raise ValueError(f"DICOM directory does not exist: {root}")
    if (
        isinstance(max_files, bool)
        or not isinstance(max_files, int)
        or max_files < 1
    ):
        raise ValueError("max_files must be a positive integer")
    series: dict[str, tuple[Any, int, str]] = {}
    scanned = 0
    for file in root.rglob("*"):
        if not file.is_file():
            continue
        scanned += 1
        if scanned > max_files:
            raise ValueError(
                f"DICOM directory exceeds max_files={max_files}"
            )
        try:
            ds = pydicom.dcmread(str(file), stop_before_pixels=True, force=False)
        except Exception:
            continue
        uid = str(getattr(ds, "SeriesInstanceUID", ""))
        if uid:
            file_key = str(file)
            if uid in series:
                first, count, first_key = series[uid]
                if file_key < first_key:
                    first = ds
                    first_key = file_key
                series[uid] = (first, count + 1, first_key)
            else:
                series[uid] = (ds, 1, file_key)
    output: list[DicomSeriesSummary] = []
    for uid, (first, file_count, _) in series.items():
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
                description=(
                    str(getattr(first, "SeriesDescription", "")) or None
                    if include_free_text
                    else None
                ),
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

    source = Path(path)
    if not source.is_file():
        raise ValueError(f"NIfTI file does not exist: {source}")

    image = nib.load(str(source))
    shape = tuple(int(x) for x in image.shape)
    zooms = tuple(float(x) for x in image.header.get_zooms())
    warnings: list[str] = []

    spacing_valid = bool(
        zooms
        and np.all(np.isfinite(zooms))
        and all(value > 0 for value in zooms)
    )
    if not spacing_valid:
        warnings.append("invalid voxel spacing")

    affine = np.asarray(image.affine, dtype=float)
    finite_affine = bool(
        affine.shape == (4, 4)
        and np.all(np.isfinite(affine))
    )
    affine_valid = False
    if finite_affine:
        try:
            validate_affine(affine)
        except ValueError:
            warnings.append("invalid affine transform")
        else:
            affine_valid = True
    else:
        warnings.append("non-finite or malformed affine")

    if not shape or any(value <= 0 for value in shape):
        warnings.append("invalid image shape")

    return {
        "path": str(source),
        "shape": shape,
        "voxel_spacing": zooms if spacing_valid else None,
        "affine": affine.tolist() if finite_affine else None,
        "finite_affine": finite_affine,
        "valid_affine": affine_valid,
        "warnings": warnings,
    }


def inspect_mesh_file(path: str | Path) -> MeshInspection:
    try:
        import meshio
    except ImportError as exc:
        raise RuntimeError("Install virelion-cardianatomy[io] for mesh-file support") from exc
    with Path(path).open("rb") as handle:
        header = handle.read(512).decode("ascii", errors="ignore")
    if "DATASET POLYDATA" in header:
        from .polydata import read_triangle_polydata

        points, triangles = read_triangle_polydata(path)
        inspection = inspect_triangle_surface(points, triangles)
        inspection.metadata["reader"] = "legacy_ascii_polydata_geometry_only"
        return inspection.model_copy(update={"path": str(path)})
    try:
        mesh = meshio.read(str(path))
    except SystemExit as exc:
        raise ValueError("Unsupported or malformed mesh file") from exc
    if any(block.type in {"tetra10", "triangle6"} for block in mesh.cells):
        raise ValueError("Higher-order mesh QC is unsupported; linearize explicitly upstream")
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
