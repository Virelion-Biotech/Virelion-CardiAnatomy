import json
from pathlib import Path
import threading

import pytest

from cardianatomy import (
    AnatomyRequest,
    ArtifactRef,
    ImagingAcquisition,
    PipelineExecutor,
    PipelinePlan,
    file_sha256,
    stage_fingerprint,
)
from cardianatomy.backends import StageOutput


class CountingSegmentationBackend:
    name = "stress"
    stage = "segmentation"

    def __init__(self) -> None:
        self.calls = 0

    def available(self) -> bool:
        return True

    def run(self, request, bundle, workdir: Path, parameters):
        self.calls += 1
        path = workdir / "seg.nii.gz"
        payload = f"segmentation-run-{self.calls}".encode()
        path.write_bytes(payload)
        return StageOutput(
            artifacts=[
                ArtifactRef(
                    artifact_id="seg",
                    kind="segmentation",
                    uri=str(path),
                    sha256=file_sha256(path),
                    size_bytes=path.stat().st_size,
                    producer=self.name,
                )
            ]
        )


class DuplicateOutputBackend:
    name = "duplicate"
    stage = "segmentation"

    def available(self) -> bool:
        return True

    def run(self, request, bundle, workdir: Path, parameters):
        return StageOutput(
            artifacts=[
                ArtifactRef(
                    artifact_id="dup",
                    kind="segmentation",
                    uri="https://example.invalid/one",
                ),
                ArtifactRef(
                    artifact_id="dup",
                    kind="segmentation",
                    uri="https://example.invalid/two",
                ),
            ]
        )


class BlockingBackend:
    name = "blocking"
    stage = "segmentation"

    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()

    def available(self) -> bool:
        return True

    def run(self, request, bundle, workdir: Path, parameters):
        self.started.set()
        if not self.release.wait(timeout=10):
            raise RuntimeError("stress test release timeout")
        path = workdir / "blocking.nii.gz"
        path.write_bytes(b"blocking")
        return StageOutput(
            artifacts=[
                ArtifactRef(
                    artifact_id="blocking-seg",
                    kind="segmentation",
                    uri=str(path),
                    sha256=file_sha256(path),
                    size_bytes=path.stat().st_size,
                )
            ]
        )


class UnverifiedBackend:
    name = "unverified"
    stage = "segmentation"

    def __init__(self) -> None:
        self.calls = 0

    def available(self) -> bool:
        return True

    def run(self, request, bundle, workdir: Path, parameters):
        self.calls += 1
        path = workdir / "unverified.nii.gz"
        path.write_bytes(f"run-{self.calls}".encode())
        return StageOutput(
            artifacts=[
                ArtifactRef(
                    artifact_id="unverified-seg",
                    kind="segmentation",
                    uri=str(path),
                )
            ]
        )


class SourceCollisionBackend:
    name = "collision"
    stage = "segmentation"

    def available(self) -> bool:
        return True

    def run(self, request, bundle, workdir: Path, parameters):
        return StageOutput(
            artifacts=[
                ArtifactRef(
                    artifact_id="raw",
                    kind="segmentation",
                    uri="https://example.invalid/collision",
                )
            ]
        )


def _request(tmp_path: Path) -> AnatomyRequest:
    return AnatomyRequest(
        subject_id="S1",
        acquisition=ImagingAcquisition(
            subject_id="S1",
            study_id="ST1",
            acquisition_id="A1",
            modality="CMR",
            source=ArtifactRef(
                artifact_id="raw",
                kind="nifti_image",
                uri="https://example.invalid/raw.nii.gz",
            ),
        ),
        output_root=str(tmp_path),
    )


def _plan(backend: str = "stress") -> PipelinePlan:
    return PipelinePlan(
        stages=["segmentation"],
        backends={"segmentation": backend},
    )


def _sidecar(tmp_path: Path) -> Path:
    return tmp_path / "S1" / "A1" / "stage-segmentation.json"


