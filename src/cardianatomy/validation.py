from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PointSetDistanceSummary:
    reference_to_prediction_mean: float
    prediction_to_reference_mean: float
    symmetric_mean: float
    symmetric_rms: float
    hd95: float
    hausdorff: float
    reference_point_count: int
    prediction_point_count: int


def _validate_point_set(points: np.ndarray, name: str) -> np.ndarray:
    values = np.asarray(points, dtype=float)
    if values.ndim != 2 or values.shape[1] != 3 or len(values) == 0:
        raise ValueError(f"{name} must have shape (N, 3) with N > 0")
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{name} must contain only finite values")
    return values


def nearest_point_distances(
    source_points: np.ndarray,
    target_points: np.ndarray,
    *,
    block_size: int = 1024,
    max_pair_evaluations: int = 20_000_000,
    backend: str = "brute_force",
) -> np.ndarray:
    """Return Euclidean distance from each source point to its nearest target point."""
    source = _validate_point_set(source_points, "source_points")
    target = _validate_point_set(target_points, "target_points")
    if (
        isinstance(block_size, bool)
        or not isinstance(block_size, int)
        or not 1 <= block_size <= 2048
    ):
        raise ValueError("block_size must be an integer in [1, 2048]")
    if (
        isinstance(max_pair_evaluations, bool)
        or not isinstance(max_pair_evaluations, int)
        or max_pair_evaluations < 1
    ):
        raise ValueError("max_pair_evaluations must be a positive integer")
    if backend not in {"brute_force", "scipy_kdtree"}:
        raise ValueError("Unknown distance backend")
    if backend == "scipy_kdtree":
        try:
            from scipy.spatial import cKDTree
        except ImportError as exc:
            raise RuntimeError(
                "Install virelion-cardianatomy[validation] for KD-tree distances"
            ) from exc
        distance, _ = cKDTree(target).query(source, k=1, eps=0, workers=1)
        if not np.all(np.isfinite(distance)):
            raise OverflowError("KD-tree distances exceed float64 range")
        return np.asarray(distance, dtype=float)
    pair_count = len(source) * len(target)
    if pair_count > max_pair_evaluations:
        raise ValueError(
            "point-set comparison exceeds the brute-force pair-evaluation limit; "
            "use a scalable spatial-index validation backend"
        )

    output = np.empty(len(source), dtype=float)
    for source_start in range(0, len(source), block_size):
        source_block = source[source_start : source_start + block_size]
        best = np.full(len(source_block), np.inf, dtype=float)
        for target_start in range(0, len(target), block_size):
            target_block = target[target_start : target_start + block_size]
            with np.errstate(over="ignore", invalid="ignore"):
                difference = source_block[:, None, :] - target_block[None, :, :]
            if not np.all(np.isfinite(difference)):
                raise OverflowError("point-set coordinate differences exceed float64 range")
            distance = np.hypot(
                np.hypot(difference[:, :, 0], difference[:, :, 1]),
                difference[:, :, 2],
            )
            best = np.minimum(best, np.min(distance, axis=1))
        output[source_start : source_start + len(source_block)] = best
    return output


def point_set_distance_summary(
    reference_points: np.ndarray,
    prediction_points: np.ndarray,
    *,
    block_size: int = 1024,
    max_pair_evaluations: int = 20_000_000,
    backend: str = "brute_force",
) -> PointSetDistanceSummary:
    """Compute symmetric nearest-point distances in the input coordinate units."""
    reference = _validate_point_set(reference_points, "reference_points")
    prediction = _validate_point_set(prediction_points, "prediction_points")
    forward = nearest_point_distances(
        reference,
        prediction,
        block_size=block_size,
        max_pair_evaluations=max_pair_evaluations,
        backend=backend,
    )
    backward = nearest_point_distances(
        prediction,
        reference,
        block_size=block_size,
        max_pair_evaluations=max_pair_evaluations,
        backend=backend,
    )
    all_distances = np.concatenate([forward, backward])
    distance_scale = float(np.max(all_distances))
    if distance_scale == 0.0:
        symmetric_rms = 0.0
    else:
        symmetric_rms = distance_scale * float(
            np.sqrt(np.mean((all_distances / distance_scale) ** 2))
        )
    hd95 = max(
        float(np.quantile(forward, 0.95)),
        float(np.quantile(backward, 0.95)),
    )
    return PointSetDistanceSummary(
        reference_to_prediction_mean=float(np.mean(forward)),
        prediction_to_reference_mean=float(np.mean(backward)),
        symmetric_mean=float(np.mean(all_distances)),
        symmetric_rms=symmetric_rms,
        hd95=hd95,
        hausdorff=float(max(np.max(forward), np.max(backward))),
        reference_point_count=int(len(reference)),
        prediction_point_count=int(len(prediction)),
    )


def segmentation_overlap_metrics(
    reference_labels: np.ndarray,
    prediction_labels: np.ndarray,
    *,
    labels: set[int] | None = None,
    background_label: int | None = 0,
) -> dict[int, dict[str, float | int]]:
    """Compute exact-array Dice/Jaccard metrics for discrete segmentation labels."""
    reference = np.asarray(reference_labels)
    prediction = np.asarray(prediction_labels)
    if reference.shape != prediction.shape:
        raise ValueError("reference_labels and prediction_labels must have the same shape")
    if reference.size == 0:
        raise ValueError("segmentation arrays must not be empty")
    if not np.issubdtype(reference.dtype, np.number) or not np.issubdtype(
        prediction.dtype, np.number
    ):
        raise ValueError("segmentation arrays must be numeric")
    if not np.all(np.isfinite(reference)) or not np.all(np.isfinite(prediction)):
        raise ValueError("segmentation arrays must be finite")
    if not np.all(reference == np.floor(reference)):
        raise ValueError("reference_labels must be integer-valued")
    if not np.all(prediction == np.floor(prediction)):
        raise ValueError("prediction_labels must be integer-valued")

    for array in (reference, prediction):
        if np.issubdtype(array.dtype, np.floating) and np.any(array >= float(2**63)):
            raise ValueError("segmentation labels exceed int64 range")
    limits = np.iinfo(np.int64)
    if (
        np.any(reference < limits.min)
        or np.any(reference > limits.max)
        or np.any(prediction < limits.min)
        or np.any(prediction > limits.max)
    ):
        raise ValueError("segmentation labels exceed int64 range")
    reference = reference.astype(np.int64, copy=False)
    prediction = prediction.astype(np.int64, copy=False)
    selected = (
        set(int(value) for value in labels)
        if labels is not None
        else set(np.unique(reference)) | set(np.unique(prediction))
    )
    if background_label is not None:
        selected.discard(int(background_label))

    result: dict[int, dict[str, float | int]] = {}
    for label in sorted(selected):
        ref_mask = reference == label
        pred_mask = prediction == label
        ref_count = int(np.count_nonzero(ref_mask))
        pred_count = int(np.count_nonzero(pred_mask))
        intersection = int(np.count_nonzero(ref_mask & pred_mask))
        union = ref_count + pred_count - intersection
        denominator = ref_count + pred_count

        dice = 1.0 if denominator == 0 else 2.0 * intersection / denominator
        jaccard = 1.0 if union == 0 else intersection / union
        result[label] = {
            "dice": float(dice),
            "jaccard": float(jaccard),
            "intersection_voxels": intersection,
            "reference_voxels": ref_count,
            "prediction_voxels": pred_count,
            "voxel_count_bias": pred_count - ref_count,
        }
    return result
