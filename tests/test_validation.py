import numpy as np

from cardianatomy import (
    nearest_point_distances,
    point_set_distance_summary,
    segmentation_overlap_metrics,
)


def test_segmentation_overlap_metrics() -> None:
    reference = np.array([1, 1, 0, 0])
    prediction = np.array([1, 0, 0, 0])
    metrics = segmentation_overlap_metrics(reference, prediction)
    assert np.isclose(metrics[1]["dice"], 2.0 / 3.0)
    assert np.isclose(metrics[1]["jaccard"], 0.5)
    assert metrics[1]["voxel_count_bias"] == -1


def test_segmentation_overlap_can_include_background() -> None:
    reference = np.array([1, 0, 0])
    prediction = np.array([1, 0, 0])
    metrics = segmentation_overlap_metrics(
        reference,
        prediction,
        background_label=None,
    )
    assert metrics[0]["dice"] == 1.0
    assert metrics[1]["dice"] == 1.0


def test_nearest_point_distances_and_summary() -> None:
    reference = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    prediction = np.array([[1.0, 0.0, 0.0], [2.0, 0.0, 0.0]])

    distances = nearest_point_distances(reference, prediction, block_size=1)
    assert distances.tolist() == [1.0, 0.0]

    summary = point_set_distance_summary(
        reference,
        prediction,
        block_size=1,
    )
    assert np.isclose(summary.symmetric_mean, 0.5)
    assert np.isclose(summary.symmetric_rms, np.sqrt(0.5))
    assert summary.hausdorff == 1.0
    assert np.isclose(summary.hd95, 0.95)
