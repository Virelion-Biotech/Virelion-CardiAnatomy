from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from time import perf_counter
from urllib.parse import unquote, urlparse

from .backends import AnatomyStageBackend, BackendUnavailable
from .models import (
    AnatomyBundle,
    AnatomyRequest,
    ArtifactRef,
    GeometryQC,
    PipelinePlan,
    StageName,
    StageRecord,
)
from .provenance import file_sha256, sha256


STAGE_ORDER: tuple[StageName, ...] = (
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
)


def validate_stage_order(plan: PipelinePlan) -> None:
    rank = {stage: index for index, stage in enumerate(STAGE_ORDER)}
    ordered = [rank[stage] for stage in plan.stages]
    if ordered != sorted(ordered):
        raise ValueError("Pipeline stages must follow the canonical anatomical-twinning order")


def stage_fingerprint(
    stage: StageName,
    backend: str,
    input_artifacts: list,
    parameters: dict,
) -> str:
    inputs = [
        {
            "artifact_id": item.artifact_id,
            "sha256": item.sha256,
            "uri": item.uri,
            "kind": item.kind,
        }
        for item in sorted(input_artifacts, key=lambda value: value.artifact_id)
    ]
    return sha256({"stage": stage, "backend": backend, "inputs": inputs, "parameters": parameters})


def bundle_fingerprint(bundle: AnatomyBundle) -> str:
    return sha256(bundle.model_dump(mode="json", exclude={"bundle_fingerprint"}))


def _local_artifact_path(uri: str) -> Path | None:
    parsed = urlparse(uri)
    if parsed.scheme == "file":
        return Path(unquote(parsed.path))
    if not parsed.scheme:
        return Path(uri)
    return None


def _restorable_artifacts(
    payload: object,
    expected_ids: list[str],
) -> list[ArtifactRef] | None:
    if not isinstance(payload, list):
        return None
    try:
        artifacts = [ArtifactRef.model_validate(item) for item in payload]
    except Exception:
        return None
    ids = [item.artifact_id for item in artifacts]
    if ids != expected_ids or len(ids) != len(set(ids)):
        return None
    for artifact in artifacts:
        path = _local_artifact_path(artifact.uri)
        if path is None:
            continue
        if not path.is_file():
            return None
        stat = path.stat()
        if artifact.size_bytes is not None and stat.st_size != artifact.size_bytes:
            return None
        if artifact.sha256 is not None and file_sha256(path) != artifact.sha256:
            return None
    return artifacts


