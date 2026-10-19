from __future__ import annotations

import pytest

from cardianatomy.models import AnatomyBundle, ArtifactRef, CoordinateFrame, GeometryQC
from cardianatomy.patient_readiness import patient_ep_readiness_issues, patient_ep_ready
from cardianatomy.service import CardiAnatomyService, ReadinessError


SHA = "a" * 64
IDENTITY = {
    "subject_id": "P1",
    "study_id": "S1",
    "acquisition_id": "A1",
}
IDENTITY_AFFINE = [
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
]


def _artifact(
    artifact_id: str,
    kind: str,
    *,
    frame_id: str,
    metadata: dict | None = None,
    **identity_overrides,
) -> ArtifactRef:
    identity = {**IDENTITY, **identity_overrides}
    return ArtifactRef(
        artifact_id=artifact_id,
        kind=kind,
        uri=f"file:///{artifact_id}",
        sha256=SHA,
        frame_id=frame_id,
        metadata=metadata or {},
        **identity,
    )


def _bundle(*, review: bool = True, connected: bool = True) -> AnatomyBundle:
    segmentation_metadata = {}
    if review:
        segmentation_metadata = {
            "review_status": "expert_corrected",
            "reviewer_role": "cardiac_imaging_specialist",
        }
    frames = [
        CoordinateFrame(frame_id="image", convention="DICOM_LPS", units="mm"),
        CoordinateFrame(
            frame_id="model",
            convention="MODEL",
            units="mm",
            parent_frame_id="image" if connected else None,
            affine_to_parent=IDENTITY_AFFINE if connected else None,
        ),
    ]
    artifacts = [
        _artifact(
            "segmentation",
            "segmentation",
            frame_id="image",
            metadata=segmentation_metadata,
        ),
        _artifact("surface", "surface_mesh", frame_id="model"),
        _artifact("volume", "volume_mesh", frame_id="model"),
        _artifact("uvc", "coordinate_field", frame_id="model"),
        _artifact("fibres", "fiber_field", frame_id="model"),
    ]
    return AnatomyBundle(
        **IDENTITY,
        artifacts=artifacts,
        frames=frames,
        qc=GeometryQC(
            passed=True,
            checks={"finite": True, "nondegenerate": True},
            artifact_id="volume",
        ),
    )


def test_patient_ep_ready_requires_more_than_generic_ep_ready() -> None:
    bundle = _bundle(review=False)
    assert bundle.ep_ready is True
    assert patient_ep_ready(bundle) is False
    issues = patient_ep_readiness_issues(bundle)
    assert any("review_status" in issue for issue in issues)
    assert any("reviewer_role" in issue for issue in issues)


def test_reviewed_traceable_patient_bundle_passes() -> None:
    bundle = _bundle()
    assert patient_ep_readiness_issues(bundle) == []
    assert patient_ep_ready(bundle) is True
    assert CardiAnatomyService.require_ready(bundle, target="patient_ep") == bundle


def test_patient_ep_requires_traceable_image_to_model_frame_path() -> None:
    bundle = _bundle(connected=False)
    issues = patient_ep_readiness_issues(bundle)
    assert any("no traceable coordinate-frame path" in issue for issue in issues)
    with pytest.raises(ReadinessError, match="traceable coordinate-frame path"):
        CardiAnatomyService.require_ready(bundle, target="patient_ep")


def test_patient_ep_rejects_ambiguous_volume_mesh_selection() -> None:
    bundle = _bundle()
    bundle.artifacts.append(_artifact("volume-2", "volume_mesh", frame_id="model"))
    issues = patient_ep_readiness_issues(bundle)
    assert any("multiple volume_mesh artifacts exist" in issue for issue in issues)


def test_explicit_patient_model_selection_resolves_multiple_candidates() -> None:
    bundle = _bundle()
    bundle.artifacts.append(_artifact("volume-2", "volume_mesh", frame_id="model"))
    original = next(item for item in bundle.artifacts if item.artifact_id == "volume")
    original.metadata["selected_for_patient_model"] = True
    assert patient_ep_readiness_issues(bundle) == []


def test_patient_ep_rejects_missing_or_wrong_artifact_identity() -> None:
    bundle = _bundle()
    segmentation = next(item for item in bundle.artifacts if item.kind == "segmentation")
    segmentation.subject_id = "OTHER"
    issues = patient_ep_readiness_issues(bundle)
    assert any("does not match bundle subject_id" in issue for issue in issues)


def test_patient_ep_rejects_undeclared_artifact_frame() -> None:
    bundle = _bundle()
    fibres = next(item for item in bundle.artifacts if item.kind == "fiber_field")
    fibres.frame_id = "missing-frame"
    issues = patient_ep_readiness_issues(bundle)
    assert any("undeclared frame" in issue for issue in issues)


def test_patient_ep_requires_qc_on_selected_volume_mesh() -> None:
    bundle = _bundle()
    bundle.qc = GeometryQC(
        passed=True,
        checks={"finite": True},
        artifact_id="surface",
    )
    issues = patient_ep_readiness_issues(bundle)
    assert any("generic EP readiness" in issue for issue in issues)
    assert any("QC does not cover the selected" in issue for issue in issues)
