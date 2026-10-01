import math

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st
from pydantic import ValidationError

from cardianatomy import (
    AnatomyRequest,
    ArtifactRef,
    CoordinateFrame,
    FiberAngleProfile,
    ImagingAcquisition,
    RegistrationRef,
    ScarThresholdSpec,
    affine_round_trip_error,
    apply_affine,
    compare_corresponding_meshes,
    cyclic_closure_error,
    estimate_rigid_transform,
    inspect_tetra_mesh,
    label_counts,
    label_volumes_ml,
    mesh_scale_metrics,
    point_set_distance_summary,
    segmentation_overlap_metrics,
    tetra_mean_ratio_quality,
    tetra_scaled_jacobian_quality,
    validate_affine,
)


REGULAR_TETRA = np.array(
    [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.5, np.sqrt(3.0) / 2.0, 0.0],
        [0.5, np.sqrt(3.0) / 6.0, np.sqrt(2.0 / 3.0)],
    ]
)
TETRA = np.array([[0, 1, 2, 3]])


@pytest.mark.parametrize("scale", [1e-12, 1e-9, 1e-3, 1.0, 1e3, 1e9, 1e12])
def test_tetra_quality_is_scale_invariant(scale: float) -> None:
    points = REGULAR_TETRA * scale
    mean_ratio = tetra_mean_ratio_quality(points, TETRA)
    scaled_jacobian = tetra_scaled_jacobian_quality(points, TETRA)
    inspection = inspect_tetra_mesh(points, TETRA)

    assert np.isclose(mean_ratio[0], 1.0, atol=1e-12)
    assert np.isclose(scaled_jacobian[0], 1.0, atol=1e-12)
    assert inspection.degenerate_fraction == 0.0
    assert inspection.finite


