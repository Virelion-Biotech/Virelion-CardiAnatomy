from __future__ import annotations

from typing import Any

from .models import AnatomyBundle, AnatomyRequest
from .service import CardiAnatomyService


class AnatomyAPI:
    """Framework-agnostic facade intended for HeartTwin native integration."""

    capabilities = ("anatomy.build", "anatomy.validate", "anatomy.health")

    def __init__(self, service: CardiAnatomyService | None = None) -> None:
        self.service = service or CardiAnatomyService()

    def health(self) -> dict[str, Any]:
        return {
            "service": "CardiAnatomy",
            "status": "ok",
            "backends": self.service.backends(),
            "capabilities": list(self.capabilities),
        }

    def build(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = AnatomyRequest.model_validate(payload)
        return self.service.build(request).model_dump(mode="json")

    def validate(self, payload: dict[str, Any]) -> dict[str, Any]:
        bundle = AnatomyBundle.model_validate(payload)
        self.service.require_ready(bundle)
        return {
            "ready": True,
            "subject_id": bundle.subject_id,
            "contract_version": bundle.contract_version,
        }