def _write_sidecar_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            json.dump(payload, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _ensure_unique_output_ids(
    bundle: AnatomyBundle,
    artifacts: list[ArtifactRef],
) -> None:
    existing = {item.artifact_id for item in bundle.artifacts}
    output_ids = [item.artifact_id for item in artifacts]
    duplicates = sorted(
        item
        for item in set(output_ids)
        if output_ids.count(item) > 1 or item in existing
    )
    if duplicates:
        raise ValueError(
            "Pipeline produced duplicate artifact IDs: "
            + ", ".join(duplicates)
        )


class PipelineExecutor:
    def __init__(self) -> None:
        self._backends: dict[tuple[str, str], AnatomyStageBackend] = {}

    def register(self, backend: AnatomyStageBackend) -> None:
        self._backends[(backend.stage, backend.name)] = backend

    def backends(self) -> dict[str, list[str]]:
        output: dict[str, list[str]] = {}
        for stage, name in self._backends:
            output.setdefault(stage, []).append(name)
        return {stage: sorted(names) for stage, names in sorted(output.items())}

    def execute(self, request: AnatomyRequest, plan: PipelinePlan) -> AnatomyBundle:
        validate_stage_order(plan)
        workdir = (
            Path(request.output_root or "work")
            / request.subject_id
            / request.acquisition.acquisition_id
        )
        workdir.mkdir(parents=True, exist_ok=True)
        bundle = AnatomyBundle(
            subject_id=request.subject_id,
            study_id=request.acquisition.study_id,
            acquisition_id=request.acquisition.acquisition_id,
            artifacts=[request.acquisition.source],
            provenance={"pipeline": "Virelion-CardiAnatomy", "contract_version": "2.0.0"},
        )
        for stage in plan.stages:
            backend_name = plan.backends.get(stage)
            if not backend_name:
                raise BackendUnavailable(f"No backend selected for anatomy stage: {stage}")
            backend = self._backends.get((stage, backend_name))
            if backend is None or not backend.available():
                raise BackendUnavailable(f"Stage backend unavailable: {stage}/{backend_name}")
            parameters = dict(plan.stage_parameters.get(stage, {}))
            fingerprint = stage_fingerprint(stage, backend_name, bundle.artifacts, parameters)
            sidecar = workdir / f"stage-{stage}.json"
            if plan.resume and sidecar.is_file():
                try:
                    previous = json.loads(sidecar.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    previous = {}
                previous_record = previous.get("record")
                if (
                    isinstance(previous_record, dict)
                    and previous_record.get("fingerprint") == fingerprint
                    and previous_record.get("status") == "ok"
                    and previous_record.get("stage") == stage
                    and previous_record.get("backend") == backend_name
                ):
                    expected_ids = previous_record.get("output_artifact_ids", [])
                    restored_artifacts = _restorable_artifacts(
                        previous.get("artifacts", []),
                        expected_ids if isinstance(expected_ids, list) else [],
                    )
                    if restored_artifacts is not None:
                        _ensure_unique_output_ids(bundle, restored_artifacts)
                        try:
                            restored_qc = (
                                None
                                if previous.get("qc") is None
                                else GeometryQC.model_validate(previous["qc"])
                            )
                            restored_record = StageRecord.model_validate(
                                previous_record
                            )
                        except Exception:
                            restored_artifacts = None
                        if restored_artifacts is not None:
                            bundle.artifacts.extend(restored_artifacts)
                            if restored_qc is not None:
                                bundle.qc = restored_qc
                            bundle.stages.append(restored_record)
                            continue
            started = datetime.now(timezone.utc)
            tick = perf_counter()
            try:
                output = backend.run(request, bundle, workdir, parameters)
            except Exception as exc:
                finished = datetime.now(timezone.utc)
                record = StageRecord(
                    stage=stage,
                    backend=backend_name,
                    status="error",
                    fingerprint=fingerprint,
                    input_artifact_ids=[item.artifact_id for item in bundle.artifacts],
                    parameters=parameters,
                    started_at=started,
                    finished_at=finished,
                    duration_seconds=perf_counter() - tick,
                    errors=[str(exc)],
                )
                bundle.stages.append(record)
                _write_sidecar_atomic(
                    sidecar,
                    {
                        "record": record.model_dump(mode="json"),
                        "artifacts": [],
                        "qc": None,
                    },
                )
                raise
            finished = datetime.now(timezone.utc)
            record = StageRecord(
                stage=stage,
                backend=backend_name,
                status="ok",
                fingerprint=fingerprint,
                input_artifact_ids=[item.artifact_id for item in bundle.artifacts],
                output_artifact_ids=[item.artifact_id for item in output.artifacts],
                parameters=parameters,
                started_at=started,
                finished_at=finished,
                duration_seconds=perf_counter() - tick,
                warnings=output.warnings,
            )
            _ensure_unique_output_ids(bundle, output.artifacts)
            bundle.artifacts.extend(output.artifacts)
            if output.qc is not None:
                bundle.qc = output.qc
            bundle.stages.append(record)
            _write_sidecar_atomic(
                sidecar,
                {
                    "record": record.model_dump(mode="json"),
                    "artifacts": [
                        item.model_dump(mode="json")
                        for item in output.artifacts
                    ],
                    "qc": (
                        None
                        if output.qc is None
                        else output.qc.model_dump(mode="json")
                    ),
                },
            )
        bundle.bundle_fingerprint = bundle_fingerprint(bundle)
        return bundle


def attach_file_hash(artifact, path: str | Path):
    path = Path(path)
    return artifact.model_copy(
        update={"sha256": file_sha256(path), "size_bytes": path.stat().st_size}
    )
