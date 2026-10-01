from __future__ import annotations

from typing import Any

import numpy as np

from .fibers import reference_rule_based_microstructure
from .integrations import tool_catalog
from .models import AnatomyBundle, AnatomyRequest, FiberAngleProfile, ScarThresholdSpec
from .qc import qc_from_inspection
from .scar import classify_scalar_scar, scar_fractions
from .service import CardiAnatomyService


class AnatomyAPI:
    """Framework-agnostic facade intended for HeartTwin native integration."""

    capabilities = (
        "anatomy.health",
        "anatomy.build",
        "anatomy.validate",
        "anatomy.tools",
        "anatomy.microstructure.reference",
        "anatomy.scar.classify",
    )

    def __init__(self, service: CardiAnatomyService | None = None) -> None:
        self.service = service or CardiAnatomyService()

    def health(self) -> dict[str, Any]:
        return {
            "service": "CardiAnatomy",
            "status": "ok",
            "contract_version": "2.0.0",
            "backends": self.service.backends(),
            "capabilities": list(self.capabilities),
        }

    def tools(self) -> dict[str, Any]:
        return {
            "tools": [
                {
                    "tool_id": item.tool_id,
                    "project": item.project,
                    "license": item.license_name,
                    "license_class": item.license_class,
                    "default_allowed": item.default_allowed,
                    "purpose": list(item.purpose),
                    "url": item.url,
                    "notes": item.notes,
                }
                for item in tool_catalog()
            ]
        }

    def build(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = AnatomyRequest.model_validate(payload)
        return self.service.build(request).model_dump(mode="json")

    def validate(self, payload: dict[str, Any]) -> dict[str, Any]:
        target = str(payload.get("target", "baseline"))
        raw_bundle = payload.get("bundle", payload)
        bundle = AnatomyBundle.model_validate(raw_bundle)
        self.service.require_ready(bundle, target=target)
        return {
            "ready": True,
            "target": target,
            "subject_id": bundle.subject_id,
            "contract_version": bundle.contract_version,
            "bundle_fingerprint": bundle.bundle_fingerprint,
        }

    def reference_microstructure(self, payload: dict[str, Any]) -> dict[str, Any]:
        profile = FiberAngleProfile.model_validate(payload.get("profile", {}))
        fiber, sheet, normal = reference_rule_based_microstructure(
            np.asarray(payload["circumferential"], dtype=float),
            np.asarray(payload["longitudinal"], dtype=float),
            np.asarray(payload["transmural_coordinate"], dtype=float),
            profile,
        )
        return {
            "method": "cardianatomy.reference_rule_based_microstructure",
            "validation_status": "integration_reference",
            "fiber": fiber.tolist(),
            "sheet": sheet.tolist(),
            "sheet_normal": normal.tolist(),
        }

    def scar_classify(self, payload: dict[str, Any]) -> dict[str, Any]:
        spec = ScarThresholdSpec.model_validate(payload["spec"])
        labels = classify_scalar_scar(np.asarray(payload["values"], dtype=float), spec)
        return {
            "method": spec.method,
            "labels": labels.tolist(),
            "fractions": scar_fractions(labels),
            "validation_status": "threshold_application_only",
        }

    @staticmethod
    def qc(inspection) -> dict[str, Any]:
        return qc_from_inspection(inspection).model_dump(mode="json")
