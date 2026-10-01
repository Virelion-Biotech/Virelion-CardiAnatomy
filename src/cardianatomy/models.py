from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ArtifactKind = Literal[
    "dicom_series",
    "segmentation",
    "surface_mesh",
    "volume_mesh",
    "fiber_field",
    "scar_map",
    "coordinate_field",
    "registration",
    "qc_report",
]


class ArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    kind: ArtifactKind
    uri: str
    sha256: str | None = Field(default=None, min_length=64, max_length=64)
    media_type: str | None = None
    producer: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImagingAcquisition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: str
    study_id: str
    acquisition_id: str
    modality: Literal["CMR", "CT", "ECHO", "OTHER"]
    acquired_at: datetime | None = None
    protocol: str | None = None
    coordinate_system: str | None = None
    source: ArtifactRef


class CoordinateFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")

    frame_id: str
    convention: str
    units: str = "mm"
    description: str | None = None


class RegistrationRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    registration_id: str
    source_frame: str
    target_frame: str
    transform: ArtifactRef
    method: str
    quality_metric: float | None = None


class GeometryQC(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool
    checks: dict[str, bool] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent_status(self) -> "GeometryQC":
        if self.passed and (self.errors or any(not v for v in self.checks.values())):
            raise ValueError("passed=True is inconsistent with failed checks or errors")
        return self


class AnatomyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: str
    acquisition: ImagingAcquisition
    requested_outputs: list[ArtifactKind] = Field(
        default_factory=lambda: ["segmentation", "surface_mesh", "volume_mesh"]
    )
    backend: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class AnatomyBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = "1.0"
    subject_id: str
    study_id: str
    acquisition_id: str
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    frames: list[CoordinateFrame] = Field(default_factory=list)
    registrations: list[RegistrationRef] = Field(default_factory=list)
    qc: GeometryQC | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)

    @property
    def ready(self) -> bool:
        kinds = {artifact.kind for artifact in self.artifacts}
        required = {"segmentation", "surface_mesh", "volume_mesh"}
        return required <= kinds and self.qc is not None and self.qc.passed
