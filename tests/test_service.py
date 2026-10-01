import pytest

from cardianatomy import AnatomyBundle, CardiAnatomyService, GeometryQC, ReadinessError
from cardianatomy.backends import BackendUnavailable
from cardianatomy.models import AnatomyRequest, ArtifactRef, ImagingAcquisition


def request() -> AnatomyRequest:
    return AnatomyRequest(
        subject_id="S1",
        acquisition=ImagingAcquisition(
            subject_id="S1",
            study_id="ST1",
            acquisition_id="A1",
            modality="CMR",
            source=ArtifactRef(
                artifact_id="raw",
                kind="dicom_series",
                uri="file:///raw",
            ),
        ),
    )


def test_service_fails_closed_without_backend() -> None:
    with pytest.raises(BackendUnavailable):
        CardiAnatomyService().build(request())


def test_require_ready_fails_closed() -> None:
    bundle = AnatomyBundle(
        subject_id="S1",
        study_id="ST1",
        acquisition_id="A1",
        qc=GeometryQC(passed=True),
    )
    with pytest.raises(ReadinessError):
        CardiAnatomyService.require_ready(bundle)
