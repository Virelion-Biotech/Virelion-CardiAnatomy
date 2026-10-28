from __future__ import annotations
import argparse, json, sys
from cardianatomy.volume_mesh_preflight import validate_volume_mesh_inputs

def main(argv=None):
    parser = argparse.ArgumentParser(description="Preflight four NIfTI cardiac views before volumetric meshing.")
    for key in ("SAX", "LAX_2CH", "LAX_3CH", "LAX_4CH"):
        parser.add_argument("--" + key.lower().replace("_", "-"), required=True, dest=key)
    parser.add_argument("--output-manifest", required=True)
    parser.add_argument("--max-voxels", type=int, default=2_000_000_000)
    args = parser.parse_args(argv)
    try:
        result = validate_volume_mesh_inputs({k:getattr(args,k) for k in ("SAX","LAX_2CH","LAX_3CH","LAX_4CH")},
                                             output_manifest=args.output_manifest, max_voxels=args.max_voxels)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (ValueError, RuntimeError, OSError, ImportError) as exc:
        print(json.dumps({"status":"preflight_failed","error":str(exc)}), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