@settings(max_examples=40, deadline=None)
@given(
    angle=st.floats(
        min_value=-math.pi,
        max_value=math.pi,
        allow_nan=False,
        allow_infinity=False,
    ),
    tx=st.floats(-1e6, 1e6, allow_nan=False, allow_infinity=False),
    ty=st.floats(-1e6, 1e6, allow_nan=False, allow_infinity=False),
    tz=st.floats(-1e6, 1e6, allow_nan=False, allow_infinity=False),
)
def test_rigid_registration_recovers_random_planar_transform(
    angle: float,
    tx: float,
    ty: float,
    tz: float,
) -> None:
    source = np.array(
        [
            [0.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [0.0, 3.0, 0.0],
            [1.0, 1.0, 0.0],
        ]
    )
    cosine = math.cos(angle)
    sine = math.sin(angle)
    rotation = np.array(
        [
            [cosine, -sine, 0.0],
            [sine, cosine, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    translation = np.array([tx, ty, tz])
    target = source @ rotation.T + translation

    result = estimate_rigid_transform(source, target)
    assert result.rms_error < 1e-7
    assert result.max_error < 1e-6
    assert np.allclose(result.matrix[:3, :3], rotation, atol=1e-7)
    assert np.allclose(result.matrix[:3, 3], translation, atol=1e-7)


@pytest.mark.parametrize("scale", [1e-14, 1e-10, 1e-6, 1.0, 1e6, 1e10])
def test_uniform_affine_scaling_is_not_misclassified_as_singular(scale: float) -> None:
    matrix = np.eye(4)
    matrix[:3, :3] *= scale
    validated = validate_affine(matrix)
    assert np.allclose(validated, matrix)


def test_nearly_singular_affine_is_rejected() -> None:
    matrix = np.eye(4)
    matrix[2, 2] = 1e-18
    with pytest.raises(ValueError, match="singular|unstable"):
        validate_affine(matrix)


@settings(max_examples=40, deadline=None)
@given(
    tx=st.floats(-1e5, 1e5, allow_nan=False, allow_infinity=False),
    ty=st.floats(-1e5, 1e5, allow_nan=False, allow_infinity=False),
    tz=st.floats(-1e5, 1e5, allow_nan=False, allow_infinity=False),
)
def test_affine_round_trip_random_translation(tx: float, ty: float, tz: float) -> None:
    matrix = np.eye(4)
    matrix[:3, 3] = [tx, ty, tz]
    points = np.array(
        [[0.0, 0.0, 0.0], [1.25, -3.5, 9.0], [-4.0, 2.0, 0.5]]
    )
    error = affine_round_trip_error(points, matrix)
    assert error < 1e-8


def test_affine_overflow_fails_loudly() -> None:
    matrix = np.eye(4)
    matrix[0, 0] = 2.0
    with pytest.raises(OverflowError):
        apply_affine(np.array([[1e308, 0.0, 0.0]]), matrix)


def test_collinear_registration_is_rejected() -> None:
    source = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
    target = source + 1.0
    with pytest.raises(ValueError, match="non-collinear"):
        estimate_rigid_transform(source, target)


@pytest.mark.parametrize(
    "spacing",
    [
        (0.0, 1.0, 1.0),
        (-1.0, 1.0, 1.0),
        (np.nan, 1.0, 1.0),
        (np.inf, 1.0, 1.0),
    ],
)
def test_invalid_voxel_spacing_is_rejected(spacing: tuple[float, float, float]) -> None:
    with pytest.raises(ValueError):
        label_volumes_ml(np.ones((2, 2, 2), dtype=np.uint8), spacing)


@pytest.mark.parametrize(
    "labels",
    [
        np.array([0.0, np.nan]),
        np.array([0.0, np.inf]),
        np.array([0.0, 1.5]),
        np.array(["0", "1"], dtype=object),
    ],
)
def test_invalid_segmentation_labels_are_rejected(labels: np.ndarray) -> None:
    with pytest.raises(ValueError):
        label_counts(labels)


def test_out_of_int64_segmentation_labels_are_rejected() -> None:
    huge = np.array([float(2**64)])
    with pytest.raises(ValueError, match="int64"):
        label_counts(huge)
    with pytest.raises(ValueError, match="int64"):
        segmentation_overlap_metrics(huge, huge)


def test_point_set_distance_overflow_is_rejected() -> None:
    reference = np.array([[1e308, 0.0, 0.0]])
    prediction = np.array([[-1e308, 0.0, 0.0]])
    with pytest.raises(OverflowError):
        point_set_distance_summary(reference, prediction)


def test_point_distance_rms_is_stable_for_large_finite_distances() -> None:
    reference = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
    prediction = np.array([[1e200, 0.0, 0.0], [1e200, 0.0, 0.0]])
    result = point_set_distance_summary(reference, prediction)
    assert np.isfinite(result.symmetric_rms)
    assert result.symmetric_rms == pytest.approx(1e200)


@pytest.mark.parametrize(
    "cells",
    [
        np.array([[0.0, 1.5, 2.0]]),
        np.array([[0, 1, 3]]),
        np.array([[-1, 1, 2]]),
    ],
)
def test_correspondence_rejects_invalid_connectivity(cells: np.ndarray) -> None:
    points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    with pytest.raises(ValueError):
        compare_corresponding_meshes(
            points,
            points.copy(),
            reference_cells=cells,
            target_cells=cells,
        )


def test_empty_or_nonfinite_cyclic_motion_is_rejected() -> None:
    with pytest.raises(ValueError):
        cyclic_closure_error(np.empty((2, 0, 3)))
    frames = np.zeros((2, 1, 3))
    frames[1, 0, 0] = np.nan
    with pytest.raises(ValueError):
        cyclic_closure_error(frames)


def test_mesh_scale_metrics_rejects_bad_indices() -> None:
    points = np.array([[0.0, 0.0, 0.0]])
    with pytest.raises(ValueError):
        mesh_scale_metrics(points, np.array([[0, 1, 0]]))


@pytest.mark.parametrize("unsafe_id", ["../escape", "a/b", r"a\b", ".", "..", ""])
def test_request_identifiers_cannot_escape_work_directory(unsafe_id: str) -> None:
    with pytest.raises(ValidationError):
        ImagingAcquisition(
            subject_id=unsafe_id,
            study_id="ST1",
            acquisition_id="A1",
            modality="CMR",
            source=ArtifactRef(
                artifact_id="raw",
                kind="nifti_image",
                uri="file:///tmp/raw.nii.gz",
            ),
        )


def test_imaging_metadata_rejects_invalid_geometry() -> None:
    with pytest.raises(ValidationError):
        ImagingAcquisition(
            subject_id="S1",
            study_id="ST1",
            acquisition_id="A1",
            modality="CMR",
            source=ArtifactRef(
                artifact_id="raw",
                kind="nifti_image",
                uri="file:///tmp/raw.nii.gz",
            ),
            shape=(256, 0, 20),
        )
    with pytest.raises(ValidationError):
        ImagingAcquisition(
            subject_id="S1",
            study_id="ST1",
            acquisition_id="A1",
            modality="CMR",
            source=ArtifactRef(
                artifact_id="raw",
                kind="nifti_image",
                uri="file:///tmp/raw.nii.gz",
            ),
            voxel_spacing_mm=(1.0, -1.0, 8.0),
        )


def test_contracts_reject_nonfinite_scientific_parameters() -> None:
    with pytest.raises(ValidationError):
        ScarThresholdSpec(border_threshold=np.nan, core_threshold=2.0)
    with pytest.raises(ValidationError):
        FiberAngleProfile(alpha_endo_deg=np.inf)


def test_coordinate_and_registration_affines_are_validated() -> None:
    singular = np.eye(4)
    singular[2, 2] = 0.0
    with pytest.raises(ValidationError):
        CoordinateFrame(
            frame_id="bad",
            convention="MODEL",
            affine_to_parent=singular.tolist(),
        )
    with pytest.raises(ValidationError):
        RegistrationRef(
            registration_id="bad",
            source_frame="a",
            target_frame="b",
            matrix=singular.tolist(),
            method="test",
        )


def test_anatomy_request_rejects_unsafe_subject_even_if_acquisition_matches() -> None:
    with pytest.raises(ValidationError):
        AnatomyRequest(
            subject_id="../S1",
            acquisition=ImagingAcquisition(
                subject_id="../S1",
                study_id="ST1",
                acquisition_id="A1",
                modality="CMR",
                source=ArtifactRef(
                    artifact_id="raw",
                    kind="nifti_image",
                    uri="file:///tmp/raw.nii.gz",
                ),
            ),
        )
