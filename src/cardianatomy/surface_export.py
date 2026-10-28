"""Extract a browser-displayable exterior surface from a supported meshio volume mesh.

The output is legacy ASCII VTK POLYDATA with triangular faces. It contains geometry
only; scalar arrays, anatomical labels, and cell attributes are not transferred.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np

_VOLUME_FACES: dict[str, tuple[tuple[int, ...], ...]] = {
    "tetra": ((0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3)),
    "hexahedron": (
        (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
        (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
    ),
    "wedge": (
        (0, 2, 1), (3, 4, 5), (0, 1, 4, 3),
        (1, 2, 5, 4), (2, 0, 3, 5),
    ),
    "pyramid": (
        (0, 3, 2, 1), (0, 1, 4), (1, 2, 4),
        (2, 3, 4), (3, 0, 4),
    ),
}
_UNSUPPORTED_VOLUME_TYPES = {
    "tetra10", "tetra14", "hexahedron20", "hexahedron27",
    "wedge15", "wedge18", "pyramid13", "voxel", "polyhedron",
}


def _triangulate(face: Iterable[int]) -> list[tuple[int, int, int]]:
    indices = tuple(int(index) for index in face)
    if len(indices) == 3:
        return [(indices[0], indices[1], indices[2])]
    if len(indices) == 4:
        return [(indices[0], indices[1], indices[2]), (indices[0], indices[2], indices[3])]
    raise ValueError("Only linear triangles and quadrilaterals can be displayed")


def _orient_outward(
    face: tuple[int, ...], cell: tuple[int, ...], points: np.ndarray
) -> tuple[int, ...]:
    coordinates = points[np.asarray(face, dtype=np.int64)]
    normal = np.cross(coordinates[1] - coordinates[0], coordinates[2] - coordinates[0])
    face_center = coordinates.mean(axis=0)
    cell_center = points[np.asarray(cell, dtype=np.int64)].mean(axis=0)
    if float(np.dot(normal, face_center - cell_center)) < 0:
        return tuple(reversed(face))
    return face


def _write_legacy_polydata(
    path: Path, points: np.ndarray, triangles: list[tuple[int, int, int]]
) -> None:
    lines = [
        "# vtk DataFile Version 3.0",
        "CardiAnatomy exterior surface; geometry-only display export",
        "ASCII",
        "DATASET POLYDATA",
        f"POINTS {len(points)} double",
    ]
    lines.extend("{:.16g} {:.16g} {:.16g}".format(*point) for point in points)
    lines.append(f"POLYGONS {len(triangles)} {4 * len(triangles)}")
    lines.extend(f"3 {a} {b} {c}" for a, b, c in triangles)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_surface_mesh(
    input_path: str | Path,
    output_path: str | Path,
    *,
    max_points: int = 2_000_000,
) -> dict[str, object]:
    """Extract exterior faces from a linear volume mesh and write VTK POLYDATA."""
    try:
        import meshio
    except ImportError as exc:
        raise RuntimeError("Install meshio support with: python -m pip install -e '.[io]'") from exc

    source = Path(input_path)
    destination = Path(output_path)
    if not source.is_file():
        raise ValueError(f"Input mesh does not exist: {source}")
    if source.resolve() == destination.resolve():
        raise ValueError("Input and output paths must be different")
    if destination.suffix.lower() != ".vtk":
        raise ValueError("Output must use the .vtk extension (legacy ASCII POLYDATA)")
    if isinstance(max_points, bool) or not isinstance(max_points, int) or max_points < 4:
        raise ValueError("max_points must be an integer >= 4")

    mesh = meshio.read(source)
    points = np.asarray(mesh.points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] < 3:
        raise ValueError("Input mesh must contain 3D points")
    if len(points) < 4 or len(points) > max_points:
        raise ValueError(f"Point count must be between 4 and max_points={max_points}")
    points = points[:, :3]
    if not np.all(np.isfinite(points)):
        raise ValueError("Input mesh contains non-finite coordinates")

    cell_types = [block.type for block in mesh.cells]
    unsupported = sorted(set(cell_types) & _UNSUPPORTED_VOLUME_TYPES)
    if unsupported:
        raise ValueError(
            "Higher-order/voxel/polyhedron cells need an explicit conversion before surface "
            f"export; unsupported cell types: {', '.join(unsupported)}"
        )

    volume_blocks = [block for block in mesh.cells if block.type in _VOLUME_FACES]
    triangles: list[tuple[int, int, int]] = []
    nonmanifold_face_count = 0

    if volume_blocks:
        face_records: dict[tuple[int, ...], tuple[int, tuple[int, ...]]] = {}
        for block in volume_blocks:
            local_faces = _VOLUME_FACES[block.type]
            for raw_cell in block.data:
                cell = tuple(int(index) for index in raw_cell)
                if any(index < 0 or index >= len(points) for index in cell):
                    raise ValueError("Input cell references an out-of-range point")
                for local_face in local_faces:
                    oriented = _orient_outward(
                        tuple(cell[position] for position in local_face), cell, points
                    )
                    key = tuple(sorted(oriented))
                    if key in face_records:
                        count, original = face_records[key]
                        face_records[key] = (count + 1, original)
                    else:
                        face_records[key] = (1, oriented)

        exterior_faces = []
        for count, face in face_records.values():
            if count == 1:
                exterior_faces.append(face)
            elif count > 2:
                nonmanifold_face_count += 1
        for face in exterior_faces:
            triangles.extend(_triangulate(face))
    else:
        surface_blocks = [block for block in mesh.cells if block.type in {"triangle", "quad"}]
        if not surface_blocks:
            found = ", ".join(sorted(set(cell_types))) or "none"
            raise ValueError(
                "No supported linear volume cells or triangular/quadrilateral surface cells "
                f"found (input cell types: {found})"
            )
        for block in surface_blocks:
            for face in block.data:
                indices = tuple(int(index) for index in face)
                if any(index < 0 or index >= len(points) for index in indices):
                    raise ValueError("Input cell references an out-of-range point")
                triangles.extend(_triangulate(indices))

    if not triangles:
        raise ValueError("No exterior surface triangles were generated")
    _write_legacy_polydata(destination, points, triangles)
    return {
        "input": str(source),
        "output": str(destination),
        "input_cell_types": sorted(set(cell_types)),
        "point_count": int(len(points)),
        "surface_triangle_count": int(len(triangles)),
        "nonmanifold_face_count": int(nonmanifold_face_count),
        "output_format": "legacy_ascii_vtk_polydata",
        "geometry_only": True,
        "note": (
            "Coordinates are unchanged. Scalar fields, anatomical labels, and cell attributes "
            "are not exported. Confirm coordinate units and inspect the rendered surface."
        ),
    }
