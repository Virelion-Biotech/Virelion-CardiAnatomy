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


def test_point_validation_rejects_excessive_block_size() -> None:
    points = np.array([[0.0, 0.0, 0.0]])
    try:
        nearest_point_distances(points, points, block_size=1000000)
    except ValueError as exc:
        assert "block_size" in str(exc)
    else:
        raise AssertionError("excessive block size should be rejected")


def test_point_validation_rejects_quadratic_work_explosion() -> None:
    source = np.zeros((5000, 3), dtype=float)
    target = np.zeros((5000, 3), dtype=float)
    try:
        point_set_distance_summary(
            source,
            target,
            max_pair_evaluations=1_000_000,
        )
    except ValueError as exc:
        assert "pair-evaluation limit" in str(exc)
    else:
        raise AssertionError("quadratic workload should be rejected")


def test_point_validation_handles_moderate_large_input_with_small_blocks() -> None:
    rng = np.random.default_rng(42)
    points = rng.normal(size=(1000, 3))
    result = point_set_distance_summary(
        points,
        points.copy(),
        block_size=128,
        max_pair_evaluations=2_000_000,
    )
    assert result.hausdorff == 0.0
    assert result.symmetric_mean == 0.0
