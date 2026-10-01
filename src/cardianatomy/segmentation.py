from __future__ import annotations

import numpy as np


def label_counts(labels: np.ndarray) -> dict[int, int]:
    values = np.asarray(labels)
    if values.size == 0:
        return {}
    if not np.issubdtype(values.dtype, np.integer):
        if not np.all(np.equal(values, np.floor(values))):
            raise ValueError("segmentation labels must be integer-valued")
        values = values.astype(int)
    unique, counts = np.unique(values, return_counts=True)
    return {int(label): int(count) for label, count in zip(unique, counts, strict=True)}


def label_volumes_ml(
    labels: np.ndarray,
    spacing_mm: tuple[float, ...],
) -> dict[int, float]:
    values = np.asarray(labels)
    if values.ndim < 2:
        raise ValueError("segmentation must have at least two dimensions")
    if len(spacing_mm) < values.ndim:
        raise ValueError("spacing_mm must cover all segmentation dimensions")
    voxel_volume_mm3 = float(np.prod(spacing_mm[: values.ndim]))
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
    total = max(sum(counts.values()), 1)
    return {
        "passed": not missing and foreground > 0,
        "present_labels": sorted(present),
        "missing_labels": missing,
        "foreground_fraction": float(foreground / total),
        "voxel_count": int(total),
    }
