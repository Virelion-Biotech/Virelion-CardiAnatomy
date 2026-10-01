from __future__ import annotations

import numpy as np


def label_counts(labels: np.ndarray) -> dict[int, int]:
    values = np.asarray(labels)
    if values.size == 0:
        return {}
    if not np.issubdtype(values.dtype, np.number):
        raise ValueError("segmentation labels must be numeric")
    if not np.all(np.isfinite(values)):
        raise ValueError("segmentation labels must be finite")
    if not np.issubdtype(values.dtype, np.integer):
        if not np.all(np.equal(values, np.floor(values))):
            raise ValueError("segmentation labels must be integer-valued")
        limits = np.iinfo(np.int64)
        if np.any(values < limits.min) or np.any(values > limits.max):
            raise ValueError("segmentation labels exceed int64 range")
        values = values.astype(np.int64)
    unique, counts = np.unique(values, return_counts=True)
    return {int(label): int(count) for label, count in zip(unique, counts, strict=True)}


def label_volumes_ml(
    labels: np.ndarray,
    spacing_mm: tuple[float, ...],
) -> dict[int, float]:
    values = np.asarray(labels)
    if values.ndim != 3:
        raise ValueError(
            "label_volumes_ml expects one 3D segmentation; "
            "select a cine phase before computing spatial volume"
        )
    if len(spacing_mm) < 3:
        raise ValueError("spacing_mm must provide three spatial dimensions")
    spacing = np.asarray(spacing_mm[:3], dtype=float)
    if not np.all(np.isfinite(spacing)) or np.any(spacing <= 0):
        raise ValueError("spatial voxel spacing must be finite and strictly positive")
    voxel_volume_mm3 = float(np.prod(spacing))
    if not np.isfinite(voxel_volume_mm3) or voxel_volume_mm3 <= 0:
        raise ValueError("voxel volume is not finite and positive")
    return {
        label: count * voxel_volume_mm3 / 1000.0
        for label, count in label_counts(values).items()
    }


def segmentation_qc(
    labels: np.ndarray,
    *,
    required_labels: set[int] | None = None,
    background_label: int = 0,
) -> dict[str, object]:
    counts = label_counts(labels)
    present = set(counts)
    missing = sorted((required_labels or set()) - present)
    foreground = sum(count for label, count in counts.items() if label != background_label)
    total = sum(counts.values())
    denominator = max(total, 1)
    return {
        "passed": total > 0 and not missing and foreground > 0,
        "present_labels": sorted(present),
        "missing_labels": missing,
        "foreground_fraction": float(foreground / denominator),
        "voxel_count": int(total),
    }
