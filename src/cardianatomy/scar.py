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
    if len(labels) == 0:
        raise ValueError("scar fractions require at least one label")
    total = len(labels)
    return {
        "normal_fraction": float(np.sum(labels == 0) / total),
        "border_fraction": float(np.sum(labels == 1) / total),
        "core_fraction": float(np.sum(labels == 2) / total),
    }


def scar_threshold_ensemble(values, specs, *, acquisition_sequence, etiology, method):
    """Empirical class frequencies across declared threshold hypotheses.

    These are threshold-sensitivity frequencies, not calibrated tissue-class
    probabilities. No LGE threshold is inferred or scientifically qualified here.
    """
    specs = tuple(specs)
    if len(specs) < 2:
        raise ValueError("Scar sensitivity requires at least two declared threshold hypotheses")
    if any(
        not isinstance(x, str) or not x.strip() for x in [acquisition_sequence, etiology, method]
    ):
        raise ValueError("Sequence, etiology and threshold method must be explicit")
    classes = np.stack([classify_scalar_scar(values, spec) for spec in specs])
    frequencies = np.stack([(classes == i).mean(axis=0) for i in range(3)], axis=-1)
    return {
        "class_frequencies": frequencies,
        "class_order": ["normal", "border_zone", "core"],
        "n_hypotheses": len(specs),
        "acquisition_sequence": acquisition_sequence,
        "etiology": etiology,
        "method": method,
        "uncertainty_kind": "threshold_sensitivity",
        "probability_calibrated": False,
        "hypotheses": [spec.model_dump(mode="json") for spec in specs],
    }
