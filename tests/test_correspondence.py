import numpy as np
import pytest

from cardianatomy import (
    compare_corresponding_meshes,
    connectivity_fingerprint,
    transfer_point_data_by_index,
)


def test_correspondence_detects_identical_connectivity() -> None:
    reference = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    )
    target = reference + np.array([1.0, 2.0, 3.0])
    cells = np.array([[0, 1, 2]])

    result = compare_corresponding_meshes(
        reference,
        target,
        reference_cells=cells,
        target_cells=cells.copy(),
    )
    assert result.connectivity_identical is True
    assert np.isclose(result.rms_displacement, np.sqrt(14.0))


def test_correspondence_reports_changed_connectivity() -> None:
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
        ]
    )
    result = compare_corresponding_meshes(
        points,
        points.copy(),
        reference_cells=np.array([[0, 1, 2], [1, 3, 2]]),
        target_cells=np.array([[0, 1, 3], [0, 3, 2]]),
    )
    assert result.connectivity_identical is False


def test_connectivity_fingerprint_is_order_sensitive() -> None:
    first = np.array([[0, 1, 2]])
    second = np.array([[0, 2, 1]])
    assert connectivity_fingerprint(first) != connectivity_fingerprint(second)


def test_transfer_point_data_uses_explicit_index_map() -> None:
    values = np.array([10.0, 20.0, 30.0])
    mapped = transfer_point_data_by_index(values, np.array([2, 0, 1]))
    assert mapped.tolist() == [30.0, 10.0, 20.0]


def test_transfer_point_data_rejects_invalid_indices() -> None:
    with pytest.raises(ValueError):
        transfer_point_data_by_index(np.array([1.0]), np.array([1]))
