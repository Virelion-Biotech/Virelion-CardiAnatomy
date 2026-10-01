from __future__ import annotations

import numpy as np

from .models import FiberAngleProfile


def _normalize(vectors: np.ndarray, label: str) -> np.ndarray:
    vectors = np.asarray(vectors, dtype=float)
    if vectors.ndim != 2 or vectors.shape[1] != 3:
        raise ValueError(f"{label} must have shape (N, 3)")
    norms = np.linalg.norm(vectors, axis=1)
    if np.any(~np.isfinite(norms)) or np.any(norms <= 0):
        raise ValueError(f"{label} contains invalid vectors")
    return vectors / norms[:, None]


def orthonormal_local_frame(
    circumferential: np.ndarray,
    longitudinal: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build a right-handed local basis with Gram-Schmidt orthogonalization."""
    c = _normalize(circumferential, "circumferential")
    l_raw = np.asarray(longitudinal, dtype=float)
    if l_raw.shape != c.shape:
        raise ValueError("longitudinal must match circumferential shape")
    longitudinal_axis = l_raw - np.sum(l_raw * c, axis=1)[:, None] * c
    longitudinal_axis = _normalize(longitudinal_axis, "longitudinal")
    t = _normalize(np.cross(c, longitudinal_axis), "transmural")
    longitudinal_axis = _normalize(np.cross(t, c), "longitudinal")
    return c, longitudinal_axis, t


def reference_rule_based_microstructure(
    circumferential: np.ndarray,
    longitudinal: np.ndarray,
    transmural_coordinate: np.ndarray,
    profile: FiberAngleProfile | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate a reference rule-based fiber/sheet/sheet-normal field.

    This is a small, original integration/reference implementation inspired by the
    published LDRB family of methods. It is not a replacement for validated LDRB solvers.
    """
    profile = profile or FiberAngleProfile()
    c, longitudinal_axis, t = orthonormal_local_frame(
        circumferential,
        longitudinal,
    )
    rho = np.asarray(transmural_coordinate, dtype=float)
    if rho.ndim != 1 or len(rho) != len(c):
        raise ValueError("transmural_coordinate must have shape (N,)")
    if np.any(~np.isfinite(rho)) or np.any((rho < 0) | (rho > 1)):
        raise ValueError("transmural_coordinate must lie in [0, 1]")

    alpha = np.deg2rad(
        profile.alpha_endo_deg
        + rho * (profile.alpha_epi_deg - profile.alpha_endo_deg)
    )
    beta = np.deg2rad(
        profile.beta_endo_deg
        + rho * (profile.beta_epi_deg - profile.beta_endo_deg)
    )

    fiber = (
        np.cos(alpha)[:, None] * c
        + np.sin(alpha)[:, None] * longitudinal_axis
    )
    cross_fiber = (
        -np.sin(alpha)[:, None] * c
        + np.cos(alpha)[:, None] * longitudinal_axis
    )
    sheet = np.cos(beta)[:, None] * t + np.sin(beta)[:, None] * cross_fiber
    fiber = _normalize(fiber, "fiber")
    sheet = sheet - np.sum(sheet * fiber, axis=1)[:, None] * fiber
    sheet = _normalize(sheet, "sheet")
    sheet_normal = _normalize(np.cross(fiber, sheet), "sheet_normal")
    return fiber, sheet, sheet_normal
