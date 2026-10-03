from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .segmentation import label_volumes_ml


@dataclass(frozen=True)
class CinePhaseSelection:
    ed_phase: int
    es_phase: int
    volumes_ml: tuple[float, ...]
    stroke_volume_ml: float
    ejection_fraction: float | None
    dynamic_range_fraction: float


def chamber_volume_curve_ml(
    labels: np.ndarray,
    *,
    chamber_label: int,
    spacing_mm: tuple[float, float, float],
    phase_axis: int = -1,
) -> np.ndarray:
    """Compute one chamber's 3D label volume across cine phases."""
    values = np.asarray(labels)
    if chamber_label < 0:
        raise ValueError("chamber_label must be non-negative")
    if values.ndim != 4:
        raise ValueError("cine segmentation must have four dimensions")
    phase_axis = phase_axis % values.ndim
    phases = np.moveaxis(values, phase_axis, 0)
    curve = []
    for phase in phases:
        volumes = label_volumes_ml(phase, spacing_mm)
        curve.append(float(volumes.get(int(chamber_label), 0.0)))
    return np.asarray(curve, dtype=float)


def select_ed_es_from_volume_curve(
    volumes_ml: np.ndarray,
    *,
    minimum_dynamic_range_fraction: float = 0.02,
) -> CinePhaseSelection:
    """Select ED at maximum chamber volume and ES at minimum volume."""
    if (
        not np.isfinite(minimum_dynamic_range_fraction)
        or not 0.0 <= minimum_dynamic_range_fraction < 1.0
    ):
        raise ValueError(
            "minimum_dynamic_range_fraction must lie in [0, 1)"
        )
    volumes = np.asarray(volumes_ml, dtype=float)
    if volumes.ndim != 1 or len(volumes) < 2:
        raise ValueError("volumes_ml must be a one-dimensional curve with >=2 phases")
    if not np.all(np.isfinite(volumes)) or np.any(volumes < 0):
        raise ValueError("cine chamber volumes must be finite and non-negative")
    maximum = float(volumes.max())
    minimum = float(volumes.min())
    if maximum <= 0:
        raise ValueError("cine chamber volume curve contains no positive volume")
    dynamic_range = (maximum - minimum) / maximum
    if dynamic_range < minimum_dynamic_range_fraction:
        raise ValueError(
            "cine chamber volume curve has insufficient dynamic range "
            "for robust ED/ES selection"
        )
    ed_phase = int(np.argmax(volumes))
    es_phase = int(np.argmin(volumes))
    stroke_volume = maximum - minimum
    return CinePhaseSelection(
        ed_phase=ed_phase,
        es_phase=es_phase,
        volumes_ml=tuple(float(value) for value in volumes),
        stroke_volume_ml=float(stroke_volume),
        ejection_fraction=float(stroke_volume / maximum),
        dynamic_range_fraction=float(dynamic_range),
    )


def select_ed_es_from_segmentation(
    labels: np.ndarray,
    *,
    chamber_label: int,
    spacing_mm: tuple[float, float, float],
    phase_axis: int = -1,
    minimum_dynamic_range_fraction: float = 0.02,
) -> CinePhaseSelection:
    curve = chamber_volume_curve_ml(
        labels,
        chamber_label=chamber_label,
        spacing_mm=spacing_mm,
        phase_axis=phase_axis,
    )
    return select_ed_es_from_volume_curve(
        curve,
        minimum_dynamic_range_fraction=minimum_dynamic_range_fraction,
    )
