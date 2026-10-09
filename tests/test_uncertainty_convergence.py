import numpy as np
from cardianatomy.scar import scar_threshold_ensemble
from cardianatomy.models import ScarThresholdSpec
from cardianatomy.convergence import three_grid_convergence


def test_scar_hypotheses_preserve_ambiguity_and_do_not_claim_calibration():
    result = scar_threshold_ensemble(
        [0, 2, 5],
        [
            ScarThresholdSpec(border_threshold=1, core_threshold=4),
            ScarThresholdSpec(border_threshold=3, core_threshold=6),
        ],
        acquisition_sequence="LGE",
        etiology="ischemic",
        method="declared sensitivity",
    )
    assert np.allclose(result["class_frequencies"].sum(axis=1), 1)
    assert np.allclose(result["class_frequencies"][1], [0.5, 0.5, 0])
    assert not result["probability_calibrated"]


def test_three_grid_reports_known_order_and_rejects_oscillation():
    result = three_grid_convergence([1, 0.5, 0.25], [2, 1.25, 1.0625], maximum_relative_gci=0.1)
    assert abs(result["observed_order"] - 2) < 1e-12
    assert result["extrapolated_endpoint"] == 1
    assert result["passed"]
    assert not three_grid_convergence([1, 0.5, 0.25], [1, 2, 1.5])["passed"]
