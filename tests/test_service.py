import pytest

from cardianatomy import (
    AnatomyBundle,
    AnatomyRequest,
    ArtifactRef,
    CardiAnatomyService,
    GeometryQC,
    ImagingAcquisition,
    ReadinessError,
)
from cardianatomy.backends import BackendUnavailable


def request() -> AnatomyRequest:
    return AnatomyRequest(
        subject_id="S1",
        acquisition=ImagingAcquisition(
            subject_id="S1",
            study_id="ST1",
            acquisition_id="A1",
            modality="CMR",
            source=ArtifactRef(artifact_id="raw", kind="dicom_series", uri="file:///raw"),
        ),
    )


def test_service_fails_closed_without_backend() -> None:
    with pytest.raises(BackendUnavailable):
        CardiAnatomyService().build(request())


def test_require_ready_is_target_specific() -> None:
    bundle = AnatomyBundle(
        subject_id="S1",
        study_id="ST1",
        acquisition_id="A1",
        artifacts=[ArtifactRef(artifact_id="surf", kind="surface_mesh", uri="file:///surf")],
        qc=GeometryQC(passed=True),
    )
    CardiAnatomyService.require_ready(bundle, "flow")
    with pytest.raises(ReadinessError):
        CardiAnatomyService.require_ready(bundle, "mechanics")
