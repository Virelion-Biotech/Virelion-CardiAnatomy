import numpy as np
import pytest

from cardianatomy import (
    inspect_tetra_mesh,
    inspect_triangle_surface,
    qc_from_inspection,
    tetra_mean_ratio_quality,
    tetra_scaled_jacobian_quality,
    triangle_shape_quality,
)


def test_clean_tetra_mesh_passes_reference_qc() -> None:
    points = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
    tetra = np.array([[0, 1, 2, 3]], dtype=int)
    inspection = inspect_tetra_mesh(points, tetra)
    qc = qc_from_inspection(inspection)
    assert qc.passed
    assert inspection.min_abs_tetra_volume > 0


def test_degenerate_tetra_fails_qc() -> None:
    points = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], dtype=float)
    tetra = np.array([[0, 1, 2, 3]], dtype=int)
    qc = qc_from_inspection(inspect_tetra_mesh(points, tetra))
    assert not qc.passed
    assert not qc.checks["no_degenerate_cells"]


def test_open_surface_can_be_allowed_or_required_watertight() -> None:
    points = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float)
    triangles = np.array([[0, 1, 2]], dtype=int)
    inspection = inspect_triangle_surface(points, triangles)
    assert qc_from_inspection(inspection).passed
    assert not qc_from_inspection(inspection, require_watertight=True).passed


def test_nonmanifold_surface_without_boundary_edges_is_not_watertight() -> None:
    # Two closed tetrahedral shells share an edge: four incident faces there.
    points = np.array(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [0, -1, 0], [0, 0, -1]],
        dtype=float,
    )
    triangles = np.array(
        [[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3],
         [0, 4, 1], [0, 1, 5], [0, 5, 4], [1, 4, 5]],
    )
    inspection = inspect_triangle_surface(points, triangles)
    assert inspection.boundary_edge_count == 0
    assert inspection.nonmanifold_edge_count == 1
    assert inspection.metadata["duplicate_cell_count"] == 0
    qc = qc_from_inspection(inspection, require_watertight=True)
    assert not qc.checks["watertight"]
    assert "watertight" in qc.errors
    assert not qc.passed


@pytest.mark.parametrize("boundary,nonmanifold", [(None, 0), (0, None), (None, None)])
def test_unknown_topology_cannot_establish_watertightness(boundary, nonmanifold) -> None:
    from cardianatomy import MeshInspection

    inspection = MeshInspection(
        point_count=4,
        cell_count=4,
        triangle_count=4,
        connected_components=1,
        boundary_edge_count=boundary,
        nonmanifold_edge_count=nonmanifold,
    )
    qc = qc_from_inspection(inspection, require_watertight=True)
    assert not qc.checks["watertight"]
    assert not qc.passed


def test_closed_manifold_surface_retains_watertight_pass() -> None:
    points = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
    triangles = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
    qc = qc_from_inspection(inspect_triangle_surface(points, triangles), require_watertight=True)
    assert qc.checks["watertight"]
    assert qc.passed


def test_regular_tetra_has_high_shape_quality() -> None:
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.5, np.sqrt(3.0) / 2.0, 0.0],
            [0.5, np.sqrt(3.0) / 6.0, np.sqrt(2.0 / 3.0)],
        ]
    )
    tetra = np.array([[0, 1, 2, 3]])
    quality = tetra_mean_ratio_quality(points, tetra)
    assert np.isclose(quality[0], 1.0)


def test_equilateral_triangle_has_unit_shape_quality() -> None:
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.5, np.sqrt(3.0) / 2.0, 0.0],
        ]
    )
    triangles = np.array([[0, 1, 2]])
    quality = triangle_shape_quality(points, triangles)
    assert np.isclose(quality[0], 1.0)


def test_shape_quality_threshold_can_fail_distorted_tetra() -> None:
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.001, 0.001, 0.0001],
        ]
    )
    tetra = np.array([[0, 1, 2, 3]])
    inspection = inspect_tetra_mesh(points, tetra)
    qc = qc_from_inspection(inspection, minimum_shape_quality=0.1)
    assert not qc.passed
    assert not qc.checks["minimum_shape_quality"]


def test_regular_tetra_has_unit_scaled_jacobian() -> None:
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.5, np.sqrt(3.0) / 2.0, 0.0],
            [0.5, np.sqrt(3.0) / 6.0, np.sqrt(2.0 / 3.0)],
        ]
    )
    tetra = np.array([[0, 1, 2, 3]])
    quality = tetra_scaled_jacobian_quality(points, tetra)
    assert np.isclose(quality[0], 1.0)


def test_distorted_tetra_has_lower_scaled_jacobian() -> None:
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.01, 0.01, 0.001],
        ]
    )
    tetra = np.array([[0, 1, 2, 3]])
    quality = tetra_scaled_jacobian_quality(points, tetra)
    assert 0.0 <= quality[0] < 0.1


def test_unused_points_fail_qc() -> None:
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [99.0, 99.0, 99.0],
        ]
    )
    tetra = np.array([[0, 1, 2, 3]])
    inspection = inspect_tetra_mesh(points, tetra)
    qc = qc_from_inspection(inspection)
    assert inspection.metadata["unused_point_count"] == 1
    assert not qc.passed
    assert not qc.checks["no_unused_points"]


def test_duplicate_tetrahedra_fail_qc_even_with_reordered_nodes() -> None:
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    tetra = np.array([[0, 1, 2, 3], [1, 0, 3, 2]])
    inspection = inspect_tetra_mesh(points, tetra)
    qc = qc_from_inspection(inspection)
    assert inspection.metadata["duplicate_cell_count"] == 1
    assert not qc.passed
    assert not qc.checks["no_duplicate_cells"]


def test_unknown_mesh_cell_type_cannot_pass_generic_qc() -> None:
    from cardianatomy import MeshInspection

    inspection = MeshInspection(
        point_count=2,
        cell_count=1,
        finite=True,
        metadata={"cell_types": ["line"]},
    )
    qc = qc_from_inspection(inspection)
    assert not qc.passed
    assert not qc.checks["supported_geometry"]
