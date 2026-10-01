from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .coordinates import apply_affine


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

    source_centroid = source.mean(axis=0)
    target_centroid = target.mean(axis=0)
    source_centered = source - source_centroid
    target_centered = target - target_centroid

    covariance = source_centered.T @ target_centered
    u, _, vt = np.linalg.svd(covariance)
    rotation = vt.T @ u.T
    if np.linalg.det(rotation) < 0 and not allow_reflection:
        vt[-1, :] *= -1
        rotation = vt.T @ u.T

    translation = target_centroid - rotation @ source_centroid
    matrix = np.eye(4, dtype=float)
    matrix[:3, :3] = rotation
    matrix[:3, 3] = translation

    transformed = apply_affine(source, matrix)
    error = np.linalg.norm(transformed - target, axis=1)
    return RigidRegistrationResult(
        matrix=matrix,
        rms_error=float(np.sqrt(np.mean(error**2))),
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
    if source.shape != target.shape:
        raise ValueError("source_points and target_points must have the same shape")
    return np.linalg.norm(apply_affine(source, matrix) - target, axis=1)
