from __future__ import annotations
import argparse
import json
import sys
from cardianatomy.scan_to_twin import run_biv_me_scan_to_twin

def main(argv=None):
    parser = argparse.ArgumentParser(description="Run local cine-CMR model construction.")
    parser.add_argument("dicom_case")
    parser.add_argument("--biv-me-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--python-executable", default="python")
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--review-mode", choices=["manual", "adaptive", "automatic"], default="adaptive")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=int, default=43200)
    parser.add_argument("--analysis-timeout-seconds", type=int, default=1800)
    parser.add_argument("--skip-metrics", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_biv_me_scan_to_twin(
            args.dicom_case, biv_me_root=args.biv_me_root, output_root=args.output_root,
            python_executable=args.python_executable, case_id=args.case_id,
            review_mode=args.review_mode, workers=args.workers,
            timeout_seconds=args.timeout_seconds,
            analysis_timeout_seconds=args.analysis_timeout_seconds,
            calculate_metrics=not args.skip_metrics,
        )
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0 if result["workflow_status"] == "completed" else 1
    except (ValueError, TypeError, KeyError, OSError, RuntimeError, ImportError) as exc:
        print(json.dumps({"error": str(exc)}, file=sys.stderr))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
