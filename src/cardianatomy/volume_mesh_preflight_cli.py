"""Command-line interface for cardiac volume-mesh input preflight."""

from __future__ import annotations

import argparse
import json
import sys

from cardianatomy.volume_mesh_preflight import validate_volume_mesh_inputs


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Preflight four NIfTI cardiac views before volumetric meshing."
    )
    keys = ("SAX", "LAX_2CH", "LAX_3CH", "LAX_4CH")
    for key in keys:
        parser.add_argument(
            "--" + key.lower().replace("_", "-"),
            required=True,
            dest=key,
        )
    parser.add_argument("--output-manifest", required=True)
    parser.add_argument("--max-voxels", type=int, default=2_000_000_000)
    args = parser.parse_args(argv)

    try:
        views = {key: getattr(args, key) for key in keys}
        result = validate_volume_mesh_inputs(
            views,
            output_manifest=args.output_manifest,
            max_voxels=args.max_voxels,
        )
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (ValueError, RuntimeError, OSError, ImportError) as exc:
        error = {"status": "preflight_failed", "error": str(exc)}
        print(json.dumps(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
