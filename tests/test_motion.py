import numpy as np

from cardianatomy import cyclic_closure_error, summarize_mesh_sequence


def test_mesh_motion_summary_tracks_dense_correspondence() -> None:
    base = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    frames = np.stack(
        [
            base,
            base + np.array([1.0, 0.0, 0.0]),
            base + np.array([2.0, 0.0, 0.0]),
        ]
    )
    result = summarize_mesh_sequence(frames)
    assert result.phase_count == 3
    assert result.point_count == 2
    assert result.rms_displacement_to_reference == (0.0, 1.0, 2.0)
    assert result.rms_step_displacement == (1.0, 1.0)
    assert result.mean_vertex_path_length == 2.0


def test_cyclic_closure_error_is_zero_for_closed_sequence() -> None:
    base = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    frames = np.stack(
        [
            base,
            base + np.array([0.5, 0.0, 0.0]),
            base,
        ]
    )
    closure = cyclic_closure_error(frames)
    assert closure == {"mean": 0.0, "rms": 0.0, "max": 0.0}
