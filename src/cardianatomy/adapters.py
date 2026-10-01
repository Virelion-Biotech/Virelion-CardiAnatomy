from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .backends import StageOutput
from .execution import run_command
from .integrations import (
    biv_volumetric_command,
    nnunet_predict_command,
)
from .models import AnatomyBundle, AnatomyRequest, ArtifactKind, ArtifactRef, StageName
from .provenance import file_sha256


CommandFactory = Callable[[AnatomyRequest, Path, dict[str, Any]], list[str]]


def _resolve_output(path_value: str, workdir: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = workdir / path
    return path


def _artifact_from_output(
    *,
    request: AnatomyRequest,
    path: Path,
    artifact_id: str,
    kind: ArtifactKind,
    producer: str,
    derived_from: list[str],
    frame_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ArtifactRef:
    if not path.is_file():
        raise FileNotFoundError(f"Declared backend output does not exist: {path}")
    return ArtifactRef(
        artifact_id=artifact_id,
        kind=kind,
        uri=str(path),
        sha256=file_sha256(path),
        size_bytes=path.stat().st_size,
        producer=producer,
        frame_id=frame_id,
        subject_id=request.subject_id,
        study_id=request.acquisition.study_id,
        acquisition_id=request.acquisition.acquisition_id,
        derived_from=derived_from,
        metadata=metadata or {},
    )


@dataclass
class DeclaredCommandStageBackend:
    name: str
    stage: StageName
    output_kind: ArtifactKind
    command_factory: CommandFactory

    def available(self) -> bool:
        return True

    def run(
        self,
        request: AnatomyRequest,
        bundle: AnatomyBundle,
        workdir: Path,
        parameters: dict,
    ) -> StageOutput:
        if "output_file" not in parameters:
            raise ValueError(
                f"{self.name}/{self.stage} requires explicit parameter output_file"
            )
        command = self.command_factory(request, workdir, parameters)
        result = run_command(
            command,
            cwd=parameters.get("cwd"),
            timeout=float(parameters.get("timeout", 3600.0)),
        )
        output = _resolve_output(str(parameters["output_file"]), workdir)
        artifact_id = str(
            parameters.get(
                "artifact_id",
                f"{request.acquisition.acquisition_id}-{self.stage}",
            )
        )
        artifact = _artifact_from_output(
            request=request,
            path=output,
            artifact_id=artifact_id,
            kind=self.output_kind,
            producer=self.name,
            derived_from=[item.artifact_id for item in bundle.artifacts],
            frame_id=parameters.get("frame_id"),
            metadata={
                "command": list(result.command),
                "duration_seconds": result.duration_seconds,
                "returncode": result.returncode,
                "executable": result.executable,
            },
        )
        return StageOutput(artifacts=[artifact])


def nnunet_segmentation_backend() -> DeclaredCommandStageBackend:
    def build_command(
        request: AnatomyRequest,
        workdir: Path,
        parameters: dict[str, Any],
    ) -> list[str]:
        required = ("input_dir", "output_dir", "dataset")
        missing = [key for key in required if not parameters.get(key)]
        if missing:
            raise ValueError(f"nnU-Net backend missing parameters: {missing}")
        folds_raw = parameters.get("folds")
        folds = None if folds_raw is None else tuple(str(value) for value in folds_raw)
        return nnunet_predict_command(
            input_dir=str(parameters["input_dir"]),
            output_dir=str(parameters["output_dir"]),
            dataset=str(parameters["dataset"]),
            configuration=str(parameters.get("configuration", "3d_fullres")),
            folds=folds,
            device=parameters.get("device"),
        )

    return DeclaredCommandStageBackend(
        name="nnunet",
        stage="segmentation",
        output_kind="segmentation",
        command_factory=build_command,
    )


def biv_volumetric_stage_backend(stage: StageName) -> DeclaredCommandStageBackend:
    mapping: dict[StageName, tuple[str, ArtifactKind]] = {
        "surface_mesh": ("surface", "surface_mesh"),
        "volume_mesh": ("volumetric", "volume_mesh"),
        "coordinates": ("uvc-fiber", "coordinate_field"),
        "microstructure": ("uvc-fiber", "fiber_field"),
    }
    if stage not in mapping:
        raise ValueError(f"Unsupported BiV volumetric stage: {stage}")
    component, output_kind = mapping[stage]

    def build_command(
        request: AnatomyRequest,
        workdir: Path,
        parameters: dict[str, Any],
    ) -> list[str]:
        for key in ("run_script", "data_dir"):
            if not parameters.get(key):
                raise ValueError(f"BiV volumetric backend requires parameter {key}")
        return biv_volumetric_command(
            run_script=str(parameters["run_script"]),
            data_dir=str(parameters["data_dir"]),
            components=(component,),
            subject=str(parameters.get("subject", request.subject_id)),
            instance=parameters.get("instance"),
            timeframe=parameters.get("timeframe"),
            workspace_dir=parameters.get("workspace_dir"),
            carp_bin_dir=parameters.get("carp_bin_dir"),
            python_executable=str(parameters.get("python_executable", "python")),
        )

    return DeclaredCommandStageBackend(
        name="biv-volumetric-meshing",
        stage=stage,
        output_kind=output_kind,
        command_factory=build_command,
    )


def register_standard_external_stage_backends(service) -> None:
    service.register_stage_backend(nnunet_segmentation_backend())
    for stage in ("surface_mesh", "volume_mesh", "coordinates", "microstructure"):
        service.register_stage_backend(biv_volumetric_stage_backend(stage))
