from __future__ import annotations

from .backends import AnatomyBackend, BackendUnavailable
from .models import AnatomyBundle, AnatomyRequest


class ReadinessError(RuntimeError):
    pass


class CardiAnatomyService:
    """Backend-neutral anatomy service used by HeartTwin and CLI clients."""

    def __init__(self) -> None:
        self._backends: dict[str, AnatomyBackend] = {}

    def register_backend(self, backend: AnatomyBackend) -> None:
        self._backends[backend.name] = backend

    def backends(self) -> list[str]:
        return sorted(self._backends)

    def build(self, request: AnatomyRequest) -> AnatomyBundle:
        if not request.backend:
            raise BackendUnavailable(
                "No anatomy backend selected. Register a validated backend and set request.backend."
            )
        backend = self._backends.get(request.backend)
        if backend is None or not backend.available():
            raise BackendUnavailable(f"Anatomy backend unavailable: {request.backend}")
        bundle = backend.build(request)
        if bundle.subject_id != request.subject_id:
            raise ReadinessError("Backend returned anatomy for a different subject")
        return bundle

    @staticmethod
    def require_ready(bundle: AnatomyBundle) -> AnatomyBundle:
        if not bundle.ready:
            raise ReadinessError(
                "Anatomy bundle is not ready: segmentation, surface mesh, volume mesh, "
                "and passing geometry QC are required."
            )
        return bundle
