from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .models import AnatomyBundle, AnatomyRequest, ArtifactRef, GeometryQC, StageName


class AnatomyBackend(Protocol):
    """Monolithic backend contract kept for compatibility and external pipelines."""

    name: str

    def available(self) -> bool: ...

    def build(self, request: AnatomyRequest) -> AnatomyBundle: ...


@dataclass
class StageOutput:
    artifacts: list[ArtifactRef] = field(default_factory=list)
    qc: GeometryQC | None = None
    warnings: list[str] = field(default_factory=list)


class AnatomyStageBackend(Protocol):
    name: str
    stage: StageName

    def available(self) -> bool: ...

    def run(
        self,
        request: AnatomyRequest,
        bundle: AnatomyBundle,
        workdir: Path,
        parameters: dict,
    ) -> StageOutput: ...


class BackendUnavailable(RuntimeError):
    pass
