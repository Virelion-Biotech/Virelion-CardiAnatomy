import numpy as np

from cardianatomy import reference_rule_based_microstructure


def test_reference_microstructure_is_orthonormal() -> None:
    c = np.tile([1.0, 0.0, 0.0], (3, 1))
    l = np.tile([0.0, 1.0, 0.0], (3, 1))
    rho = np.array([0.0, 0.5, 1.0])
    fiber, sheet, normal = reference_rule_based_microstructure(c, l, rho)
    np.testing.assert_allclose(np.linalg.norm(fiber, axis=1), 1.0)
    np.testing.assert_allclose(np.linalg.norm(sheet, axis=1), 1.0)
    np.testing.assert_allclose(np.linalg.norm(normal, axis=1), 1.0)
    np.testing.assert_allclose(np.sum(fiber * sheet, axis=1), 0.0, atol=1e-12)
