from __future__ import annotations

import argparse
import json
from pathlib import Path

from .api import AnatomyAPI
from .models import AnatomyBundle
from .service import CardiAnatomyService


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(prog="cardianatomy")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Report package and backend availability")
    validate = sub.add_parser("validate", help="Validate an AnatomyBundle JSON file")
    validate.add_argument("bundle")
    args = parser.parse_args()

    api = AnatomyAPI(CardiAnatomyService())
    if args.command == "doctor":
        print(json.dumps(api.health(), indent=2, sort_keys=True))
        return 0

    bundle = AnatomyBundle.model_validate(_load_json(args.bundle))
    CardiAnatomyService.require_ready(bundle)
    print(json.dumps({"ready": True, "subject_id": bundle.subject_id}, indent=2))
    return 0
