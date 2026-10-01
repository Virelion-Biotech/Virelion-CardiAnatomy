import numpy as np
import pytest

from cardianatomy import (
    affine_round_trip_error,
    apply_affine,
    compose_affines,
    invert_affine,
    validate_affine,
)


def test_compose_affines_matches_sequential_application() -> None:
    translate = np.eye(4)
    translate[:3, 3] = [2.0, -1.0, 3.0]

    rotate = np.eye(4)
    rotate[:3, :3] = np.array(
        [
            [0.0, -1.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )

    points = np.array([[1.0, 2.0, 3.0], [0.0, 0.0, 0.0]])
    sequential = apply_affine(apply_affine(points, translate), rotate)
    composed = apply_affine(points, compose_affines(translate, rotate))
    assert np.allclose(composed, sequential)


def test_affine_inverse_round_trip() -> None:
    matrix = np.eye(4)
    matrix[:3, 3] = [3.0, 4.0, -2.0]
    inverse = invert_affine(matrix)
    assert np.allclose(compose_affines(matrix, inverse), np.eye(4))

    points = np.array([[1.0, 2.0, 3.0], [-5.0, 0.5, 9.0]])
    assert affine_round_trip_error(points, matrix) < 1e-12


def test_affine_validation_rejects_singular_transform() -> None:
    matrix = np.eye(4)
    matrix[2, 2] = 0.0
    with pytest.raises(ValueError):
        validate_affine(matrix)


def test_affine_validation_rejects_invalid_homogeneous_row() -> None:
    matrix = np.eye(4)
    matrix[3, 0] = 1.0
    with pytest.raises(ValueError):
        validate_affine(matrix)
