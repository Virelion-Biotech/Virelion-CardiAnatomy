from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ArtifactKind = Literal[
    "dicom_series",
    "nifti_image",
    "segmentation",
    "contour_set",
    "guidepoint_set",
    "landmark_set",
    "surface_mesh",
    "volume_mesh",
    "chamber_tags",
    "valve_tags",
    "coordinate_field",
    "fiber_field",
    "sheet_field",
    "scar_map",
    "motion_field",
    "registration",
    "qc_report",
    "model_fit",
    "report",
    "other",
]

StageName = Literal[
    "ingest",
    "view_selection",
    "phase_harmonization",
    "segmentation",
    "contours",
    "surface_fit",
    "surface_mesh",
    "volume_mesh",
    "coordinates",
    "microstructure",
    "scar",
    "registration",
    "qc",
    "export",
]

StageStatus = Literal["pending", "running", "ok", "skipped", "error"]


class ArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    kind: ArtifactKind
    uri: str
    sha256: str | None = Field(default=None, min_length=64, max_length=64)
    media_type: str | None = None
    producer: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    frame_id: str | None = None
    subject_id: str | None = None
    study_id: str | None = None
    acquisition_id: str | None = None
    derived_from: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImagingAcquisition(BaseModel):
    """Geometry-relevant acquisition metadata only; PHI is intentionally excluded."""

    model_config = ConfigDict(extra="forbid")

    subject_id: str
    study_id: str
    acquisition_id: str
    modality: Literal["CMR", "CT", "ECHO", "EAM", "OTHER"]
    acquired_at: datetime | None = None
    protocol: str | None = None
    coordinate_system: str | None = None
    source: ArtifactRef
    shape: tuple[int, ...] | None = None
    voxel_spacing_mm: tuple[float, ...] | None = None
    phase_count: int | None = Field(default=None, ge=1)
    selected_phases: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DicomSeriesSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    series_uid_sha256: str
    modality: str | None = None
    description: str | None = None
    file_count: int = Field(ge=1)
    rows: int | None = Field(default=None, ge=1)
    columns: int | None = Field(default=None, ge=1)
    pixel_spacing_mm: tuple[float, float] | None = None
    slice_thickness_mm: float | None = Field(default=None, gt=0)
    temporal_positions: int | None = Field(default=None, ge=1)
    image_orientation_patient: tuple[float, ...] | None = None
    warnings: list[str] = Field(default_factory=list)


class CoordinateFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")

    frame_id: str
    convention: Literal["DICOM_LPS", "NIFTI_RAS", "MODEL", "UVC", "UAC", "OTHER"]
    units: str = "mm"
    description: str | None = None
    affine_to_parent: list[list[float]] | None = None
    parent_frame_id: str | None = None

    @model_validator(mode="after")
    def validate_affine(self) -> "CoordinateFrame":
        if self.affine_to_parent is not None:
            if len(self.affine_to_parent) != 4 or any(
                len(row) != 4 for row in self.affine_to_parent
            ):
                raise ValueError("affine_to_parent must be a 4x4 matrix")
        return self


class RegistrationRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    registration_id: str
    source_frame: str
    target_frame: str
    transform: ArtifactRef | None = None
    matrix: list[list[float]] | None = None
    method: str
    quality_metric: float | None = None
    quality_metric_name: str | None = None
    uncertainty: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_transform(self) -> "RegistrationRef":
        if self.transform is None and self.matrix is None:
            raise ValueError("registration requires a transform artifact or inline matrix")
        if self.matrix is not None:
            if len(self.matrix) != 4 or any(len(row) != 4 for row in self.matrix):
                raise ValueError("registration matrix must be 4x4")
        return self


class AnatomyLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    value: int
    structure: str
    ontology_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GeometryQC(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool
    checks: dict[str, bool] = Field(default_factory=dict)
    metrics: dict[str, float | int | bool | str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    artifact_id: str | None = None

    @model_validator(mode="after")
    def consistent_status(self) -> "GeometryQC":
        if self.passed and (self.errors or any(not value for value in self.checks.values())):
            raise ValueError("passed=True is inconsistent with failed checks or errors")
        return self


class StageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: StageName
    backend: str
    status: StageStatus
    fingerprint: str
    input_artifact_ids: list[str] = Field(default_factory=list)
    output_artifact_ids: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class PipelinePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stages: list[StageName]
    backends: dict[str, str] = Field(default_factory=dict)
    stage_parameters: dict[str, dict[str, Any]] = Field(default_factory=dict)
    resume: bool = True

    @model_validator(mode="after")
    def unique_stages(self) -> "PipelinePlan":
        if not self.stages:
            raise ValueError("Pipeline plan requires at least one stage")
        if len(self.stages) != len(set(self.stages)):
            raise ValueError("Pipeline stages must be unique")
        return self


class AnatomyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: str
    acquisition: ImagingAcquisition
    requested_outputs: list[ArtifactKind] = Field(
        default_factory=lambda: ["segmentation", "surface_mesh", "volume_mesh"]
    )
    backend: str | None = None
    plan: PipelinePlan | None = None
    output_root: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def consistent_subject(self) -> "AnatomyRequest":
        if self.acquisition.subject_id != self.subject_id:
            raise ValueError("request subject_id and acquisition subject_id disagree")
        if self.backend and self.plan:
            raise ValueError("Specify either monolithic backend or staged plan, not both")
        return self


class AnatomyBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = "2.0.0"
    subject_id: str
    study_id: str
    acquisition_id: str
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    frames: list[CoordinateFrame] = Field(default_factory=list)
    registrations: list[RegistrationRef] = Field(default_factory=list)
    labels: list[AnatomyLabel] = Field(default_factory=list)
    stages: list[StageRecord] = Field(default_factory=list)
    qc: GeometryQC | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    bundle_fingerprint: str | None = None

    def artifact_kinds(self) -> set[str]:
        return {artifact.kind for artifact in self.artifacts}

    @property
    def surface_ready(self) -> bool:
        kinds = self.artifact_kinds()
        return "segmentation" in kinds and "surface_mesh" in kinds

    @property
    def ep_ready(self) -> bool:
        kinds = self.artifact_kinds()
        return (
            {"surface_mesh", "volume_mesh", "coordinate_field", "fiber_field"} <= kinds
            and self.qc is not None
            and self.qc.passed
        )

    @property
    def mechanics_ready(self) -> bool:
        kinds = self.artifact_kinds()
        return "volume_mesh" in kinds and self.qc is not None and self.qc.passed

    @property
    def flow_ready(self) -> bool:
        kinds = self.artifact_kinds()
        return "surface_mesh" in kinds and self.qc is not None and self.qc.passed

    @property
    def ready(self) -> bool:
        """Backward-compatible baseline readiness for geometry consumers."""
        kinds = self.artifact_kinds()
        required = {"segmentation", "surface_mesh", "volume_mesh"}
        return required <= kinds and self.qc is not None and self.qc.passed


class MeshInspection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str | None = None
    point_count: int = Field(ge=0)
    cell_count: int = Field(ge=0)
    tetra_count: int = Field(default=0, ge=0)
    triangle_count: int = Field(default=0, ge=0)
    connected_components: int | None = Field(default=None, ge=0)
    degenerate_fraction: float | None = Field(default=None, ge=0, le=1)
    minority_orientation_fraction: float | None = Field(default=None, ge=0, le=1)
    boundary_edge_count: int | None = Field(default=None, ge=0)
    nonmanifold_edge_count: int | None = Field(default=None, ge=0)
    min_edge_length: float | None = Field(default=None, ge=0)
    max_edge_length: float | None = Field(default=None, ge=0)
    min_abs_tetra_volume: float | None = Field(default=None, ge=0)
    max_abs_tetra_volume: float | None = Field(default=None, ge=0)
    finite: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScarThresholdSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    border_threshold: float
    core_threshold: float
    method: Literal["explicit", "normalized_explicit"] = "explicit"

    @model_validator(mode="after")
    def ordered(self) -> "ScarThresholdSpec":
        if self.border_threshold >= self.core_threshold:
            raise ValueError("border_threshold must be lower than core_threshold")
        return self


class FiberAngleProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alpha_endo_deg: float = 60.0
    alpha_epi_deg: float = -60.0
    beta_endo_deg: float = 0.0
    beta_epi_deg: float = 0.0
