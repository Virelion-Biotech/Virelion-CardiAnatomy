"""CLI for the optional external BiV volumetric meshing pipeline."""
from __future__ import annotations

import argparse
import json
import sys

from .biv_volumetric import _STAGES, run_biv_volumetric_pipeline


def _run(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="cardianatomy-biv-volumetric-run",
        description=(
            "Run cdttk/biv-volumetric-meshing with a fresh workspace, staged logs, "
            "input hashes, and tetrahedral mesh QC."
        ),
    )
    parser.add_argument("--sax", required=True)
    parser.add_argument("--lax-2ch", required=True, dest="lax_2ch")
    parser.add_argument("--lax-3ch", required=True, dest="lax_3ch")
    parser.add_argument("--lax-4ch", required=True, dest="lax_4ch")
    parser.add_argument("--upstream-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument(
        "--stages",
        nargs="+",
        choices=list(_STAGES),
        default=["segmentation", "contour", "surface"],
        help="Sequential stage prefix; default stops after surface generation.",
    )
    parser.add_argument("--subject-id", default="cardianatomy_case")
    parser.add_argument("--instance", type=int, default=2)
    parser.add_argument("--timeframe", type=int)
    parser.add_argument(
        "--nnunet-workspace",
        dest="workspace_dir",
        help="nnU-Net workspace containing the required upstream model assets.",
    )
    parser.add_argument("--carp-bin-dir", help="Separate openCARP binaries directory.")
    parser.add_argument(
        "--allow-restricted-runtime",
        action="store_true",
        help=(
            "Explicitly acknowledge that volumetric/UVC/fiber stages rely on a separately "
            "installed openCARP runtime with independent licensing terms."
        ),
    )
    parser.add_argument(
        "--gpu", action="store_true", help="Use the upstream GPU segmentation path."
    )
    parser.add_argument("--python-executable", default="python")
    parser.add_argument("--timeout-seconds", type=float, default=14_400)
    parser.add_argument(
        "--minimum-points",
        type=int,
        default=500,
        help="Minimum points required before a tetrahedral mesh can pass the artifact guard.",
    )
    parser.add_argument(
        "--minimum-tetrahedra",
        type=int,
        default=1000,
        help="Minimum tetrahedra required before a volume mesh can pass the artifact guard.",
    )
    parser.add_argument(
        "--minimum-shape-quality",
        type=float,
        default=0.05,
        help="Minimum normalized tetrahedral shape metric in [0, 1]; screening only.",
    )
    args = parser.parse_args(argv)

    result = run_biv_volumetric_pipeline(
        {
            "SAX": args.sax,
            "LAX_2CH": args.lax_2ch,
            "LAX_3CH": args.lax_3ch,
            "LAX_4CH": args.lax_4ch,
        },
        upstream_root=args.upstream_root,
        output_root=args.output_root,
        stages=args.stages,
        subject_id=args.subject_id,
        instance=args.instance,
        timeframe=args.timeframe,
        workspace_dir=args.workspace_dir,
        carp_bin_dir=args.carp_bin_dir,
        allow_restricted_runtime=args.allow_restricted_runtime,
        gpu=args.gpu,
        python_executable=args.python_executable,
        timeout_seconds=args.timeout_seconds,
        minimum_points=args.minimum_points,
        minimum_tetrahedra=args.minimum_tetrahedra,
        minimum_shape_quality=args.minimum_shape_quality,
    )
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["status"].startswith("completed") else 1


def main(argv=None) -> int:
    try:
        return _run(argv)
    except (
        ValueError,
        TypeError,
        KeyError,
        OSError,
        RuntimeError,
        ImportError,
        OverflowError,
    ) as exc:
        print(json.dumps({"error": str(exc)}, allow_nan=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
