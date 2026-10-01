import numpy as np

from cardianatomy import apply_affine, lps_to_ras_matrix


def test_lps_to_ras_flips_first_two_axes() -> None:
    points = np.array([[1.0, 2.0, 3.0]])
    result = apply_affine(points, lps_to_ras_matrix())
    np.testing.assert_allclose(result, [[-1.0, -2.0, 3.0]])
