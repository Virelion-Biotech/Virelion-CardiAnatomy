from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _vector_norm(vectors: np.ndarray) -> np.ndarray:
    return np.hypot(
        np.hypot(vectors[..., 0], vectors[..., 1]),
        vectors[..., 2],
    )


def _stable_rms_rows(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if values.ndim != 2:
        raise ValueError("RMS rows require a two-dimensional array")
    scale = np.max(np.abs(values), axis=1)
    normalized = np.divide(
        values,
        scale[:, None],
        out=np.zeros_like(values),
        where=scale[:, None] > 0,
    )
    result = scale * np.sqrt(np.mean(normalized**2, axis=1))
    if not np.all(np.isfinite(result)):
        raise OverflowError("motion RMS exceeds float64 range")
    return result


def _stable_sum_columns(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    scale = np.max(np.abs(values), axis=0)
    normalized = np.divide(
        values,
        scale[None, :],
        out=np.zeros_like(values),
        where=scale[None, :] > 0,
    )
    result = scale * np.sum(normalized, axis=0)
    if not np.all(np.isfinite(result)):
        raise OverflowError("motion path length exceeds float64 range")
    return result


@dataclass(frozen=True)
class MeshMotionSummary:
    phase_count: int
    point_count: int
    reference_phase: int
    rms_displacement_to_reference: tuple[float, ...]
    max_displacement_to_reference: tuple[float, ...]
    rms_step_displacement: tuple[float, ...]
    max_step_displacement: tuple[float, ...]
    mean_vertex_path_length: float
    max_vertex_path_length: float


def summarize_mesh_sequence(
    frames: np.ndarray,
    *,
    reference_phase: int = 0,
) -> MeshMotionSummary:
    """Summarize motion for a dense-correspondence 3D+t mesh sequence."""
    values = np.asarray(frames, dtype=float)
    if values.ndim != 3 or values.shape[2] != 3:
        raise ValueError("frames must have shape (T, N, 3)")
    phase_count, point_count, _ = values.shape
    if phase_count < 2 or point_count < 1:
        raise ValueError("mesh sequence requires at least two phases and one point")
    if not np.all(np.isfinite(values)):
        raise ValueError("mesh sequence coordinates must be finite")
    if not 0 <= reference_phase < phase_count:
        raise ValueError("reference_phase is outside the mesh sequence")

    reference = values[reference_phase]
    with np.errstate(over="ignore", invalid="ignore"):
        displacement_vectors = values - reference[None, :, :]
        step_vectors = np.diff(values, axis=0)
    if (
        not np.all(np.isfinite(displacement_vectors))
        or not np.all(np.isfinite(step_vectors))
    ):
        raise OverflowError("mesh coordinate differences exceed float64 range")

    displacement = _vector_norm(displacement_vectors)
    steps = _vector_norm(step_vectors)
    rms_reference = _stable_rms_rows(displacement)
    max_reference = np.max(displacement, axis=1)
    rms_steps = _stable_rms_rows(steps)
    max_steps = np.max(steps, axis=1)
    path_length = _stable_sum_columns(steps)

    return MeshMotionSummary(
        phase_count=int(phase_count),
        point_count=int(point_count),
        reference_phase=int(reference_phase),
        rms_displacement_to_reference=tuple(float(x) for x in rms_reference),
        max_displacement_to_reference=tuple(float(x) for x in max_reference),
        rms_step_displacement=tuple(float(x) for x in rms_steps),
        max_step_displacement=tuple(float(x) for x in max_steps),
        mean_vertex_path_length=(
            0.0
            if not len(path_length)
            else float(
                np.max(path_length)
                * np.mean(
                    path_length / np.max(path_length)
                    if np.max(path_length) > 0
                    else path_length
                )
            )
        ),
        max_vertex_path_length=float(np.max(path_length)),
    )


def cyclic_closure_error(frames: np.ndarray) -> dict[str, float]:
    """Measure first/last-phase mismatch for a nominally cyclic mesh sequence."""
    values = np.asarray(frames, dtype=float)
    if (
        values.ndim != 3
        or values.shape[2] != 3
        or values.shape[0] < 2
        or values.shape[1] < 1
    ):
        raise ValueError("frames must have shape (T, N, 3) with T >= 2 and N >= 1")
    if not np.all(np.isfinite(values)):
        raise ValueError("mesh sequence coordinates must be finite")
    with np.errstate(over="ignore", invalid="ignore"):
        delta = values[-1] - values[0]
    if not np.all(np.isfinite(delta)):
        raise OverflowError("cyclic closure differences exceed float64 range")
    mismatch = _vector_norm(delta)
    scale = float(np.max(mismatch))
    mean = (
        0.0
        if scale == 0.0
        else scale * float(np.mean(mismatch / scale))
    )
    return {
        "mean": mean,
        "rms": float(_stable_rms_rows(mismatch[None, :])[0]),
        "max": scale,
    }
