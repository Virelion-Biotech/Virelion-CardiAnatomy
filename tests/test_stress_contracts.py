from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
from pydantic import ValidationError

from cardianatomy import (
    AnatomyBundle,
    AnatomyLabel,
    ArtifactRef,
    CoordinateFrame,
    GeometryQC,
    ImagingAcquisition,
    RegistrationRef,
    StageRecord,
    bundle_fingerprint,
)


def _artifact(artifact_id: str = "a") -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        kind="segmentation",
        uri=f"https://example.invalid/{artifact_id}",
    )


def test_artifact_lineage_cannot_self_reference() -> None:
    with pytest.raises(ValidationError, match="derived from itself"):
        ArtifactRef(
            artifact_id="a",
            kind="segmentation",
            uri="https://example.invalid/a",
            derived_from=["a"],
        )


def test_artifact_lineage_cannot_repeat_parent_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate"):
        ArtifactRef(
            artifact_id="a",
            kind="segmentation",
            uri="https://example.invalid/a",
            derived_from=["raw", "raw"],
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"shape": ()},
        {"voxel_spacing_mm": ()},
        {"shape": (10, 10, 10), "voxel_spacing_mm": (1.0, 1.0)},
        {"phase_count": 3, "selected_phases": {"ED": 3}},
        {"phase_count": 3, "selected_phases": {"ES": -1}},
    ],
)
def test_imaging_acquisition_rejects_inconsistent_geometry(kwargs: dict) -> None:
    with pytest.raises(ValidationError):
        ImagingAcquisition(
            subject_id="S1",
            study_id="ST1",
            acquisition_id="A1",
            modality="CMR",
            source=_artifact("raw").model_copy(update={"kind": "nifti_image"}),
            **kwargs,
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": "", "value": 1, "structure": "lv_cavity"},
        {"name": "LV", "value": -1, "structure": "lv_cavity"},
        {"name": "LV", "value": 1, "structure": ""},
    ],
)
def test_anatomy_labels_reject_invalid_identity(kwargs: dict) -> None:
    with pytest.raises(ValidationError):
        AnatomyLabel(**kwargs)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_qc_metrics_must_be_finite(bad: float) -> None:
    with pytest.raises(ValidationError, match="must be finite"):
        GeometryQC(
            passed=False,
            metrics={"bad": bad},
        )


def test_stage_record_ok_cannot_contain_errors() -> None:
    with pytest.raises(ValidationError):
        StageRecord(
            stage="qc",
            backend="native",
            status="ok",
            fingerprint="f",
            errors=["should-not-be-here"],
        )


def test_stage_record_error_requires_error_message() -> None:
    with pytest.raises(ValidationError):
        StageRecord(
            stage="qc",
            backend="native",
            status="error",
            fingerprint="f",
        )


def test_stage_record_rejects_backward_timestamps() -> None:
    start = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        StageRecord(
            stage="qc",
            backend="native",
            status="ok",
            fingerprint="f",
            started_at=start,
            finished_at=start - timedelta(seconds=1),
        )


def test_stage_record_rejects_nonfinite_duration() -> None:
    with pytest.raises(ValidationError):
        StageRecord(
            stage="qc",
            backend="native",
            status="ok",
            fingerprint="f",
            duration_seconds=np.inf,
        )


def test_bundle_rejects_duplicate_artifact_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate artifact"):
        AnatomyBundle(
            subject_id="S1",
            study_id="ST1",
            acquisition_id="A1",
            artifacts=[_artifact("a"), _artifact("a")],
        )


def test_bundle_rejects_duplicate_frame_ids() -> None:
    frame = CoordinateFrame(frame_id="model", convention="MODEL")
    with pytest.raises(ValidationError, match="duplicate frame"):
        AnatomyBundle(
            subject_id="S1",
            study_id="ST1",
            acquisition_id="A1",
            frames=[frame, frame.model_copy()],
        )


def test_bundle_rejects_duplicate_registration_ids() -> None:
    registration = RegistrationRef(
        registration_id="r1",
        source_frame="a",
        target_frame="b",
        matrix=np.eye(4).tolist(),
        method="rigid",
    )
    with pytest.raises(ValidationError, match="duplicate registration"):
        AnatomyBundle(
            subject_id="S1",
            study_id="ST1",
            acquisition_id="A1",
            registrations=[registration, registration.model_copy()],
        )


def test_bundle_rejects_duplicate_label_values() -> None:
    with pytest.raises(ValidationError, match="duplicate anatomical label"):
        AnatomyBundle(
            subject_id="S1",
            study_id="ST1",
            acquisition_id="A1",
            labels=[
                AnatomyLabel(name="LV", value=1, structure="lv_cavity"),
                AnatomyLabel(name="RV", value=1, structure="rv_cavity"),
            ],
        )


def test_bundle_fingerprint_round_trip_and_tamper_detection() -> None:
    bundle = AnatomyBundle(
        subject_id="S1",
        study_id="ST1",
        acquisition_id="A1",
        artifacts=[_artifact("a")],
        provenance={"source": "stress"},
    )
    payload = bundle.model_dump(mode="json")
    payload["bundle_fingerprint"] = bundle_fingerprint(bundle)

    restored = AnatomyBundle.model_validate(payload)
    assert restored.bundle_fingerprint == payload["bundle_fingerprint"]

    payload["provenance"]["source"] = "tampered"
    with pytest.raises(ValidationError, match="fingerprint"):
        AnatomyBundle.model_validate(payload)
