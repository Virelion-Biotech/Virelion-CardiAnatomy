from __future__ import annotations

from collections import Counter

import numpy as np

from .models import GeometryQC, MeshInspection


def _validate_points(points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must have shape (N, 3)")
    return points


def tetra_signed_volumes(points: np.ndarray, tetrahedra: np.ndarray) -> np.ndarray:
    points = _validate_points(points)
    tetrahedra = np.asarray(tetrahedra, dtype=int)
    if tetrahedra.ndim != 2 or tetrahedra.shape[1] != 4:
        raise ValueError("tetrahedra must have shape (M, 4)")
    if tetrahedra.size and (tetrahedra.min() < 0 or tetrahedra.max() >= len(points)):
        raise ValueError("tetrahedra contain out-of-range node indices")
    p0, p1, p2, p3 = (points[tetrahedra[:, i]] for i in range(4))
    return np.einsum("ij,ij->i", np.cross(p1 - p0, p2 - p0), p3 - p0) / 6.0


def _edge_lengths(points: np.ndarray, cells: np.ndarray) -> np.ndarray:
    pairs: set[tuple[int, int]] = set()
    for cell in np.asarray(cells, dtype=int):
        for i in range(len(cell)):
            for j in range(i + 1, len(cell)):
                a, b = sorted((int(cell[i]), int(cell[j])))
                pairs.add((a, b))
    if not pairs:
        return np.array([], dtype=float)
    edges = np.asarray(sorted(pairs), dtype=int)
    return np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1)


def _connected_components(node_count: int, cells: np.ndarray) -> int:
    if node_count == 0:
        return 0
    parent = list(range(node_count))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    used: set[int] = set()
    for cell in np.asarray(cells, dtype=int):
        values = [int(x) for x in cell]
        used.update(values)
        for value in values[1:]:
            union(values[0], value)
    return len({find(index) for index in used}) if used else 0


def inspect_tetra_mesh(points: np.ndarray, tetrahedra: np.ndarray) -> MeshInspection:
    points = _validate_points(points)
    tetrahedra = np.asarray(tetrahedra, dtype=int)
    volumes = tetra_signed_volumes(points, tetrahedra)
    finite = bool(np.all(np.isfinite(points)) and np.all(np.isfinite(volumes)))
    abs_volumes = np.abs(volumes)
    scale = max(float(np.max(abs_volumes)) if len(abs_volumes) else 0.0, 1.0)
    tolerance = np.finfo(float).eps * scale * 100.0
    degenerate = abs_volumes <= tolerance
    nonzero = volumes[~degenerate]
    minority_fraction = 0.0
    if len(nonzero):
        positive = int(np.sum(nonzero > 0))
        negative = int(np.sum(nonzero < 0))
        minority_fraction = min(positive, negative) / len(nonzero)
    lengths = _edge_lengths(points, tetrahedra)
    return MeshInspection(
        point_count=len(points),
        cell_count=len(tetrahedra),
        tetra_count=len(tetrahedra),
        connected_components=_connected_components(len(points), tetrahedra),
        degenerate_fraction=float(np.mean(degenerate)) if len(degenerate) else 0.0,
        minority_orientation_fraction=float(minority_fraction),
        min_edge_length=float(lengths.min()) if len(lengths) else None,
        max_edge_length=float(lengths.max()) if len(lengths) else None,
        min_abs_tetra_volume=float(abs_volumes.min()) if len(abs_volumes) else None,
        max_abs_tetra_volume=float(abs_volumes.max()) if len(abs_volumes) else None,
        finite=finite,
    )


def inspect_triangle_surface(points: np.ndarray, triangles: np.ndarray) -> MeshInspection:
    points = _validate_points(points)
    triangles = np.asarray(triangles, dtype=int)
    if triangles.ndim != 2 or triangles.shape[1] != 3:
        raise ValueError("triangles must have shape (M, 3)")
    if triangles.size and (triangles.min() < 0 or triangles.max() >= len(points)):
        raise ValueError("triangles contain out-of-range node indices")
    a, b, c = (points[triangles[:, i]] for i in range(3))
    areas = np.linalg.norm(np.cross(b - a, c - a), axis=1) / 2.0
    scale = max(float(np.max(areas)) if len(areas) else 0.0, 1.0)
    tolerance = np.finfo(float).eps * scale * 100.0
    degenerate = areas <= tolerance
    counts: Counter[tuple[int, int]] = Counter()
    for tri in triangles:
        for i, j in ((0, 1), (1, 2), (2, 0)):
            counts[tuple(sorted((int(tri[i]), int(tri[j]))))] += 1
    boundary = sum(1 for count in counts.values() if count == 1)
    nonmanifold = sum(1 for count in counts.values() if count > 2)
    lengths = _edge_lengths(points, triangles)
    return MeshInspection(
        point_count=len(points),
        cell_count=len(triangles),
        triangle_count=len(triangles),
        connected_components=_connected_components(len(points), triangles),
        degenerate_fraction=float(np.mean(degenerate)) if len(degenerate) else 0.0,
        boundary_edge_count=boundary,
        nonmanifold_edge_count=nonmanifold,
        min_edge_length=float(lengths.min()) if len(lengths) else None,
        max_edge_length=float(lengths.max()) if len(lengths) else None,
        finite=bool(np.all(np.isfinite(points)) and np.all(np.isfinite(areas))),
    )


def qc_from_inspection(
    inspection: MeshInspection, *, require_watertight: bool = False
) -> GeometryQC:
    checks = {
        "nonempty": inspection.point_count > 0 and inspection.cell_count > 0,
        "finite": inspection.finite,
        "single_component": inspection.connected_components in {None, 1},
        "no_degenerate_cells": (inspection.degenerate_fraction or 0.0) == 0.0,
    }
    if inspection.tetra_count:
        checks["consistent_tetra_orientation"] = (
            inspection.minority_orientation_fraction or 0.0
        ) == 0.0
    if inspection.triangle_count:
        checks["manifold_edges"] = (inspection.nonmanifold_edge_count or 0) == 0
        if require_watertight:
            checks["watertight"] = (inspection.boundary_edge_count or 0) == 0
    errors = [name for name, passed in checks.items() if not passed]
    metrics = {
        key: value
        for key, value in inspection.model_dump(exclude={"path", "metadata"}).items()
        if value is not None
    }
    return GeometryQC(
        passed=not errors,
        checks=checks,
        metrics=metrics,
        errors=errors,
    )
