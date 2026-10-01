from __future__ import annotations

from typing import Any

import numpy as np

from .fibers import reference_rule_based_microstructure
from .geometry import (
    bounding_box,
    closed_surface_signed_volume,
    tetrahedral_volume,
    triangle_surface_area,
)
from .integrations import tool_catalog
from .manifests import ToolchainManifest, audit_manifest_licenses
from .models import (
    AnatomyBundle,
    AnatomyRequest,
    DicomSeriesSummary,
    FiberAngleProfile,
    ScarThresholdSpec,
)
from .presets import preset_catalog
from .qc import qc_from_inspection
from .registration import estimate_rigid_transform
from .scar import classify_scalar_scar, scar_fractions
from .segmentation import segmentation_qc
from .series import rank_series_for_cine
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
        "anatomy.presets",
        "anatomy.registration.rigid",
        "anatomy.geometry.measure",
        "anatomy.manifest.audit",
        "anatomy.series.rank",
        "anatomy.segmentation.qc",
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

    def presets(self) -> dict[str, Any]:
        return {
            "presets": {
                name: plan.model_dump(mode="json")
                for name, plan in preset_catalog().items()
            }
        }

    def registration_rigid(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = estimate_rigid_transform(
            np.asarray(payload["source_points"], dtype=float),
            np.asarray(payload["target_points"], dtype=float),
            allow_reflection=bool(payload.get("allow_reflection", False)),
        )
        return {
            "matrix": result.matrix.tolist(),
            "rms_error": result.rms_error,
            "max_error": result.max_error,
            "source_centroid": result.source_centroid.tolist(),
            "target_centroid": result.target_centroid.tolist(),
            "method": "paired_landmark_rigid_svd",
        }

    def geometry_measure(self, payload: dict[str, Any]) -> dict[str, Any]:
        points = np.asarray(payload["points"], dtype=float)
        output: dict[str, Any] = {"bounding_box": bounding_box(points)}
        if "triangles" in payload:
            triangles = np.asarray(payload["triangles"], dtype=int)
            output["surface_area"] = triangle_surface_area(points, triangles)
            output["signed_surface_volume"] = closed_surface_signed_volume(
                points, triangles
            )
        if "tetrahedra" in payload:
            output["tetrahedral_volume"] = tetrahedral_volume(
                points,
                np.asarray(payload["tetrahedra"], dtype=int),
            )
        return output

    def manifest_audit(self, payload: dict[str, Any]) -> dict[str, Any]:
        manifest_payload = {
            key: value
            for key, value in payload.items()
            if key != "allow_restricted"
        }
        manifest = ToolchainManifest.model_validate(manifest_payload)
        problems = audit_manifest_licenses(
            manifest,
            allow_restricted=bool(payload.get("allow_restricted", False)),
        )
        finalized = manifest.finalized()
        return {
            "valid": not problems,
            "problems": problems,
            "manifest": finalized.model_dump(mode="json"),
        }

    def series_rank(self, payload: dict[str, Any]) -> dict[str, Any]:
        summaries = [
            DicomSeriesSummary.model_validate(item)
            for item in payload.get("series", [])
        ]
        return {
            "candidates": [
                {
                    "series_uid_sha256": item.series_uid_sha256,
                    "predicted_view": item.predicted_view,
                    "confidence": item.confidence,
                    "reasons": list(item.reasons),
                }
                for item in rank_series_for_cine(summaries)
            ],
            "validation_status": "metadata_heuristic_only",
        }

    def segmentation_qc(self, payload: dict[str, Any]) -> dict[str, Any]:
        required = payload.get("required_labels")
        return segmentation_qc(
            np.asarray(payload["labels"]),
            required_labels=None if required is None else {int(x) for x in required},
            background_label=int(payload.get("background_label", 0)),
        )

    @staticmethod
    def qc(inspection) -> dict[str, Any]:
        return qc_from_inspection(inspection).model_dump(mode="json")
