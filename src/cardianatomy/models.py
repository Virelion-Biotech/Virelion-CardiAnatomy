from __future__ import annotations

from datetime import datetime
import math
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


def _safe_identifier(value: str, field_name: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    if value in {".", ".."} or any(token in value for token in ("/", "\\", "\x00")):
        raise ValueError(f"{field_name} contains unsafe path characters")
    reserved = {"CON", "PRN", "AUX", "NUL"} | {
        f"{prefix}{n}" for prefix in ("COM", "LPT") for n in range(1, 10)
    }
    if (value.endswith((".", " ")) or value.split(".")[0].upper() in reserved
            or any(ord(char) < 32 or char in ':<>"|?*' for char in value)):
        raise ValueError(f"{field_name} is not a portable filesystem identifier")
    return value


class ArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(min_length=1)
    kind: ArtifactKind
    uri: str = Field(min_length=1)
    sha256: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-fA-F]{64}$",
    )
    media_type: str | None = None
    producer: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    frame_id: str | None = None
    subject_id: str | None = None
    study_id: str | None = None
    acquisition_id: str | None = None
    derived_from: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_lineage(self) -> "ArtifactRef":
        if len(self.derived_from) != len(set(self.derived_from)):
            raise ValueError("derived_from must not contain duplicate artifact IDs")
        if self.artifact_id in self.derived_from:
            raise ValueError("artifact cannot be derived from itself")
        return self


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

    @field_validator("subject_id", "study_id", "acquisition_id")
    @classmethod
    def safe_identifiers(cls, value: str, info) -> str:
        return _safe_identifier(value, info.field_name)

    @model_validator(mode="after")
    def validate_geometry_metadata(self) -> "ImagingAcquisition":
        if self.shape is not None:
            if not self.shape or any(int(value) <= 0 for value in self.shape):
                raise ValueError("shape dimensions must be strictly positive")
        if self.voxel_spacing_mm is not None:
            spacing = np.asarray(self.voxel_spacing_mm, dtype=float)
            if (
                len(spacing) == 0
                or not np.all(np.isfinite(spacing))
                or np.any(spacing <= 0)
            ):
                raise ValueError(
                    "voxel_spacing_mm must contain finite positive values"
                )
            if self.shape is not None and len(spacing) != len(self.shape):
                raise ValueError(
                    "voxel_spacing_mm dimensionality must match shape"
                )
        for name, phase in self.selected_phases.items():
            if phase < 0:
                raise ValueError(f"selected phase {name!r} must be non-negative")
            if self.phase_count is not None and phase >= self.phase_count:
                raise ValueError(
                    f"selected phase {name!r} is outside phase_count"
                )
        return self


class DicomSeriesSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    series_uid_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-fA-F]{64}$",
    )
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

    @model_validator(mode="after")
    def validate_dicom_geometry(self) -> "DicomSeriesSummary":
        if self.pixel_spacing_mm is not None:
            spacing = np.asarray(self.pixel_spacing_mm, dtype=float)
            if not np.all(np.isfinite(spacing)) or np.any(spacing <= 0):
                raise ValueError("pixel_spacing_mm must be finite and positive")
        if self.image_orientation_patient is not None:
            orientation = np.asarray(
                self.image_orientation_patient,
                dtype=float,
            )
            if len(orientation) != 6 or not np.all(np.isfinite(orientation)):
                raise ValueError(
                    "image_orientation_patient must contain six finite values"
                )
        return self


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
            from .transforms import validate_affine

            validate_affine(np.asarray(self.affine_to_parent, dtype=float))
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
            from .transforms import validate_affine

            validate_affine(np.asarray(self.matrix, dtype=float))
        if self.quality_metric is not None and not math.isfinite(self.quality_metric):
            raise ValueError("quality_metric must be finite")
        return self


class AnatomyLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    value: int = Field(ge=0)
    structure: str = Field(min_length=1)
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
        for key, value in self.metrics.items():
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"QC metric {key!r} must be finite")
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


    @model_validator(mode="after")
    def consistent_stage_status(self) -> "StageRecord":
        if self.status == "ok" and self.errors:
            raise ValueError("status='ok' is inconsistent with stage errors")
        if self.status == "error" and not self.errors:
            raise ValueError("status='error' requires at least one error")
        if (
            self.started_at is not None
            and self.finished_at is not None
            and self.finished_at < self.started_at
        ):
            raise ValueError("finished_at cannot precede started_at")
        if self.duration_seconds is not None and not math.isfinite(
            self.duration_seconds
        ):
            raise ValueError("duration_seconds must be finite")
        return self


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

    @field_validator("subject_id")
    @classmethod
    def safe_subject_id(cls, value: str) -> str:
        return _safe_identifier(value, "subject_id")

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
    bundle_fingerprint: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-fA-F]{64}$",
    )

    @model_validator(mode="after")
    def bundle_integrity(self) -> "AnatomyBundle":
        artifact_ids = [item.artifact_id for item in self.artifacts]
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("bundle contains duplicate artifact_id values")
        frame_ids = [item.frame_id for item in self.frames]
        if len(frame_ids) != len(set(frame_ids)):
            raise ValueError("bundle contains duplicate frame_id values")
        registration_ids = [item.registration_id for item in self.registrations]
        if len(registration_ids) != len(set(registration_ids)):
            raise ValueError("bundle contains duplicate registration_id values")
        label_values = [item.value for item in self.labels]
        if len(label_values) != len(set(label_values)):
            raise ValueError("bundle contains duplicate anatomical label values")
        if self.bundle_fingerprint is not None:
            from .provenance import sha256

            expected = sha256(
                self.model_dump(
                    mode="json",
                    exclude={"bundle_fingerprint"},
                )
            )
            if self.bundle_fingerprint.lower() != expected:
                raise ValueError("bundle fingerprint does not match bundle contents")
        return self

    def artifact_kinds(self) -> set[str]:
        return {artifact.kind for artifact in self.artifacts}

    def _qc_covers(self, kind: str) -> bool:
        return self.qc is not None and self.qc.passed and (
            self.qc.artifact_id is None
            or any(a.kind == kind and a.artifact_id == self.qc.artifact_id
                   for a in self.artifacts)
        )

    @property
    def surface_ready(self) -> bool:
        kinds = self.artifact_kinds()
        return "segmentation" in kinds and "surface_mesh" in kinds

    @property
    def ep_ready(self) -> bool:
        kinds = self.artifact_kinds()
        return (
            {"surface_mesh", "volume_mesh", "coordinate_field", "fiber_field"} <= kinds
            and self._qc_covers("volume_mesh")
        )

    @property
    def mechanics_ready(self) -> bool:
        kinds = self.artifact_kinds()
        return "volume_mesh" in kinds and self._qc_covers("volume_mesh")

    @property
    def flow_ready(self) -> bool:
        kinds = self.artifact_kinds()
        return "surface_mesh" in kinds and self._qc_covers("surface_mesh")

    @property
    def ready(self) -> bool:
        """Backward-compatible baseline readiness for geometry consumers."""
        kinds = self.artifact_kinds()
        required = {"segmentation", "surface_mesh", "volume_mesh"}
        return required <= kinds and self._qc_covers("volume_mesh")


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
        if not (
            math.isfinite(self.border_threshold)
            and math.isfinite(self.core_threshold)
        ):
            raise ValueError("scar thresholds must be finite")
        if self.border_threshold >= self.core_threshold:
            raise ValueError("border_threshold must be lower than core_threshold")
        return self


class FiberAngleProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alpha_endo_deg: float = 60.0
    alpha_epi_deg: float = -60.0
    beta_endo_deg: float = 0.0
    beta_epi_deg: float = 0.0

    @model_validator(mode="after")
    def finite_angles(self) -> "FiberAngleProfile":
        values = (
            self.alpha_endo_deg,
            self.alpha_epi_deg,
            self.beta_endo_deg,
            self.beta_epi_deg,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("fiber angles must be finite")
        return self
