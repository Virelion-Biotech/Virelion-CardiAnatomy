import numpy as np

from cardianatomy import estimate_rigid_transform, registration_residuals


def test_rigid_registration_recovers_known_transform() -> None:
    source = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 2.0, 0.0],
            [0.0, 0.0, 3.0],
        ]
    )
    rotation = np.array(
        [
            [0.0, -1.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    translation = np.array([5.0, -2.0, 1.5])
    target = source @ rotation.T + translation

    result = estimate_rigid_transform(source, target)
    residuals = registration_residuals(source, target, result.matrix)

    assert np.allclose(result.matrix[:3, :3], rotation)
    assert np.allclose(result.matrix[:3, 3], translation)
    assert np.max(residuals) < 1e-10
