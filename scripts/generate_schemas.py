from __future__ import annotations

import argparse
import json
from pathlib import Path

from cardianatomy.models import AnatomyBundle, AnatomyRequest, PipelinePlan


SCHEMAS = {
    "anatomy-bundle-2.0.0.schema.json": AnatomyBundle.model_json_schema(),
    "anatomy-request-2.0.0.schema.json": AnatomyRequest.model_json_schema(),
    "pipeline-plan-2.0.0.schema.json": PipelinePlan.model_json_schema(),
}


def payload(schema: dict) -> str:
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "schemas"
    root.mkdir(exist_ok=True)
    packaged = root.parent / "src/cardianatomy/schemas"
    packaged.mkdir(exist_ok=True)
    stale = []
    for directory, filename, schema in (
        (directory, filename, schema)
        for directory in (root, packaged)
        for filename, schema in SCHEMAS.items()
    ):
        path = directory / filename
        if args.check:
            if not path.exists():
                stale.append(str(path.relative_to(root.parent)))
                continue
            try:
                current = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                stale.append(str(path.relative_to(root.parent)))
                continue
            if current != schema:
                stale.append(str(path.relative_to(root.parent)))
        else:
            path.write_text(payload(schema), encoding="utf-8")
    if stale:
        raise SystemExit("stale schemas: " + ", ".join(stale))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
