# Colab numerical run and watertight QC correction

`12_CardiAnatomy_Numerical_v1_results.zip` completed its declared scope in
1.32968 seconds with return code zero. The worker reports `NUMERICAL_ONLY`;
the harness reports `PASS`. All 17 unique archive members are retained under
[`colab_numerical_2026_10_15/original`](colab_numerical_2026_10_15/original/).
All 16 artifact hashes, launcher hashes, and canonical protocol identity match.
The 110-file source snapshot matches pinned commit
`0bd310ac9408ba208d5248804ba07a053c988e21`. All 35 implementation module hashes
and the harness hash matched the checkout before correction. Supplied launchers
are retained as inert `.py.txt` copies and were not executed during this review.

## What passed

The original harness was independently rerun locally before modifying QC.
Dataset diagnostics, analytic controls, original source hashes and harness hash
reproduced (floating metrics compared with relative tolerance 1e-12 and absolute
tolerance 1e-14). Fixture bytes are already pinned in the repository and their
decompressed hashes were verified by the harness; this notebook does not download
an independent patient cohort. Its empty `input_receipts` is consistent with
using repository fixtures.

| Control | Result | Meaning |
|---|---|---|
| Unit tetrahedron / closed surface | Volume 1/6; cubic scaling checks pass | Analytical geometry |
| Toy label arrays | Dice 0.5; Jaccard 1/3 | Metric arithmetic |
| Identical point sets | Zero distances | Identity control |
| Known translated mesh vertices | Rigid registration residual below 1e-10 | Paired-landmark numerical control |
| LV public fixture | 14 duplicate cells, 15 nonmanifold edges; QC fails | Expected negative control |
| Biventricular public fixture | Two components, 251 boundary edges; QC fails | Expected negative control |

The overall harness PASS means the expected controls passed. It does not mean
either public fixture passed geometric QC or became simulation-ready.

## Corrected defect

The original LV report had `watertight=true` because that check used only the
absence of boundary edges. It ignored nonmanifold edges, even though the separate
`manifold_edges` check correctly failed and overall QC rejected the mesh.
Missing counts were also coerced to zero, allowing unknown topology to produce
a passing watertight flag.

`manifold_edges` now requires a measured nonmanifold count of zero.
With `require_watertight=True`, `watertight` requires both measured boundary and
nonmanifold counts to equal zero. This checks closed edge incidence; it is not
a self-intersection test or proof of anatomical correctness. Other QC checks
still enforce orientation, duplicates, degeneracy and connectedness separately.
Callers supplying custom partial inspections must provide topology measurements
to establish these checks; unknown measurements no longer imply success.

Four new regression cases failed before correction: two closed shells sharing
an edge, and three combinations of missing topology counts. All now pass, and
a clean closed-manifold positive control retains its passing QC. The numerical
harness explicitly asserts that both negative fixtures have `watertight=false`.

The corrected LV report retains the same geometry and failing overall QC, now
with a false watertight flag and an additional `watertight` error. The biventricular
diagnostics and analytical results remain unchanged. No source mesh was repaired,
deduplicated, closed, or relabeled. Original and corrected reports are separate:
`baseline_reproduction.json` and `corrected_reproduction.json` accompany the
untouched original payload. `REVIEW.json` and `PAYLOAD_SHA256.json` record checks.

## Verification and remaining limits

268 local tests passed with warnings treated as errors and 86.73% statement
coverage. Ruff, schema drift checks and the CPU harness passed.

```bash
python -m pip install -e '.[dev,validation]'
python -m pytest -q --cov=cardianatomy --cov-fail-under=85 -W error
python scripts/generate_schemas.py --check
python scripts/run_cpu_validation.py --output /tmp/anatomy-cpu-validation.json
```

No notebook execution repair is required. The numerical run contains no patient
segmentation, reconstruction, scar or fiber reference truth. Its rigid-displacement
control does not establish real-world registration accuracy. External backends,
independent labeled acquisitions and intended-scale downstream solver checks
remain necessary for anatomical reconstruction qualification. These missing
scientific endpoints cannot be resolved from this export.
