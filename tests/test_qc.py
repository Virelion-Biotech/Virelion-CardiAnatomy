import numpy as np

from cardianatomy import inspect_tetra_mesh, inspect_triangle_surface, qc_from_inspection


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
