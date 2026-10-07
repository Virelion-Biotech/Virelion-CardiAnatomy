from __future__ import annotations

import numpy as np

from .qc import tetra_signed_volumes


def _stable_centroid(points: np.ndarray) -> np.ndarray:
    scale = np.max(np.abs(points), axis=0)
    normalized = np.divide(
        points,
        scale,
        out=np.zeros_like(points),
        where=scale > 0,
    )
    return normalized.mean(axis=0) * scale


def _row_norm(vectors: np.ndarray) -> np.ndarray:
    return np.hypot(
        np.hypot(vectors[:, 0], vectors[:, 1]),
        vectors[:, 2],
    )


def bounding_box(points: np.ndarray) -> dict[str, list[float]]:
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) == 0:
        raise ValueError("points must have shape (N, 3) with N > 0")
    if not np.all(np.isfinite(points)):
        raise ValueError("points must be finite")
    minimum = points.min(axis=0)
    maximum = points.max(axis=0)
    with np.errstate(over="ignore", invalid="ignore"):
        extent = maximum - minimum
    centroid = _stable_centroid(points)
    if not np.all(np.isfinite(extent)) or not np.all(np.isfinite(centroid)):
        raise OverflowError("bounding-box summary exceeds float64 range")
    return {
        "min": minimum.tolist(),
        "max": maximum.tolist(),
        "extent": extent.tolist(),
        "centroid": centroid.tolist(),
    }


def triangle_surface_area(points: np.ndarray, triangles: np.ndarray) -> float:
    points = np.asarray(points, dtype=float)
    triangles = np.asarray(triangles)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must have shape (N, 3)")
    if not np.all(np.isfinite(points)):
        raise ValueError("points must be finite")
    if triangles.ndim != 2 or triangles.shape[1] != 3:
        raise ValueError("triangles must have shape (M, 3)")
    if not np.issubdtype(triangles.dtype, np.integer):
        if (
            not np.issubdtype(triangles.dtype, np.number)
            or not np.all(np.isfinite(triangles))
            or not np.all(triangles == np.floor(triangles))
        ):
            raise ValueError("triangles must contain finite integer indices")
        triangles = triangles.astype(np.int64)
    if triangles.size and (triangles.min() < 0 or triangles.max() >= len(points)):
        raise ValueError("triangles contain out-of-range point indices")
    a, b, c = (points[triangles[:, index]] for index in range(3))
    with np.errstate(over="ignore", invalid="ignore"):
        cross = np.cross(b - a, c - a)
    if not np.all(np.isfinite(cross)):
        raise OverflowError("triangle area computation exceeds float64 range")
    areas = _row_norm(cross) / 2.0
    total = float(np.sum(areas))
    if not np.isfinite(total):
        raise OverflowError("total triangle area exceeds float64 range")
    return total


def tetrahedral_volume(points: np.ndarray, tetrahedra: np.ndarray) -> float:
    volumes = tetra_signed_volumes(points, tetrahedra)
    if not np.all(np.isfinite(volumes)):
        raise OverflowError("tetrahedral volume computation exceeds float64 range")
    total = float(np.sum(np.abs(volumes)))
    if not np.isfinite(total):
        raise OverflowError("total tetrahedral volume exceeds float64 range")
    return total


def closed_surface_signed_volume(points: np.ndarray, triangles: np.ndarray) -> float:
    """Compute oriented volume of a closed triangular surface."""
    points = np.asarray(points, dtype=float)
    triangles = np.asarray(triangles)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must have shape (N, 3)")
    if not np.all(np.isfinite(points)):
        raise ValueError("points must be finite")
    if triangles.ndim != 2 or triangles.shape[1] != 3:
        raise ValueError("triangles must have shape (M, 3)")
    if not np.issubdtype(triangles.dtype, np.integer):
        if (
            not np.issubdtype(triangles.dtype, np.number)
            or not np.all(np.isfinite(triangles))
            or not np.all(triangles == np.floor(triangles))
        ):
            raise ValueError("triangles must contain finite integer indices")
        triangles = triangles.astype(np.int64)
    if triangles.size and (triangles.min() < 0 or triangles.max() >= len(points)):
        raise ValueError("triangles contain out-of-range point indices")
    from .qc import inspect_triangle_surface, qc_from_inspection

    qc = qc_from_inspection(inspect_triangle_surface(points, triangles),
                            require_watertight=True)
    if not qc.passed:
        raise ValueError("Surface volume requires a closed, consistently oriented manifold")
    shifted = points - points[0]
    a, b, c = (shifted[triangles[:, index]] for index in range(3))
    with np.errstate(over="ignore", invalid="ignore"):
        cross = np.cross(b, c)
        contributions = np.einsum("ij,ij->i", a, cross)
    if not np.all(np.isfinite(contributions)):
        raise OverflowError("surface-volume computation exceeds float64 range")
    volume = float(np.sum(contributions) / 6.0)
    if not np.isfinite(volume):
        raise OverflowError("surface volume exceeds float64 range")
    return volume


def mesh_scale_metrics(points: np.ndarray, cells: np.ndarray) -> dict[str, float]:
    points = np.asarray(points, dtype=float)
    cells = np.asarray(cells)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must have shape (N, 3)")
    if not np.all(np.isfinite(points)):
        raise ValueError("points must be finite")
    if cells.ndim != 2:
        raise ValueError("cells must be a 2D connectivity array")
    if not np.issubdtype(cells.dtype, np.integer):
        if (
            not np.issubdtype(cells.dtype, np.number)
            or not np.all(np.isfinite(cells))
            or not np.all(cells == np.floor(cells))
        ):
            raise ValueError("cells must contain finite integer indices")
        cells = cells.astype(np.int64)
    if cells.size and (cells.min() < 0 or cells.max() >= len(points)):
        raise ValueError("cells contain out-of-range point indices")
    edges: set[tuple[int, int]] = set()
    for cell in cells:
        for i in range(len(cell)):
            for j in range(i + 1, len(cell)):
                edges.add(tuple(sorted((int(cell[i]), int(cell[j])))))
    if not edges:
        return {"edge_count": 0.0}
    edge_array = np.asarray(sorted(edges), dtype=int)
    with np.errstate(over="ignore", invalid="ignore"):
        delta = points[edge_array[:, 0]] - points[edge_array[:, 1]]
    if not np.all(np.isfinite(delta)):
        raise OverflowError("edge coordinate differences exceed float64 range")
    lengths = _row_norm(delta)
    return {
        "edge_count": float(len(lengths)),
        "edge_min": float(lengths.min()),
        "edge_median": float(np.median(lengths)),
        "edge_mean": float(lengths.mean()),
        "edge_max": float(lengths.max()),
    }
