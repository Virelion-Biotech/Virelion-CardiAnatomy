from __future__ import annotations

import numpy as np


def lps_to_ras_matrix() -> np.ndarray:
    """Return the standard homogeneous DICOM-LPS -> NIfTI-RAS axis transform."""
    return np.diag([-1.0, -1.0, 1.0, 1.0])


def ras_to_lps_matrix() -> np.ndarray:
    return lps_to_ras_matrix()


def apply_affine(points: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=float)
    matrix = np.asarray(matrix, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must have shape (N, 3)")
    if matrix.shape != (4, 4):
        raise ValueError("matrix must have shape (4, 4)")
    homogeneous = np.column_stack([points, np.ones(len(points), dtype=float)])
    transformed = homogeneous @ matrix.T
    scale = transformed[:, 3:4]
    if np.any(np.isclose(scale, 0.0)):
        raise ValueError("affine produced invalid homogeneous coordinates")
    return transformed[:, :3] / scale


def affine_is_finite(matrix: np.ndarray) -> bool:
    matrix = np.asarray(matrix, dtype=float)
    return matrix.shape == (4, 4) and bool(np.all(np.isfinite(matrix)))
