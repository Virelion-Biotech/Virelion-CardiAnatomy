"""Virelion CardiAnatomy public API."""

from .api import AnatomyAPI
from .coordinates import apply_affine, lps_to_ras_matrix, ras_to_lps_matrix
from .fibers import orthonormal_local_frame, reference_rule_based_microstructure
from .io import inspect_dicom_directory, inspect_mesh_file, inspect_nifti
from .models import (
    AnatomyBundle,
    AnatomyLabel,
    AnatomyRequest,
    ArtifactRef,
    CoordinateFrame,
    DicomSeriesSummary,
    FiberAngleProfile,
    GeometryQC,
    ImagingAcquisition,
    MeshInspection,
    PipelinePlan,
    RegistrationRef,
    ScarThresholdSpec,
    StageRecord,
)
from .pipeline import PipelineExecutor, bundle_fingerprint, stage_fingerprint
from .provenance import canonical_json, file_sha256, sha256
from .qc import (
    inspect_tetra_mesh,
    inspect_triangle_surface,
    qc_from_inspection,
    tetra_signed_volumes,
)
from .scar import classify_scalar_scar, scar_fractions
from .service import CardiAnatomyService, ReadinessError

__all__ = [
    "AnatomyAPI",
    "AnatomyBundle",
    "AnatomyLabel",
    "AnatomyRequest",
    "ArtifactRef",
    "CoordinateFrame",
    "DicomSeriesSummary",
    "FiberAngleProfile",
    "GeometryQC",
    "ImagingAcquisition",
    "MeshInspection",
    "PipelinePlan",
    "RegistrationRef",
    "ScarThresholdSpec",
    "StageRecord",
    "CardiAnatomyService",
    "ReadinessError",
    "PipelineExecutor",
    "stage_fingerprint",
    "bundle_fingerprint",
    "sha256",
    "file_sha256",
    "canonical_json",
    "lps_to_ras_matrix",
    "ras_to_lps_matrix",
    "apply_affine",
    "inspect_tetra_mesh",
    "inspect_triangle_surface",
    "tetra_signed_volumes",
    "qc_from_inspection",
    "inspect_mesh_file",
    "inspect_nifti",
    "inspect_dicom_directory",
    "orthonormal_local_frame",
    "reference_rule_based_microstructure",
    "classify_scalar_scar",
    "scar_fractions",
]

__version__ = "0.2.0"