def test_valid_resume_does_not_rerun_backend(tmp_path: Path) -> None:
    backend = CountingSegmentationBackend()
    executor = PipelineExecutor()
    executor.register(backend)

    first = executor.execute(_request(tmp_path), _plan())
    second = executor.execute(_request(tmp_path), _plan())

    assert backend.calls == 1
    assert first.bundle_fingerprint == second.bundle_fingerprint
    assert first.artifacts[-1].sha256 == second.artifacts[-1].sha256


def test_repeated_resume_is_stable(tmp_path: Path) -> None:
    backend = CountingSegmentationBackend()
    executor = PipelineExecutor()
    executor.register(backend)

    fingerprints = {
        executor.execute(_request(tmp_path), _plan()).bundle_fingerprint
        for _ in range(25)
    }
    assert backend.calls == 1
    assert len(fingerprints) == 1


def test_malformed_sidecar_triggers_recomputation(tmp_path: Path) -> None:
    backend = CountingSegmentationBackend()
    executor = PipelineExecutor()
    executor.register(backend)
    executor.execute(_request(tmp_path), _plan())

    _sidecar(tmp_path).write_text("{not-json", encoding="utf-8")
    executor.execute(_request(tmp_path), _plan())
    assert backend.calls == 2
    json.loads(_sidecar(tmp_path).read_text(encoding="utf-8"))


def test_missing_local_artifact_triggers_recomputation(tmp_path: Path) -> None:
    backend = CountingSegmentationBackend()
    executor = PipelineExecutor()
    executor.register(backend)
    first = executor.execute(_request(tmp_path), _plan())

    Path(first.artifacts[-1].uri).unlink()
    executor.execute(_request(tmp_path), _plan())
    assert backend.calls == 2


def test_modified_local_artifact_triggers_recomputation(tmp_path: Path) -> None:
    backend = CountingSegmentationBackend()
    executor = PipelineExecutor()
    executor.register(backend)
    first = executor.execute(_request(tmp_path), _plan())

    Path(first.artifacts[-1].uri).write_bytes(b"tampered")
    second = executor.execute(_request(tmp_path), _plan())
    assert backend.calls == 2
    assert Path(second.artifacts[-1].uri).read_bytes() == b"segmentation-run-2"


