"""Virelion CardiAnatomy public API."""

from .api import AnatomyAPI
from .coordinates import apply_affine, lps_to_ras_matrix, ras_to_lps_matrix
from .fibers import orthonormal_local_frame, reference_rule_based_microstructure
from .geometry import (
    bounding_box,
    closed_surface_signed_volume,
    mesh_scale_metrics,
    tetrahedral_volume,
    triangle_surface_area,
)
from .integrations import (
    biv_me_command,
    biv_volumetric_command,
    geox_command,
    ldrb_command,
    meshtool_command,
    myomesh_command,
    nnunet_predict_command,
    require_tool_policy,
    tool_catalog,
)
from .io import inspect_dicom_directory, inspect_mesh_file, inspect_nifti
from .labels import canonical_structures, normalize_structure_name, validate_label_mapping
from .manifests import (
    ExternalAsset,
    ToolchainEntry,
    ToolchainManifest,
    audit_manifest_licenses,
)
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
from .presets import (
    cine_cmr_biventricular_plan,
    mesh_qc_only_plan,
    presegmented_ep_plan,
    preset_catalog,
)
from .provenance import canonical_json, file_sha256, sha256
from .registration import (
    RigidRegistrationResult,
    estimate_rigid_transform,
    registration_residuals,
)
from .qc import (
    inspect_tetra_mesh,
    inspect_triangle_surface,
    qc_from_inspection,
    tetra_signed_volumes,
)
from .scar import classify_scalar_scar, scar_fractions
from .segmentation import label_counts, label_volumes_ml, segmentation_qc
from .series import SeriesCandidate, classify_cine_series, rank_series_for_cine
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
    "bounding_box",
    "triangle_surface_area",
    "tetrahedral_volume",
    "closed_surface_signed_volume",
    "mesh_scale_metrics",
    "RigidRegistrationResult",
    "estimate_rigid_transform",
    "registration_residuals",
    "tool_catalog",
    "require_tool_policy",
    "nnunet_predict_command",
    "biv_me_command",
    "biv_volumetric_command",
    "myomesh_command",
    "meshtool_command",
    "ldrb_command",
    "geox_command",
    "ExternalAsset",
    "ToolchainEntry",
    "ToolchainManifest",
    "audit_manifest_licenses",
    "cine_cmr_biventricular_plan",
    "presegmented_ep_plan",
    "mesh_qc_only_plan",
    "preset_catalog",
    "canonical_structures",
    "normalize_structure_name",
    "validate_label_mapping",
    "SeriesCandidate",
    "classify_cine_series",
    "rank_series_for_cine",
    "label_counts",
    "label_volumes_ml",
    "segmentation_qc",
]

__version__ = "0.3.0"
