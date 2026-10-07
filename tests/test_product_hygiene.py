import meshio
import numpy as np
import pytest

from cardianatomy import ArtifactRef, AnatomyBundle, GeometryQC, CardiAnatomyService
from cardianatomy.io import inspect_mesh_file
from cardianatomy.qc import qc_from_inspection
from test_stress_pipeline import CountingSegmentationBackend, _request, _plan
from cardianatomy.pipeline import PipelineExecutor


def test_changed_unhashed_source_invalidates_resume(tmp_path):
    source = tmp_path / "raw.nii"
    source.write_bytes(b"first")
    request = _request(tmp_path)
    request.acquisition.source.uri = str(source)
    executor = PipelineExecutor()
    backend = CountingSegmentationBackend()
    executor.register(backend)
    executor.execute(request, _plan())
    source.write_bytes(b"other")
    executor.execute(request, _plan())
    assert backend.calls == 2


def test_high_order_mesh_not_silently_linearized(tmp_path):
    path = tmp_path / "curved.vtu"
    meshio.write_points_cells(
        path,
        np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0.5, 0, 0], [0.5, 0.5, 0], [0, 0.5, 0]]),
        [("triangle6", np.array([[0, 1, 2, 3, 4, 5]]))],
    )
    with pytest.raises(ValueError, match="Higher-order"):
        inspect_mesh_file(path)


def test_ready_revalidates_mutated_qc():
    bundle = AnatomyBundle(
        subject_id="S",
        study_id="ST",
        acquisition_id="A",
        artifacts=[ArtifactRef(artifact_id="v", kind="volume_mesh", uri="memory://v")],
        qc=GeometryQC(passed=True, checks={"finite": True}),
    )
    bundle.qc.checks["finite"] = False
    with pytest.raises(ValueError):
        CardiAnatomyService.require_ready(bundle, "mechanics")


def test_volume_qc_does_not_approve_unchecked_surface():
    bundle = AnatomyBundle(
        subject_id="S",
        study_id="ST",
        acquisition_id="A",
        artifacts=[
            ArtifactRef(artifact_id="v", kind="volume_mesh", uri="memory://v"),
            ArtifactRef(artifact_id="s", kind="surface_mesh", uri="memory://s"),
        ],
        qc=GeometryQC(passed=True, artifact_id="v"),
    )
    assert not bundle.flow_ready


def test_quality_threshold_cannot_pass_without_measurement():
    from cardianatomy.models import MeshInspection

    inspection = MeshInspection(point_count=4, cell_count=1, tetra_count=1)
    assert not qc_from_inspection(inspection, minimum_shape_quality=0.5).passed


def test_kdtree_matches_bounded_reference_and_scales():
    pytest.importorskip("scipy")
    from cardianatomy.validation import nearest_point_distances, point_set_distance_summary

    rng = np.random.default_rng(7)
    a, b = rng.normal(size=(101, 3)), rng.normal(size=(83, 3))
    brute = nearest_point_distances(a, b)
    tree = nearest_point_distances(a, b, backend="scipy_kdtree")
    assert np.allclose(brute, tree, atol=1e-14, rtol=1e-14)
    large = rng.normal(size=(10000, 3))
    assert point_set_distance_summary(large, large, backend="scipy_kdtree").hausdorff == 0


def test_closed_surface_rejects_open_or_inconsistently_oriented_geometry():
    from cardianatomy.geometry import closed_surface_signed_volume

    points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    triangles = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
    assert np.isclose(closed_surface_signed_volume(points, triangles), 1 / 6)
    with pytest.raises(ValueError, match="closed"):
        closed_surface_signed_volume(points, triangles[:3])
    triangles[0] = triangles[0, ::-1]
    with pytest.raises(ValueError, match="oriented"):
        closed_surface_signed_volume(points, triangles)


def test_int64_boundary_float_label_is_rejected():
    from cardianatomy.segmentation import label_counts
    from cardianatomy.validation import segmentation_overlap_metrics

    boundary = np.array([float(2**63)])
    with pytest.raises(ValueError, match="int64"):
        label_counts(boundary)
    with pytest.raises(ValueError, match="int64"):
        segmentation_overlap_metrics(boundary, boundary)


def test_affine_normalization_cannot_return_infinity():
    from cardianatomy.coordinates import apply_affine

    matrix = np.eye(4)
    matrix[3, 3] = 1e-7
    with pytest.raises(OverflowError, match="normalization"):
        apply_affine(np.array([[1e308, 0.0, 0.0]]), matrix)


def test_non_object_sidecar_is_treated_as_cache_miss(tmp_path):
    executor = PipelineExecutor()
    backend = CountingSegmentationBackend()
    executor.register(backend)
    request, plan = _request(tmp_path), _plan()
    executor.execute(request, plan)
    (tmp_path / "S1/A1/stage-segmentation.json").write_text("[]")
    executor.execute(request, plan)
    assert backend.calls == 2


@pytest.mark.parametrize("identifier", ["CON", "AUX.txt", "LPT1", "S:", "S.", "S ", "S?"])
def test_request_identifiers_are_portable(tmp_path, identifier):
    from cardianatomy import AnatomyRequest

    payload = _request(tmp_path).model_dump()
    payload["subject_id"] = identifier
    payload["acquisition"]["subject_id"] = identifier
    with pytest.raises(ValueError, match="portable"):
        AnatomyRequest.model_validate(payload)
