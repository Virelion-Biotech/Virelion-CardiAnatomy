from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .coordinates import apply_affine


def _stable_centroid(points: np.ndarray) -> np.ndarray:
    scale = np.max(np.abs(points), axis=0)
    normalized = np.divide(
        points,
        scale,
        out=np.zeros_like(points),
        where=scale > 0,
    )
    return normalized.mean(axis=0) * scale


def _row_norm(vectors: np.ndarray) -> np.ndarray:
    return np.hypot(
        np.hypot(vectors[:, 0], vectors[:, 1]),
        vectors[:, 2],
    )


def _stable_rms(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(values)):
        raise OverflowError("RMS input contains non-finite values")
    scale = float(np.max(np.abs(values))) if values.size else 0.0
    if scale == 0.0:
        return 0.0
    result = scale * float(np.sqrt(np.mean((values / scale) ** 2)))
    if not np.isfinite(result):
        raise OverflowError("RMS exceeds float64 range")
    return result


@dataclass(frozen=True)
class RigidRegistrationResult:
    matrix: np.ndarray
    rms_error: float
    max_error: float
    source_centroid: np.ndarray
    target_centroid: np.ndarray


def estimate_rigid_transform(
    source_points: np.ndarray,
    target_points: np.ndarray,
    *,
    allow_reflection: bool = False,
) -> RigidRegistrationResult:
    """Estimate a least-squares rigid transform using paired landmarks."""
    source = np.asarray(source_points, dtype=float)
    target = np.asarray(target_points, dtype=float)
    if source.shape != target.shape or source.ndim != 2 or source.shape[1] != 3:
        raise ValueError("source_points and target_points must both have shape (N, 3)")
    if len(source) < 3:
        raise ValueError("At least three paired landmarks are required")
    if not np.all(np.isfinite(source)) or not np.all(np.isfinite(target)):
        raise ValueError("Landmarks must be finite")

    source_centroid = _stable_centroid(source)
    target_centroid = _stable_centroid(target)
    with np.errstate(over="ignore", invalid="ignore"):
        source_centered = source - source_centroid
        target_centered = target - target_centroid
    if (
        not np.all(np.isfinite(source_centered))
        or not np.all(np.isfinite(target_centered))
    ):
        raise OverflowError("landmark coordinate span exceeds float64 range")
    source_rank = int(np.linalg.matrix_rank(source_centered))
    target_rank = int(np.linalg.matrix_rank(target_centered))
    if source_rank < 2 or target_rank < 2:
        raise ValueError(
            "Rigid registration requires at least three non-collinear landmarks "
            "in both point sets"
        )

    source_scale = float(np.max(np.abs(source_centered)))
    target_scale = float(np.max(np.abs(target_centered)))
    if source_scale == 0.0 or target_scale == 0.0:
        raise ValueError("landmark sets must span nonzero geometry")
    covariance = (
        source_centered / source_scale
    ).T @ (
        target_centered / target_scale
    )
    u, _, vt = np.linalg.svd(covariance)
    rotation = vt.T @ u.T
    if np.linalg.det(rotation) < 0 and not allow_reflection:
        vt[-1, :] *= -1
        rotation = vt.T @ u.T

    with np.errstate(over="ignore", invalid="ignore"):
        translation = target_centroid - rotation @ source_centroid
    if not np.all(np.isfinite(translation)):
        raise OverflowError("rigid-registration translation exceeds float64 range")
    matrix = np.eye(4, dtype=float)
    matrix[:3, :3] = rotation
    matrix[:3, 3] = translation

    transformed = apply_affine(source, matrix)
    error = _row_norm(transformed - target)
    return RigidRegistrationResult(
        matrix=matrix,
        rms_error=_stable_rms(error),
        max_error=float(error.max()),
        source_centroid=source_centroid,
        target_centroid=target_centroid,
    )


def registration_residuals(
    source_points: np.ndarray,
    target_points: np.ndarray,
    matrix: np.ndarray,
) -> np.ndarray:
    source = np.asarray(source_points, dtype=float)
    target = np.asarray(target_points, dtype=float)
    if (
        source.shape != target.shape
        or source.ndim != 2
        or source.shape[1] != 3
    ):
        raise ValueError(
            "source_points and target_points must both have shape (N, 3)"
        )
    if not np.all(np.isfinite(source)) or not np.all(np.isfinite(target)):
        raise ValueError("registration points must be finite")
    with np.errstate(over="ignore", invalid="ignore"):
        difference = apply_affine(source, matrix) - target
    if not np.all(np.isfinite(difference)):
        raise OverflowError("registration residuals exceed float64 range")
    return _row_norm(difference)
