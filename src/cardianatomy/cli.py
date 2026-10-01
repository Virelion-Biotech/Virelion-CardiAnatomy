from __future__ import annotations

import argparse
import json
from pathlib import Path

from .api import AnatomyAPI
from .io import inspect_dicom_directory, inspect_mesh_file, inspect_nifti
from .models import AnatomyBundle
from .provenance import file_sha256
from .qc import qc_from_inspection
from .report import render_html_report
from .service import CardiAnatomyService


def _load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(prog="cardianatomy")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Report package, tool catalog, and backend availability")
    sub.add_parser("tools", help="Show researched external tool/license catalog")
    sub.add_parser("presets", help="Show canonical pipeline presets")

    validate = sub.add_parser("validate", help="Validate an AnatomyBundle JSON file")
    validate.add_argument("bundle")
    validate.add_argument(
        "--target",
        choices=["baseline", "surface", "ep", "mechanics", "flow"],
        default="baseline",
    )

    hash_cmd = sub.add_parser("hash", help="Compute SHA-256 for an artifact file")
    hash_cmd.add_argument("path")

    inspect_mesh = sub.add_parser("inspect-mesh", help="Inspect VTK/VTU/Gmsh/etc via meshio")
    inspect_mesh.add_argument("path")
    inspect_mesh.add_argument("--require-watertight", action="store_true")
    inspect_mesh.add_argument(
        "--minimum-shape-quality",
        type=float,
        default=None,
        help="Optional normalized minimum cell-shape quality in [0, 1]",
    )

    inspect_dicom = sub.add_parser(
        "inspect-dicom", help="Inspect DICOM geometry metadata without PHI"
    )
    inspect_dicom.add_argument("path")

    inspect_nifti_cmd = sub.add_parser(
        "inspect-nifti", help="Inspect NIfTI shape, spacing, and affine"
    )
    inspect_nifti_cmd.add_argument("path")

    report = sub.add_parser("report", help="Render a self-contained HTML AnatomyBundle report")
    report.add_argument("bundle")
    report.add_argument("output")

    register = sub.add_parser(
        "register-rigid",
        help="Estimate a rigid transform from paired landmark JSON arrays",
    )
    register.add_argument("source")
    register.add_argument("target")

    audit = sub.add_parser("audit-manifest", help="Audit an external toolchain manifest")
    audit.add_argument("manifest")
    audit.add_argument("--allow-restricted", action="store_true")

    cine = sub.add_parser(
        "cine-phases",
        help="Select ED/ES from a JSON chamber-volume curve",
    )
    cine.add_argument("volumes")

    compose = sub.add_parser(
        "compose-affines",
        help="Compose JSON 4x4 affine matrices in application order",
    )
    compose.add_argument("matrices")

    invert = sub.add_parser(
        "invert-affine",
        help="Invert one JSON 4x4 affine matrix",
    )
    invert.add_argument("matrix")

    args = parser.parse_args()
    api = AnatomyAPI(CardiAnatomyService())

    if args.command == "doctor":
        health = api.health()
        health["external_tools"] = api.tools()["tools"]
        _write_json(health)
        return 0
    if args.command == "tools":
        _write_json(api.tools())
        return 0
    if args.command == "presets":
        _write_json(api.presets())
        return 0
    if args.command == "validate":
        bundle = AnatomyBundle.model_validate(_load_json(args.bundle))
        CardiAnatomyService.require_ready(bundle, target=args.target)
        _write_json({"ready": True, "target": args.target, "subject_id": bundle.subject_id})
        return 0
    if args.command == "hash":
        _write_json({"path": args.path, "sha256": file_sha256(args.path)})
        return 0
    if args.command == "inspect-mesh":
        inspection = inspect_mesh_file(args.path)
        qc = qc_from_inspection(
            inspection,
            require_watertight=args.require_watertight,
            minimum_shape_quality=args.minimum_shape_quality,
        )
        _write_json(
            {
                "inspection": inspection.model_dump(mode="json"),
                "qc": qc.model_dump(mode="json"),
            }
        )
        return 0
    if args.command == "inspect-dicom":
        _write_json([item.model_dump(mode="json") for item in inspect_dicom_directory(args.path)])
        return 0
    if args.command == "inspect-nifti":
        _write_json(inspect_nifti(args.path))
        return 0
    if args.command == "report":
        bundle = AnatomyBundle.model_validate(_load_json(args.bundle))
        Path(args.output).write_text(render_html_report(bundle), encoding="utf-8")
        _write_json({"output": args.output})
        return 0
    if args.command == "register-rigid":
        _write_json(
            api.registration_rigid(
                {
                    "source_points": _load_json(args.source),
                    "target_points": _load_json(args.target),
                }
            )
        )
        return 0
    if args.command == "audit-manifest":
        payload = _load_json(args.manifest)
        payload["allow_restricted"] = args.allow_restricted
        _write_json(api.manifest_audit(payload))
        return 0
    if args.command == "cine-phases":
        _write_json(
            api.cine_phases(
                {"volumes_ml": _load_json(args.volumes)}
            )
        )
        return 0
    if args.command == "compose-affines":
        _write_json(
            api.transforms_compose(
                {"matrices": _load_json(args.matrices)}
            )
        )
        return 0
    if args.command == "invert-affine":
        _write_json(
            api.transforms_invert(
                {"matrix": _load_json(args.matrix)}
            )
        )
        return 0
    return 2
