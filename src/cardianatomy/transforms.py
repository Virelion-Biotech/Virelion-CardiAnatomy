from __future__ import annotations

import numpy as np


def validate_affine(matrix: np.ndarray) -> np.ndarray:
    value = np.asarray(matrix, dtype=float)
    if value.shape != (4, 4):
        raise ValueError("affine must have shape (4, 4)")
    if not np.all(np.isfinite(value)):
        raise ValueError("affine must contain only finite values")
    if not np.isclose(value[3, 3], 1.0):
        raise ValueError("homogeneous affine bottom-right element must equal 1")
    if not np.allclose(value[3, :3], 0.0):
        raise ValueError("affine bottom row must be [0, 0, 0, 1]")
    if abs(np.linalg.det(value[:3, :3])) < 1e-12:
        raise ValueError("affine spatial transform is singular")
    return value


def invert_affine(matrix: np.ndarray) -> np.ndarray:
    return np.linalg.inv(validate_affine(matrix))


def compose_affines(*matrices: np.ndarray) -> np.ndarray:
    """Compose transforms in application order."""
    if not matrices:
        return np.eye(4, dtype=float)
    result = np.eye(4, dtype=float)
    for matrix in matrices:
        result = validate_affine(matrix) @ result
    return validate_affine(result)


def affine_round_trip_error(
    points: np.ndarray,
    matrix: np.ndarray,
) -> float:
    from .coordinates import apply_affine

    values = np.asarray(points, dtype=float)
    forward = apply_affine(values, validate_affine(matrix))
    restored = apply_affine(forward, invert_affine(matrix))
    return float(np.max(np.linalg.norm(values - restored, axis=1)))
