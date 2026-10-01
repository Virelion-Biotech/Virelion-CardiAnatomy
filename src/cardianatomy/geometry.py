from __future__ import annotations

import numpy as np

from .qc import tetra_signed_volumes


def bounding_box(points: np.ndarray) -> dict[str, list[float]]:
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) == 0:
        raise ValueError("points must have shape (N, 3) with N > 0")
    if not np.all(np.isfinite(points)):
        raise ValueError("points must be finite")
    return {
        "min": points.min(axis=0).tolist(),
        "max": points.max(axis=0).tolist(),
        "extent": np.ptp(points, axis=0).tolist(),
        "centroid": points.mean(axis=0).tolist(),
    }


def triangle_surface_area(points: np.ndarray, triangles: np.ndarray) -> float:
    points = np.asarray(points, dtype=float)
    triangles = np.asarray(triangles, dtype=int)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must have shape (N, 3)")
    if not np.all(np.isfinite(points)):
        raise ValueError("points must be finite")
    if triangles.ndim != 2 or triangles.shape[1] != 3:
        raise ValueError("triangles must have shape (M, 3)")
    if triangles.size and (triangles.min() < 0 or triangles.max() >= len(points)):
        raise ValueError("triangles contain out-of-range point indices")
    a, b, c = (points[triangles[:, index]] for index in range(3))
    return float(np.sum(np.linalg.norm(np.cross(b - a, c - a), axis=1) / 2.0))


def tetrahedral_volume(points: np.ndarray, tetrahedra: np.ndarray) -> float:
    volumes = tetra_signed_volumes(points, tetrahedra)
    return float(np.sum(np.abs(volumes)))


def closed_surface_signed_volume(points: np.ndarray, triangles: np.ndarray) -> float:
    """Compute oriented volume of a closed triangular surface."""
    points = np.asarray(points, dtype=float)
    triangles = np.asarray(triangles, dtype=int)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must have shape (N, 3)")
    if not np.all(np.isfinite(points)):
        raise ValueError("points must be finite")
    if triangles.ndim != 2 or triangles.shape[1] != 3:
        raise ValueError("triangles must have shape (M, 3)")
    if triangles.size and (triangles.min() < 0 or triangles.max() >= len(points)):
        raise ValueError("triangles contain out-of-range point indices")
    a, b, c = (points[triangles[:, index]] for index in range(3))
    return float(np.sum(np.einsum("ij,ij->i", a, np.cross(b, c))) / 6.0)


def mesh_scale_metrics(points: np.ndarray, cells: np.ndarray) -> dict[str, float]:
    points = np.asarray(points, dtype=float)
    cells = np.asarray(cells, dtype=int)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must have shape (N, 3)")
    if not np.all(np.isfinite(points)):
        raise ValueError("points must be finite")
    if cells.ndim != 2:
        raise ValueError("cells must be a 2D connectivity array")
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
    lengths = np.linalg.norm(points[edge_array[:, 0]] - points[edge_array[:, 1]], axis=1)
    return {
        "edge_count": float(len(lengths)),
        "edge_min": float(lengths.min()),
        "edge_median": float(np.median(lengths)),
        "edge_mean": float(lengths.mean()),
        "edge_max": float(lengths.max()),
    }
