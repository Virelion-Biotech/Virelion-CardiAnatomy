from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Any, Callable

from .backends import StageOutput
from .execution import run_command
from .integrations import (
    biv_me_command,
    biv_volumetric_command,
    myomesh_command,
    nnunet_predict_command,
)
from .io import inspect_mesh_file
from .models import AnatomyBundle, AnatomyRequest, ArtifactKind, ArtifactRef, StageName
from .provenance import file_sha256
from .qc import qc_from_inspection


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
    probe_executable: str | None = None

    def available(self) -> bool:
        return (
            self.probe_executable is None
            or shutil.which(self.probe_executable) is not None
        )

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
        probe_executable="nnUNetv2_predict",
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
        probe_executable="python",
    )


def register_standard_external_stage_backends(service) -> None:
    service.register_stage_backend(nnunet_segmentation_backend())
    for stage in ("surface_mesh", "volume_mesh", "coordinates", "microstructure"):
        service.register_stage_backend(biv_volumetric_stage_backend(stage))


def _declared_outputs(
    request: AnatomyRequest,
    output_specs: list[dict[str, Any]],
    *,
    producer: str,
) -> list[ArtifactRef]:
    artifacts: list[ArtifactRef] = []
    for index, spec in enumerate(output_specs):
        if not isinstance(spec, dict):
            raise ValueError(f"outputs[{index}] must be an object")
        for key in ("artifact_id", "kind", "path"):
            if not spec.get(key):
                raise ValueError(f"outputs[{index}] requires {key}")
        path = Path(str(spec["path"]))
        artifacts.append(
            _artifact_from_output(
                request=request,
                path=path,
                artifact_id=str(spec["artifact_id"]),
                kind=spec["kind"],
                producer=producer,
                derived_from=[request.acquisition.source.artifact_id],
                frame_id=spec.get("frame_id"),
                metadata=dict(spec.get("metadata") or {}),
            )
        )
    return artifacts


def _geometry_qc_from_outputs(artifacts: list[ArtifactRef]):
    for artifact in reversed(artifacts):
        if artifact.kind not in {"volume_mesh", "surface_mesh"}:
            continue
        path = Path(artifact.uri)
        if path.is_file():
            return qc_from_inspection(
                inspect_mesh_file(path),
                require_watertight=artifact.kind == "surface_mesh",
            )
    return None


class BivMeBackend:
    name = "biv-me"

    def available(self) -> bool:
        return shutil.which("python") is not None

    def build(self, request: AnatomyRequest) -> AnatomyBundle:
        parameters = request.parameters
        for key in ("main_script", "config_file", "outputs"):
            if key not in parameters:
                raise ValueError(f"biv-me backend requires parameter {key}")
        command = biv_me_command(
            main_script=str(parameters["main_script"]),
            config_file=str(parameters["config_file"]),
            case_name=str(parameters.get("case_name", request.subject_id)),
            python_executable=str(parameters.get("python_executable", "python")),
        )
        result = run_command(
            command,
            cwd=parameters.get("cwd"),
            timeout=float(parameters.get("timeout", 7200.0)),
        )
        outputs = _declared_outputs(
            request,
            list(parameters["outputs"]),
            producer="biv-me",
        )
        return AnatomyBundle(
            subject_id=request.subject_id,
            study_id=request.acquisition.study_id,
            acquisition_id=request.acquisition.acquisition_id,
            artifacts=[request.acquisition.source, *outputs],
            qc=_geometry_qc_from_outputs(outputs),
            provenance={
                "backend": "biv-me",
                "command": list(result.command),
                "duration_seconds": result.duration_seconds,
                "executable": result.executable,
            },
        )


class MyoMeshBackend:
    name = "myomesh"

    def available(self) -> bool:
        return shutil.which("python") is not None

    def build(self, request: AnatomyRequest) -> AnatomyBundle:
        parameters = request.parameters
        for key in ("input_mat", "outputs"):
            if key not in parameters:
                raise ValueError(f"MyoMesh backend requires parameter {key}")
        command = myomesh_command(
            input_mat=str(parameters["input_mat"]),
            python_executable=str(parameters.get("python_executable", "python")),
            no_alg=bool(parameters.get("no_alg", False)),
            no_align_dicom=bool(parameters.get("no_align_dicom", False)),
            extra_args=tuple(str(item) for item in parameters.get("extra_args", [])),
        )
        result = run_command(
            command,
            cwd=parameters.get("cwd"),
            timeout=float(parameters.get("timeout", 7200.0)),
        )
        outputs = _declared_outputs(
            request,
            list(parameters["outputs"]),
            producer="myomesh",
        )
        return AnatomyBundle(
            subject_id=request.subject_id,
            study_id=request.acquisition.study_id,
            acquisition_id=request.acquisition.acquisition_id,
            artifacts=[request.acquisition.source, *outputs],
            qc=_geometry_qc_from_outputs(outputs),
            provenance={
                "backend": "myomesh",
                "command": list(result.command),
                "duration_seconds": result.duration_seconds,
                "executable": result.executable,
            },
        )


def register_standard_monolithic_backends(service) -> None:
    service.register_backend(BivMeBackend())
    service.register_backend(MyoMeshBackend())


@dataclass
class ExistingArtifactStageBackend:
    stage: StageName
    output_kind: ArtifactKind
    name: str = "external"

    def available(self) -> bool:
        return True

    def run(
        self,
        request: AnatomyRequest,
        bundle: AnatomyBundle,
        workdir: Path,
        parameters: dict,
    ) -> StageOutput:
        if not parameters.get("path"):
            raise ValueError(
                f"external/{self.stage} requires explicit parameter path"
            )
        path = Path(str(parameters["path"]))
        artifact = _artifact_from_output(
            request=request,
            path=path,
            artifact_id=str(
                parameters.get(
                    "artifact_id",
                    f"{request.acquisition.acquisition_id}-{self.stage}",
                )
            ),
            kind=self.output_kind,
            producer=str(parameters.get("producer", "external")),
            derived_from=[
                str(value)
                for value in parameters.get(
                    "derived_from",
                    [request.acquisition.source.artifact_id],
                )
            ],
            frame_id=parameters.get("frame_id"),
            metadata=dict(parameters.get("metadata") or {}),
        )
        return StageOutput(artifacts=[artifact])


def register_existing_artifact_backends(service) -> None:
    mapping: dict[StageName, ArtifactKind] = {
        "segmentation": "segmentation",
        "contours": "contour_set",
        "surface_fit": "model_fit",
        "surface_mesh": "surface_mesh",
        "volume_mesh": "volume_mesh",
        "coordinates": "coordinate_field",
        "microstructure": "fiber_field",
        "scar": "scar_map",
        "registration": "registration",
    }
    for stage, kind in mapping.items():
        service.register_stage_backend(
            ExistingArtifactStageBackend(stage=stage, output_kind=kind)
        )
