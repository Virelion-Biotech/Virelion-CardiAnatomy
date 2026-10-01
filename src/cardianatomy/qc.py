from __future__ import annotations

from collections import Counter

import numpy as np

from .models import GeometryQC, MeshInspection


def _validate_points(points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must have shape (N, 3)")
    return points


def _validate_cells(
    cells: np.ndarray,
    width: int,
    node_count: int,
    name: str,
) -> np.ndarray:
    values = np.asarray(cells, dtype=int)
    if values.ndim != 2 or values.shape[1] != width:
        raise ValueError(f"{name} must have shape (M, {width})")
    if values.size and (values.min() < 0 or values.max() >= node_count):
        raise ValueError(f"{name} contain out-of-range node indices")
    return values


def _require_finite_points(points: np.ndarray) -> None:
    if not np.all(np.isfinite(points)):
        raise ValueError("points must contain only finite values")


def tetra_signed_volumes(points: np.ndarray, tetrahedra: np.ndarray) -> np.ndarray:
    points = _validate_points(points)
    tetrahedra = _validate_cells(tetrahedra, 4, len(points), "tetrahedra")
    _require_finite_points(points)
    p0, p1, p2, p3 = (points[tetrahedra[:, i]] for i in range(4))
    with np.errstate(over="ignore", invalid="ignore"):
        cross = np.cross(p1 - p0, p2 - p0)
        volumes = np.einsum("ij,ij->i", cross, p3 - p0) / 6.0
    return volumes

def tetra_mean_ratio_quality(points: np.ndarray, tetrahedra: np.ndarray) -> np.ndarray:
    """Return normalized tetrahedral mean-ratio quality in [0, 1]."""
    points = _validate_points(points)
    tetrahedra = _validate_cells(tetrahedra, 4, len(points), "tetrahedra")
    _require_finite_points(points)
    volumes = np.abs(tetra_signed_volumes(points, tetrahedra))
    if not np.all(np.isfinite(volumes)):
        raise OverflowError("tetrahedral quality computation exceeds float64 range")
    edge_pairs = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
    edge_sq_sum = np.zeros(len(tetrahedra), dtype=float)
    for i, j in edge_pairs:
        delta = points[tetrahedra[:, i]] - points[tetrahedra[:, j]]
        edge_sq_sum += np.einsum("ij,ij->i", delta, delta)
    numerator = 12.0 * np.power(3.0 * volumes, 2.0 / 3.0)
    return np.divide(
        numerator,
        edge_sq_sum,
        out=np.zeros_like(numerator),
        where=edge_sq_sum > 0,
    )


def tetra_scaled_jacobian_quality(
    points: np.ndarray,
    tetrahedra: np.ndarray,
) -> np.ndarray:
    """Return minimum corner scaled-Jacobian magnitude per tetrahedron in [0, 1]."""
    points = _validate_points(points)
    tetrahedra = _validate_cells(tetrahedra, 4, len(points), "tetrahedra")
    _require_finite_points(points)
    tetra_signed_volumes(points, tetrahedra)

    corner_neighbors = (
        (0, 1, 2, 3),
        (1, 0, 2, 3),
        (2, 0, 1, 3),
        (3, 0, 1, 2),
    )
    corner_quality = []
    for origin, first, second, third in corner_neighbors:
        p0 = points[tetrahedra[:, origin]]
        e1 = points[tetrahedra[:, first]] - p0
        e2 = points[tetrahedra[:, second]] - p0
        e3 = points[tetrahedra[:, third]] - p0
        with np.errstate(over="ignore", invalid="ignore"):
            determinant = np.abs(
                np.einsum("ij,ij->i", np.cross(e1, e2), e3)
            )
        denominator = (
            np.linalg.norm(e1, axis=1)
            * np.linalg.norm(e2, axis=1)
            * np.linalg.norm(e3, axis=1)
        )
        if not np.all(np.isfinite(determinant)):
            raise OverflowError(
                "scaled-Jacobian computation exceeds float64 range"
            )
        scaled = np.divide(
            np.sqrt(2.0) * determinant,
            denominator,
            out=np.zeros_like(determinant),
            where=denominator > 0,
        )
        corner_quality.append(scaled)

    quality = np.min(np.stack(corner_quality, axis=1), axis=1)
    return np.clip(quality, 0.0, 1.0)


def triangle_shape_quality(points: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    """Return normalized triangle shape quality in [0, 1]."""
    points = _validate_points(points)
    triangles = _validate_cells(triangles, 3, len(points), "triangles")
    _require_finite_points(points)
    a, b, c = (points[triangles[:, i]] for i in range(3))
    with np.errstate(over="ignore", invalid="ignore"):
        cross = np.cross(b - a, c - a)
    if not np.all(np.isfinite(cross)):
        raise OverflowError("triangle quality computation exceeds float64 range")
    area = np.hypot(
        np.hypot(cross[:, 0], cross[:, 1]),
        cross[:, 2],
    ) / 2.0
    edge_sq_sum = (
        np.sum((a - b) ** 2, axis=1)
        + np.sum((b - c) ** 2, axis=1)
        + np.sum((c - a) ** 2, axis=1)
    )
    numerator = 4.0 * np.sqrt(3.0) * area
    return np.divide(
        numerator,
        edge_sq_sum,
        out=np.zeros_like(numerator),
        where=edge_sq_sum > 0,
    )


def _quality_summary(values: np.ndarray, prefix: str) -> dict[str, float]:
    if not len(values):
        return {}
    return {
        f"{prefix}_min": float(np.min(values)),
        f"{prefix}_p05": float(np.quantile(values, 0.05)),
        f"{prefix}_median": float(np.median(values)),
    }



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
    with np.errstate(over="ignore", invalid="ignore"):
        delta = points[edges[:, 0]] - points[edges[:, 1]]
    if not np.all(np.isfinite(delta)):
        return np.full(len(edges), np.inf, dtype=float)
    return np.hypot(
        np.hypot(delta[:, 0], delta[:, 1]),
        delta[:, 2],
    )


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
    tetrahedra = _validate_cells(tetrahedra, 4, len(points), "tetrahedra")
    finite = bool(np.all(np.isfinite(points)))
    if not finite:
        return MeshInspection(
            point_count=len(points),
            cell_count=len(tetrahedra),
            tetra_count=len(tetrahedra),
            connected_components=_connected_components(len(points), tetrahedra),
            finite=False,
        )
    volumes = tetra_signed_volumes(points, tetrahedra)
    finite = bool(np.all(np.isfinite(volumes)))
    if not finite:
        return MeshInspection(
            point_count=len(points),
            cell_count=len(tetrahedra),
            tetra_count=len(tetrahedra),
            connected_components=_connected_components(len(points), tetrahedra),
            finite=False,
        )
    abs_volumes = np.abs(volumes)
    scale = float(np.max(abs_volumes)) if len(abs_volumes) else 0.0
    tolerance = np.finfo(float).eps * scale * 100.0
    degenerate = abs_volumes <= tolerance
    nonzero = volumes[~degenerate]
    minority_fraction = 0.0
    if len(nonzero):
        positive = int(np.sum(nonzero > 0))
        negative = int(np.sum(nonzero < 0))
        minority_fraction = min(positive, negative) / len(nonzero)
    lengths = _edge_lengths(points, tetrahedra)
    quality = tetra_mean_ratio_quality(points, tetrahedra)
    scaled_jacobian = tetra_scaled_jacobian_quality(points, tetrahedra)
    metadata = _quality_summary(quality, "tetra_mean_ratio")
    metadata.update(
        _quality_summary(scaled_jacobian, "tetra_scaled_jacobian")
    )
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
        metadata=metadata,
    )


def inspect_triangle_surface(points: np.ndarray, triangles: np.ndarray) -> MeshInspection:
    points = _validate_points(points)
    triangles = _validate_cells(triangles, 3, len(points), "triangles")
    if not np.all(np.isfinite(points)):
        return MeshInspection(
            point_count=len(points),
            cell_count=len(triangles),
            triangle_count=len(triangles),
            connected_components=_connected_components(len(points), triangles),
            finite=False,
        )
    a, b, c = (points[triangles[:, i]] for i in range(3))
    with np.errstate(over="ignore", invalid="ignore"):
        cross = np.cross(b - a, c - a)
    if not np.all(np.isfinite(cross)):
        return MeshInspection(
            point_count=len(points),
            cell_count=len(triangles),
            triangle_count=len(triangles),
            connected_components=_connected_components(len(points), triangles),
            finite=False,
        )
    areas = np.hypot(
        np.hypot(cross[:, 0], cross[:, 1]),
        cross[:, 2],
    ) / 2.0
    scale = float(np.max(areas)) if len(areas) else 0.0
    tolerance = np.finfo(float).eps * scale * 100.0
    degenerate = areas <= tolerance
    counts: Counter[tuple[int, int]] = Counter()
    for tri in triangles:
        for i, j in ((0, 1), (1, 2), (2, 0)):
            counts[tuple(sorted((int(tri[i]), int(tri[j]))))] += 1
    boundary = sum(1 for count in counts.values() if count == 1)
    nonmanifold = sum(1 for count in counts.values() if count > 2)
    lengths = _edge_lengths(points, triangles)
    quality = triangle_shape_quality(points, triangles)
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
        metadata=_quality_summary(quality, "triangle_quality"),
    )


def qc_from_inspection(
    inspection: MeshInspection,
    *,
    require_watertight: bool = False,
    minimum_shape_quality: float | None = None,
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
    if minimum_shape_quality is not None:
        if not 0 <= minimum_shape_quality <= 1:
            raise ValueError("minimum_shape_quality must lie in [0, 1]")
        quality_keys = (
            "tetra_mean_ratio_min",
            "tetra_scaled_jacobian_min",
            "triangle_quality_min",
        )
        quality_values = [
            float(inspection.metadata[key])
            for key in quality_keys
            if key in inspection.metadata
        ]
        if quality_values:
            checks["minimum_shape_quality"] = min(quality_values) >= minimum_shape_quality

    errors = [name for name, passed in checks.items() if not passed]
    metrics = {
        key: value
        for key, value in inspection.model_dump(exclude={"path", "metadata"}).items()
        if value is not None
    }
    metrics.update(
        {
            key: value
            for key, value in inspection.metadata.items()
            if isinstance(value, (int, float, bool, str))
        }
    )
    return GeometryQC(
        passed=not errors,
        checks=checks,
        metrics=metrics,
        errors=errors,
    )
