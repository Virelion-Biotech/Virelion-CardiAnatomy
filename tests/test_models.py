import pytest

from cardianatomy import (
    AnatomyBundle,
    AnatomyRequest,
    ArtifactRef,
    CoordinateFrame,
    GeometryQC,
    ImagingAcquisition,
    PipelinePlan,
    RegistrationRef,
)


def artifact(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=f"a-{kind}", kind=kind, uri=f"file:///{kind}")


def test_bundle_readiness_profiles() -> None:
    bundle = AnatomyBundle(
        subject_id="S1",
        study_id="ST1",
        acquisition_id="A1",
        artifacts=[
            artifact("segmentation"),
            artifact("surface_mesh"),
            artifact("volume_mesh"),
            artifact("coordinate_field"),
            artifact("fiber_field"),
        ],
        qc=GeometryQC(passed=True, checks={"mesh_nonempty": True}),
    )
    assert bundle.ready
    assert bundle.surface_ready
    assert bundle.ep_ready
    assert bundle.mechanics_ready
    assert bundle.flow_ready


def test_request_rejects_subject_mismatch() -> None:
    acquisition = ImagingAcquisition(
        subject_id="OTHER",
        study_id="ST1",
        acquisition_id="A1",
        modality="CMR",
        source=artifact("dicom_series"),
    )
    with pytest.raises(ValueError):
        AnatomyRequest(subject_id="S1", acquisition=acquisition, backend="x")


def test_request_rejects_backend_and_plan() -> None:
    acquisition = ImagingAcquisition(
        subject_id="S1",
        study_id="ST1",
        acquisition_id="A1",
        modality="CMR",
        source=artifact("dicom_series"),
    )
    with pytest.raises(ValueError):
        AnatomyRequest(
            subject_id="S1",
            acquisition=acquisition,
            backend="x",
            plan=PipelinePlan(stages=["segmentation"], backends={"segmentation": "y"}),
        )


def test_registration_requires_transform() -> None:
    with pytest.raises(ValueError):
        RegistrationRef(
            registration_id="R1",
            source_frame="A",
            target_frame="B",
            method="rigid",
        )


def test_coordinate_frame_requires_4x4_affine() -> None:
    with pytest.raises(ValueError):
        CoordinateFrame(
            frame_id="x",
            convention="MODEL",
            affine_to_parent=[[1, 0], [0, 1]],
        )
