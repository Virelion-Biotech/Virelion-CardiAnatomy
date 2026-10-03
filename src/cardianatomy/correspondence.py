from __future__ import annotations

from dataclasses import dataclass
import hashlib

import numpy as np


@dataclass(frozen=True)
class CorrespondenceSummary:
    point_count: int
    mean_displacement: float
    rms_displacement: float
    median_displacement: float
    p95_displacement: float
    max_displacement: float
    connectivity_identical: bool | None
    reference_centroid: tuple[float, float, float]
    target_centroid: tuple[float, float, float]


def _validated_cells(
    cells: np.ndarray,
    *,
    point_count: int | None = None,
    name: str = "cells",
) -> np.ndarray:
    raw = np.asarray(cells)
    if not np.issubdtype(raw.dtype, np.integer):
        if not np.issubdtype(raw.dtype, np.number):
            raise ValueError(f"{name} must contain integer indices")
        if not np.all(np.isfinite(raw)) or not np.all(raw == np.floor(raw)):
            raise ValueError(f"{name} must contain finite integer indices")
    values = raw.astype(np.int64, copy=False)
    if values.ndim != 2 or values.shape[1] not in {3, 4}:
        raise ValueError(f"{name} must have shape (M, 3) or (M, 4)")
    if np.any(values < 0):
        raise ValueError(f"{name} indices must be non-negative")
    if point_count is not None and values.size and np.max(values) >= point_count:
        raise ValueError(f"{name} contain out-of-range point indices")
    return values


def connectivity_fingerprint(cells: np.ndarray) -> str:
    values = _validated_cells(cells)
    digest = hashlib.sha256()
    digest.update(str(values.shape).encode("ascii"))
    digest.update(np.ascontiguousarray(values).tobytes())
    return digest.hexdigest()


def compare_corresponding_meshes(
    reference_points: np.ndarray,
    target_points: np.ndarray,
    *,
    reference_cells: np.ndarray | None = None,
    target_cells: np.ndarray | None = None,
) -> CorrespondenceSummary:
    reference = np.asarray(reference_points, dtype=float)
    target = np.asarray(target_points, dtype=float)
    if reference.shape != target.shape or reference.ndim != 2 or reference.shape[1] != 3:
        raise ValueError(
            "reference_points and target_points must both have shape (N, 3)"
        )
    if len(reference) == 0:
        raise ValueError("corresponding meshes must contain at least one point")
    if not np.all(np.isfinite(reference)) or not np.all(np.isfinite(target)):
        raise ValueError("mesh points must be finite")

    connectivity_identical: bool | None = None
    if (reference_cells is None) != (target_cells is None):
        raise ValueError(
            "reference_cells and target_cells must either both be provided or omitted"
        )
    if reference_cells is not None and target_cells is not None:
        ref_cells = _validated_cells(
            reference_cells,
            point_count=len(reference),
            name="reference_cells",
        )
        tgt_cells = _validated_cells(
            target_cells,
            point_count=len(target),
            name="target_cells",
        )
        connectivity_identical = bool(
            ref_cells.shape == tgt_cells.shape
            and np.array_equal(ref_cells, tgt_cells)
        )

    displacement = np.linalg.norm(target - reference, axis=1)
    return CorrespondenceSummary(
        point_count=int(len(reference)),
        mean_displacement=float(np.mean(displacement)),
        rms_displacement=float(np.sqrt(np.mean(displacement**2))),
        median_displacement=float(np.median(displacement)),
        p95_displacement=float(np.quantile(displacement, 0.95)),
        max_displacement=float(np.max(displacement)),
        connectivity_identical=connectivity_identical,
        reference_centroid=tuple(float(x) for x in reference.mean(axis=0)),
        target_centroid=tuple(float(x) for x in target.mean(axis=0)),
    )


def transfer_point_data_by_index(
    source_values: np.ndarray,
    source_index_for_target: np.ndarray,
) -> np.ndarray:
    values = np.asarray(source_values)
    raw_index = np.asarray(source_index_for_target)
    if not np.issubdtype(raw_index.dtype, np.integer):
        if (
            not np.issubdtype(raw_index.dtype, np.number)
            or not np.all(np.isfinite(raw_index))
            or not np.all(raw_index == np.floor(raw_index))
        ):
            raise ValueError("correspondence map must contain finite integer indices")
    index = raw_index.astype(np.int64, copy=False)
    if index.ndim != 1:
        raise ValueError("source_index_for_target must be one-dimensional")
    if np.any(index < 0) or np.any(index >= len(values)):
        raise ValueError("correspondence map contains out-of-range source indices")
    return np.asarray(values[index]).copy()
