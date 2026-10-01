import numpy as np
import pytest

from cardianatomy import (
    AnatomyBundle,
    AnatomyRequest,
    ArtifactRef,
    CardiAnatomyService,
    FiberAngleProfile,
    ImagingAcquisition,
    ReadinessError,
    ScarThresholdSpec,
    classify_scalar_scar,
    orthonormal_local_frame,
    reference_rule_based_microstructure,
    scar_fractions,
)


def test_huge_finite_local_frame_vectors_remain_normalizable() -> None:
    circumferential = np.array(
        [[1e300, 0.0, 0.0], [0.0, 1e300, 0.0]]
    )
    longitudinal = np.array(
        [[0.0, 1e300, 0.0], [0.0, 0.0, 1e300]]
    )
    c, l_axis, t = orthonormal_local_frame(circumferential, longitudinal)

    assert np.all(np.isfinite(c))
    assert np.all(np.isfinite(l_axis))
    assert np.all(np.isfinite(t))
    assert np.allclose(np.linalg.norm(c, axis=1), 1.0)
    assert np.allclose(np.linalg.norm(l_axis, axis=1), 1.0)
    assert np.allclose(np.linalg.norm(t, axis=1), 1.0)
    assert np.allclose(np.sum(c * l_axis, axis=1), 0.0, atol=1e-12)


def test_parallel_local_frame_vectors_are_rejected() -> None:
    vectors = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    with pytest.raises(ValueError):
        orthonormal_local_frame(vectors, vectors)


def test_reference_microstructure_remains_orthonormal_at_extreme_angles() -> None:
    circumferential = np.array(
        [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
    )
    longitudinal = np.array(
        [[0.0, 1.0, 0.0], [0.0, 1.0, 0.0]]
    )
    profile = FiberAngleProfile(
        alpha_endo_deg=720.0,
        alpha_epi_deg=-720.0,
        beta_endo_deg=360.0,
        beta_epi_deg=-360.0,
    )
    fiber, sheet, normal = reference_rule_based_microstructure(
        circumferential,
        longitudinal,
        np.array([0.0, 1.0]),
        profile,
    )
    assert np.allclose(np.linalg.norm(fiber, axis=1), 1.0)
    assert np.allclose(np.linalg.norm(sheet, axis=1), 1.0)
    assert np.allclose(np.linalg.norm(normal, axis=1), 1.0)
    assert np.allclose(np.sum(fiber * sheet, axis=1), 0.0, atol=1e-12)


def test_empty_scar_fraction_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least one"):
        scar_fractions(np.array([], dtype=np.uint8))


def test_scar_classification_extreme_finite_values() -> None:
    values = np.array([-1e300, -1.0, 0.0, 1.0, 1e300])
    labels = classify_scalar_scar(
        values,
        ScarThresholdSpec(border_threshold=0.0, core_threshold=1.0),
    )
    assert labels.tolist() == [0, 0, 1, 2, 2]
    fractions = scar_fractions(labels)
    assert sum(fractions.values()) == pytest.approx(1.0)


class WrongIdentityBackend:
    name = "wrong-identity"

    def available(self) -> bool:
        return True

    def build(self, request: AnatomyRequest) -> AnatomyBundle:
        return AnatomyBundle(
            subject_id=request.subject_id,
            study_id="WRONG-STUDY",
            acquisition_id=request.acquisition.acquisition_id,
            artifacts=[request.acquisition.source],
        )


def test_service_rejects_wrong_study_from_monolithic_backend() -> None:
    request = AnatomyRequest(
        subject_id="S1",
        acquisition=ImagingAcquisition(
            subject_id="S1",
            study_id="ST1",
            acquisition_id="A1",
            modality="CMR",
            source=ArtifactRef(
                artifact_id="raw",
                kind="nifti_image",
                uri="https://example.invalid/raw.nii.gz",
            ),
        ),
        backend="wrong-identity",
    )
    service = CardiAnatomyService()
    service.register_backend(WrongIdentityBackend())
    with pytest.raises(ReadinessError, match="study_id"):
        service.build(request)


def test_readiness_never_ignores_failed_qc() -> None:
    bundle = AnatomyBundle(
        subject_id="S1",
        study_id="ST1",
        acquisition_id="A1",
        artifacts=[
            ArtifactRef(
                artifact_id="seg",
                kind="segmentation",
                uri="https://example.invalid/seg",
            ),
            ArtifactRef(
                artifact_id="surface",
                kind="surface_mesh",
                uri="https://example.invalid/surface",
            ),
            ArtifactRef(
                artifact_id="volume",
                kind="volume_mesh",
                uri="https://example.invalid/volume",
            ),
        ],
        qc={
            "passed": False,
            "checks": {"geometry": False},
            "errors": ["geometry"],
        },
    )
    assert not bundle.ready
    assert not bundle.mechanics_ready
    with pytest.raises(ReadinessError):
        CardiAnatomyService.require_ready(bundle, target="baseline")
