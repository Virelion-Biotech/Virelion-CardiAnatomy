from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from .models import DicomSeriesSummary, MeshInspection
from .provenance import sha256
from .qc import inspect_tetra_mesh, inspect_triangle_surface


def inspect_dicom_directory(path: str | Path) -> list[DicomSeriesSummary]:
    """Inspect DICOM geometry metadata without returning direct patient identifiers."""
    try:
        import pydicom
    except ImportError as exc:
        raise RuntimeError("Install virelion-cardianatomy[io] for DICOM support") from exc

    root = Path(path)
    if not root.is_dir():
        raise ValueError(f"DICOM directory does not exist: {root}")
    series: dict[str, list[Any]] = defaultdict(list)
    for file in sorted(p for p in root.rglob("*") if p.is_file()):
        try:
            ds = pydicom.dcmread(str(file), stop_before_pixels=True, force=False)
        except Exception:
            continue
        uid = str(getattr(ds, "SeriesInstanceUID", ""))
        if uid:
            series[uid].append(ds)
    output: list[DicomSeriesSummary] = []
    for uid, datasets in series.items():
        first = datasets[0]
        spacing = getattr(first, "PixelSpacing", None)
        orientation = getattr(first, "ImageOrientationPatient", None)
        temporal_positions = getattr(first, "NumberOfTemporalPositions", None)
        warnings: list[str] = []
        if orientation is None:
            warnings.append("missing ImageOrientationPatient")
        output.append(
            DicomSeriesSummary(
                series_uid_sha256=sha256(uid),
                modality=str(getattr(first, "Modality", "")) or None,
                description=str(getattr(first, "SeriesDescription", "")) or None,
                file_count=len(datasets),
                rows=int(first.Rows) if hasattr(first, "Rows") else None,
                columns=int(first.Columns) if hasattr(first, "Columns") else None,
                pixel_spacing_mm=tuple(float(x) for x in spacing) if spacing is not None else None,
                slice_thickness_mm=(
                    float(first.SliceThickness) if hasattr(first, "SliceThickness") else None
                ),
                temporal_positions=(int(temporal_positions) if temporal_positions else None),
                image_orientation_patient=(
                    tuple(float(x) for x in orientation) if orientation is not None else None
                ),
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
