import numpy as np
import pytest

from cardianatomy import (
    chamber_volume_curve_ml,
    select_ed_es_from_segmentation,
    select_ed_es_from_volume_curve,
)


def test_select_ed_es_from_volume_curve() -> None:
    result = select_ed_es_from_volume_curve(
        np.array([120.0, 100.0, 70.0, 80.0, 110.0])
    )
    assert result.ed_phase == 0
    assert result.es_phase == 2
    assert result.stroke_volume_ml == 50.0
    assert np.isclose(result.ejection_fraction, 50.0 / 120.0)


def test_cine_segmentation_volume_curve_and_selection() -> None:
    labels = np.zeros((3, 3, 3, 3), dtype=np.uint8)
    labels[:, :, :, 0] = 1
    labels[:2, :, :, 1] = 1
    labels[:1, :, :, 2] = 1
    curve = chamber_volume_curve_ml(
        labels,
        chamber_label=1,
        spacing_mm=(1.0, 1.0, 1.0),
    )
    assert curve.tolist() == [0.027, 0.018, 0.009]
    result = select_ed_es_from_segmentation(
        labels,
        chamber_label=1,
        spacing_mm=(1.0, 1.0, 1.0),
    )
    assert result.ed_phase == 0
    assert result.es_phase == 2


def test_flat_volume_curve_is_rejected() -> None:
    with pytest.raises(ValueError):
        select_ed_es_from_volume_curve(np.array([100.0, 100.0, 100.0]))