def test_tampered_sidecar_output_ids_trigger_recomputation(tmp_path: Path) -> None:
    backend = CountingSegmentationBackend()
    executor = PipelineExecutor()
    executor.register(backend)
    executor.execute(_request(tmp_path), _plan())

    path = _sidecar(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["record"]["output_artifact_ids"] = ["attacker-controlled"]
    path.write_text(json.dumps(payload), encoding="utf-8")

    executor.execute(_request(tmp_path), _plan())
    assert backend.calls == 2


def test_invalid_restored_qc_triggers_recomputation(tmp_path: Path) -> None:
    backend = CountingSegmentationBackend()
    executor = PipelineExecutor()
    executor.register(backend)
    executor.execute(_request(tmp_path), _plan())

    path = _sidecar(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["qc"] = {
        "passed": True,
        "checks": {"bad": False},
        "metrics": {},
        "warnings": [],
        "errors": [],
        "artifact_id": None,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    executor.execute(_request(tmp_path), _plan())
    assert backend.calls == 2


@pytest.mark.parametrize("backend_cls", [DuplicateOutputBackend, SourceCollisionBackend])
def test_duplicate_artifact_ids_are_failed_and_recorded(
    tmp_path: Path,
    backend_cls,
) -> None:
    executor = PipelineExecutor()
    backend = backend_cls()
    executor.register(backend)

    with pytest.raises(ValueError, match="duplicate artifact IDs"):
        executor.execute(_request(tmp_path), _plan(backend.name))

    payload = json.loads(_sidecar(tmp_path).read_text(encoding="utf-8"))
    assert payload["record"]["status"] == "error"
    assert payload["artifacts"] == []


def test_stage_fingerprint_is_input_order_independent() -> None:
    first = ArtifactRef(
        artifact_id="a",
        kind="segmentation",
        uri="https://example.invalid/a",
        sha256="a" * 64,
    )
    second = ArtifactRef(
        artifact_id="b",
        kind="surface_mesh",
        uri="https://example.invalid/b",
        sha256="b" * 64,
    )
    one = stage_fingerprint("qc", "native", [first, second], {"x": 1})
    two = stage_fingerprint("qc", "native", [second, first], {"x": 1})
    assert one == two


def test_stage_fingerprint_changes_with_artifact_digest() -> None:
    first = ArtifactRef(
        artifact_id="a",
        kind="segmentation",
        uri="https://example.invalid/a",
        sha256="a" * 64,
    )
    changed = first.model_copy(update={"sha256": "b" * 64})
    assert stage_fingerprint("qc", "native", [first], {}) != stage_fingerprint(
        "qc",
        "native",
        [changed],
        {},
    )


def test_concurrent_same_workdir_fails_fast_instead_of_racing(
    tmp_path: Path,
) -> None:
    executor = PipelineExecutor()
    backend = BlockingBackend()
    executor.register(backend)
    request = _request(tmp_path)
    plan = _plan(backend.name)

    errors: list[Exception] = []

    def first_run() -> None:
        try:
            executor.execute(request, plan)
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    thread = threading.Thread(target=first_run)
    thread.start()
    assert backend.started.wait(timeout=5)

    try:
        with pytest.raises(RuntimeError, match="Another CardiAnatomy pipeline"):
            executor.execute(request, plan)
    finally:
        backend.release.set()
        thread.join(timeout=10)

    assert not thread.is_alive()
    assert not errors


def test_sidecar_output_metadata_tampering_forces_recompute(
    tmp_path: Path,
) -> None:
    backend = CountingSegmentationBackend()
    executor = PipelineExecutor()
    executor.register(backend)
    executor.execute(_request(tmp_path), _plan())

    path = _sidecar(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["artifacts"][0]["metadata"]["tampered"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")

    executor.execute(_request(tmp_path), _plan())
    assert backend.calls == 2


def test_sidecar_valid_qc_tampering_forces_recompute(tmp_path: Path) -> None:
    backend = CountingSegmentationBackend()
    executor = PipelineExecutor()
    executor.register(backend)
    executor.execute(_request(tmp_path), _plan())

    path = _sidecar(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["qc"] = {
        "passed": True,
        "checks": {"geometry": True},
        "metrics": {},
        "warnings": [],
        "errors": [],
        "artifact_id": None,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    executor.execute(_request(tmp_path), _plan())
    assert backend.calls == 2


def test_legacy_sidecar_without_output_fingerprint_is_not_reused(
    tmp_path: Path,
) -> None:
    backend = CountingSegmentationBackend()
    executor = PipelineExecutor()
    executor.register(backend)
    executor.execute(_request(tmp_path), _plan())

    path = _sidecar(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("output_fingerprint")
    path.write_text(json.dumps(payload), encoding="utf-8")

    executor.execute(_request(tmp_path), _plan())
    assert backend.calls == 2


def test_unverified_stage_outputs_are_never_resumed(tmp_path: Path) -> None:
    backend = UnverifiedBackend()
    executor = PipelineExecutor()
    executor.register(backend)
    plan = _plan(backend.name)

    executor.execute(_request(tmp_path), plan)
    executor.execute(_request(tmp_path), plan)
    assert backend.calls == 2


def test_stage_fingerprint_changes_with_semantic_artifact_metadata() -> None:
    artifact = ArtifactRef(
        artifact_id="a",
        kind="segmentation",
        uri="https://example.invalid/a",
        sha256="a" * 64,
        frame_id="frame-a",
        metadata={"phase": "ED"},
    )
    changed_frame = artifact.model_copy(update={"frame_id": "frame-b"})
    changed_metadata = artifact.model_copy(update={"metadata": {"phase": "ES"}})

    baseline = stage_fingerprint("qc", "native", [artifact], {})
    assert baseline != stage_fingerprint("qc", "native", [changed_frame], {})
    assert baseline != stage_fingerprint("qc", "native", [changed_metadata], {})
