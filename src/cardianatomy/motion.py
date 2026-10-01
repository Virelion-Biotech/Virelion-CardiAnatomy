from __future__ import annotations

from dataclasses import dataclass

import numpy as np


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
    displacement = np.linalg.norm(values - reference[None, :, :], axis=2)
    rms_reference = np.sqrt(np.mean(displacement**2, axis=1))
    max_reference = np.max(displacement, axis=1)

    steps = np.linalg.norm(np.diff(values, axis=0), axis=2)
    rms_steps = np.sqrt(np.mean(steps**2, axis=1))
    max_steps = np.max(steps, axis=1)
    path_length = np.sum(steps, axis=0)

    return MeshMotionSummary(
        phase_count=int(phase_count),
        point_count=int(point_count),
        reference_phase=int(reference_phase),
        rms_displacement_to_reference=tuple(float(x) for x in rms_reference),
        max_displacement_to_reference=tuple(float(x) for x in max_reference),
        rms_step_displacement=tuple(float(x) for x in rms_steps),
        max_step_displacement=tuple(float(x) for x in max_steps),
        mean_vertex_path_length=float(np.mean(path_length)),
        max_vertex_path_length=float(np.max(path_length)),
    )


def cyclic_closure_error(frames: np.ndarray) -> dict[str, float]:
    """Measure first/last-phase mismatch for a nominally cyclic mesh sequence."""
    values = np.asarray(frames, dtype=float)
    if values.ndim != 3 or values.shape[2] != 3 or values.shape[0] < 2:
        raise ValueError("frames must have shape (T, N, 3) with T >= 2")
    mismatch = np.linalg.norm(values[-1] - values[0], axis=1)
    return {
        "mean": float(np.mean(mismatch)),
        "rms": float(np.sqrt(np.mean(mismatch**2))),
        "max": float(np.max(mismatch)),
    }
