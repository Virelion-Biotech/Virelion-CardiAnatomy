from __future__ import annotations

from typing import Protocol

from .models import AnatomyBundle, AnatomyRequest


class AnatomyBackend(Protocol):
    """Backend contract for segmentation/meshing implementations."""

    name: str

    def available(self) -> bool: ...

    def build(self, request: AnatomyRequest) -> AnatomyBundle: ...


class BackendUnavailable(RuntimeError):
    pass
