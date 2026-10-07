from __future__ import annotations

from pathlib import Path

from .backends import StageOutput
from .io import inspect_mesh_file
from .models import AnatomyBundle, AnatomyRequest, ArtifactRef
from .provenance import file_sha256
from .pipeline import _local_artifact_path
from .qc import qc_from_inspection
from .report import render_html_report
from .serialization import write_json_atomic, write_text_atomic


def local_artifact_path(artifact: ArtifactRef) -> Path | None:
    return _local_artifact_path(artifact.uri)


class NativeIngestBackend:
    name = "native"
    stage = "ingest"

    def available(self) -> bool:
        return True

    def run(
        self,
        request: AnatomyRequest,
        bundle: AnatomyBundle,
        workdir: Path,
        parameters: dict,
    ) -> StageOutput:
        source = request.acquisition.source
        path = local_artifact_path(source)
        warnings: list[str] = []
        artifacts: list[ArtifactRef] = []
        if path is None:
            warnings.append("source is remote; content hashing deferred")
            return StageOutput(warnings=warnings)
        if not path.is_file() and not path.is_dir():
            raise FileNotFoundError(f"Anatomy source does not exist: {path}")
        if path.is_file():
            hashed = source.model_copy(
                update={
                    "sha256": file_sha256(path),
                    "size_bytes": path.stat().st_size,
                    "producer": source.producer or "cardianatomy.native.ingest",
                }
            )
            artifacts.append(
                hashed.model_copy(update={"artifact_id": source.artifact_id + "-verified"})
            )
        else:
            warnings.append(
                "directory source verified for existence; use DICOM inspection for series hashes"
            )
        return StageOutput(artifacts=artifacts, warnings=warnings)


class NativeQCBackend:
    name = "native"
    stage = "qc"

    def available(self) -> bool:
        return True

    def run(
        self,
        request: AnatomyRequest,
        bundle: AnatomyBundle,
        workdir: Path,
        parameters: dict,
    ) -> StageOutput:
        candidates = [
            item
            for item in reversed(bundle.artifacts)
            if item.kind in {"volume_mesh", "surface_mesh"}
        ]
        if not candidates:
            raise ValueError("Native geometry QC requires a surface_mesh or volume_mesh artifact")
        selected = candidates[0]
        path = local_artifact_path(selected)
        if path is None or not path.is_file():
            raise ValueError("Native geometry QC requires a local mesh artifact")
        watertight = parameters.get("require_watertight", False)
        if not isinstance(watertight, bool):
            raise ValueError("require_watertight must be a boolean")
        inspection = inspect_mesh_file(path)
        quality = parameters.get("minimum_shape_quality")
        qc = qc_from_inspection(
            inspection,
            require_watertight=watertight,
            minimum_shape_quality=None if quality is None else float(quality),
        )
        qc.artifact_id = selected.artifact_id
        report_path = workdir / "geometry-qc.json"
        write_json_atomic(report_path, {
            "artifact_id": selected.artifact_id,
            "inspection": inspection.model_dump(mode="json"),
            "qc": qc.model_dump(mode="json"),
        })
        report = ArtifactRef(
            artifact_id=f"{selected.artifact_id}-qc",
            kind="qc_report",
            uri=str(report_path),
            sha256=file_sha256(report_path),
            size_bytes=report_path.stat().st_size,
            producer="cardianatomy.native.qc",
            subject_id=request.subject_id,
            study_id=request.acquisition.study_id,
            acquisition_id=request.acquisition.acquisition_id,
            derived_from=[selected.artifact_id],
        )
        return StageOutput(artifacts=[report], qc=qc)


class NativeExportBackend:
    name = "native"
    stage = "export"

    def available(self) -> bool:
        return True

    def run(
        self,
        request: AnatomyRequest,
        bundle: AnatomyBundle,
        workdir: Path,
        parameters: dict,
    ) -> StageOutput:
        json_path = workdir / "anatomy-bundle.json"
        html_path = workdir / "anatomy-report.html"
        write_json_atomic(json_path, bundle.model_dump(mode="json"))
        write_text_atomic(html_path, render_html_report(bundle))
        artifacts = [
            ArtifactRef(
                artifact_id="anatomy-bundle-json",
                kind="other",
                uri=str(json_path),
                sha256=file_sha256(json_path),
                size_bytes=json_path.stat().st_size,
                producer="cardianatomy.native.export",
                subject_id=request.subject_id,
                study_id=request.acquisition.study_id,
                acquisition_id=request.acquisition.acquisition_id,
            ),
            ArtifactRef(
                artifact_id="anatomy-report-html",
                kind="report",
                uri=str(html_path),
                sha256=file_sha256(html_path),
                size_bytes=html_path.stat().st_size,
                producer="cardianatomy.native.export",
                subject_id=request.subject_id,
                study_id=request.acquisition.study_id,
                acquisition_id=request.acquisition.acquisition_id,
            ),
        ]
        return StageOutput(artifacts=artifacts)


def register_native_stage_backends(service) -> None:
    service.register_stage_backend(NativeIngestBackend())
    service.register_stage_backend(NativeQCBackend())
    service.register_stage_backend(NativeExportBackend())
