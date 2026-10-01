from __future__ import annotations

from .backends import AnatomyBackend, AnatomyStageBackend, BackendUnavailable
from .models import AnatomyBundle, AnatomyRequest, MeshInspection
from .pipeline import PipelineExecutor, bundle_fingerprint


class ReadinessError(RuntimeError):
    pass


class CardiAnatomyService:
    """Backend-neutral anatomy service used by HeartTwin and CLI clients."""

    def __init__(self) -> None:
        self._backends: dict[str, AnatomyBackend] = {}
        self.pipeline = PipelineExecutor()

    def register_backend(self, backend: AnatomyBackend) -> None:
        self._backends[backend.name] = backend

    def register_stage_backend(self, backend: AnatomyStageBackend) -> None:
        self.pipeline.register(backend)

    def backends(self) -> dict[str, object]:
        return {
            "monolithic": sorted(self._backends),
            "staged": self.pipeline.backends(),
        }

    def build(self, request: AnatomyRequest) -> AnatomyBundle:
        if request.plan is not None:
            bundle = self.pipeline.execute(request, request.plan)
        else:
            if not request.backend:
                raise BackendUnavailable(
                    "No anatomy backend selected. Set request.backend or provide "
                    "a staged pipeline plan."
                )
            backend = self._backends.get(request.backend)
            if backend is None or not backend.available():
                raise BackendUnavailable(f"Anatomy backend unavailable: {request.backend}")
            bundle = backend.build(request)
        if bundle.subject_id != request.subject_id:
            raise ReadinessError("Backend returned anatomy for a different subject")
        if not bundle.bundle_fingerprint:
            bundle.bundle_fingerprint = bundle_fingerprint(bundle)
        return bundle

    @staticmethod
    def require_ready(bundle: AnatomyBundle, target: str = "baseline") -> AnatomyBundle:
        readiness = {
            "baseline": bundle.ready,
            "surface": bundle.surface_ready,
            "ep": bundle.ep_ready,
            "mechanics": bundle.mechanics_ready,
            "flow": bundle.flow_ready,
        }
        if target not in readiness:
            raise ValueError(f"Unknown readiness target: {target}")
        if not readiness[target]:
            raise ReadinessError(f"Anatomy bundle is not ready for target={target}")
        return bundle

    @staticmethod
    def inspection_summary(inspection: MeshInspection) -> dict:
        return inspection.model_dump(mode="json")
