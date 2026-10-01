from __future__ import annotations

import numpy as np

from .models import ScarThresholdSpec


def classify_scalar_scar(values: np.ndarray, spec: ScarThresholdSpec) -> np.ndarray:
    """Classify a scalar field into normal=0, border-zone=1, core=2.

    Threshold selection is intentionally external. This utility applies declared thresholds;
    it does not estimate clinically valid LGE thresholds.
    """
    values = np.asarray(values, dtype=float)
    if values.ndim != 1:
        raise ValueError("values must be a one-dimensional scalar field")
    if not np.all(np.isfinite(values)):
        raise ValueError("values must be finite")
    labels = np.zeros(values.shape, dtype=np.uint8)
    labels[values >= spec.border_threshold] = 1
    labels[values >= spec.core_threshold] = 2
    return labels


def scar_fractions(labels: np.ndarray) -> dict[str, float]:
    labels = np.asarray(labels)
    if labels.ndim != 1 or np.any(~np.isin(labels, [0, 1, 2])):
        raise ValueError("labels must contain only 0, 1, and 2")
    total = max(len(labels), 1)
    return {
        "normal_fraction": float(np.sum(labels == 0) / total),
        "border_fraction": float(np.sum(labels == 1) / total),
        "core_fraction": float(np.sum(labels == 2) / total),
    }
