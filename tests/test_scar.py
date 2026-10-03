import numpy as np
import pytest

from cardianatomy import ScarThresholdSpec, classify_scalar_scar, scar_fractions


def test_explicit_scar_threshold_application() -> None:
    values = np.array([0.1, 0.5, 0.9])
    labels = classify_scalar_scar(
        values, ScarThresholdSpec(border_threshold=0.4, core_threshold=0.8)
    )
    assert labels.tolist() == [0, 1, 2]
    fractions = scar_fractions(labels)
    assert fractions["core_fraction"] == pytest.approx(1 / 3)
