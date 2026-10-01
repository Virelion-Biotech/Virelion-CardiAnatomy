from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import unquote, urlparse

from .backends import StageOutput
from .io import inspect_mesh_file
from .models import AnatomyBundle, AnatomyRequest, ArtifactRef
from .provenance import file_sha256
from .qc import qc_from_inspection
from .report import render_html_report


def local_artifact_path(artifact: ArtifactRef) -> Path | None:
    parsed = urlparse(artifact.uri)
    if parsed.scheme == "file":
        return Path(unquote(parsed.path))
    if parsed.scheme:
        return None
    return Path(artifact.uri)


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
        inspection = inspect_mesh_file(path)
        qc = qc_from_inspection(
            inspection,
            require_watertight=bool(parameters.get("require_watertight", False)),
        )
        report_path = workdir / "geometry-qc.json"
        report_path.write_text(
            json.dumps(
                {
                    "artifact_id": selected.artifact_id,
                    "inspection": inspection.model_dump(mode="json"),
                    "qc": qc.model_dump(mode="json"),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
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
        json_path.write_text(
            json.dumps(bundle.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        html_path.write_text(render_html_report(bundle), encoding="utf-8")
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
