# CardiAnatomy 0.5.0 CPU validation audit — 2026-10-07

## Verified software result

Baseline: 236 tests passed, 79% statement coverage (rounded).
Five new product regressions failed before repair: stale unhashed-source cache,
higher-order mesh linearization, mutable-QC bypass, volume-QC approval of an
unchecked surface, and missing shape-quality evidence passing a threshold.

Final local verification: **261 tests passed**, **87.94% statement coverage**,
with warnings treated as errors. Ruff and schema synchronization passed.
Source and wheel builds succeeded. The wheel was installed into an isolated
virtual environment; core commands ran without imaging dependencies, and the
native build/validate/report and pinned-data validation workflows ran after
installing the CPU `io` and `validation` extras. Wheel source bytes were compared
to the audited source. The source distribution includes the scripts, examples,
compressed data, provenance manifest and notices needed to repeat these checks.

## External geometry fixtures

Two unchanged public fixtures from `ccmim/CardioMesh`, pinned to revision
`211710420e3504563fe18ba73980e2663ce68fc6`, are stored with their repository MIT
notice. See `../data/manifest.json` for exact source URLs, SHA-256 values and the
license limitation. These are negative geometry controls, not held-out clinical
segmentation or reconstruction benchmarks.

| Fixture | Points | Triangles | Observed issue | Expected result |
|---|---:|---:|---|---|
| LV epi/endo mesh | 4,396 | 8,794 | 14 duplicate cells; 15 nonmanifold edges | QC FAIL |
| Legacy biventricular POLYDATA | 6,155 | 12,055 | Multiple components; 251 boundary edges | Watertight QC FAIL |

The original files were not cleaned or relabeled to obtain passing QC.
The validation harness asserts checksum integrity, format support, counts and
rejection. Its overall PASS means those computational expectations passed;
it does **not** mean either mesh became simulation-ready.

## Computational controls

`results.json` retains dataset diagnostics, package/dependency versions, source
module SHA-256 values and the harness hash. Analytical controls include unit
tetrahedron volume 1/6, its consistently oriented closed-surface volume 1/6,
cubic scaling over 1e-4 to 1e4, known Dice 0.5/Jaccard 1/3, zero self-distance,
and recovery of a known rigid displacement on sampled public mesh vertices.
Tests compare the exact CPU KD-tree backend to bounded brute-force distances
and exercise 10,000-point sets. Pipeline tests exercise ingest, QC, atomic
export, finalized output, native resume and downstream mechanics gating.
Numerical units remain the input coordinate units; no patient volume claim is
inferred from arbitrary mesh coordinates.

## Hygiene and compatibility changes

- Local input bytes and complete request semantics contribute to cache keys;
  declared file-hash mismatches fail instead of being silently refreshed.
- Nonobject, malformed or nonstandard cache sidecars trigger recomputation.
- Public JSON inputs reject duplicate keys and NaN/Infinity. JSON/HTML outputs
  use atomic per-file replacement. Concurrent workdir locking is retained.
- Readiness revalidates mutable model contents and respects scoped QC artifact IDs.
  Legacy unscoped QC remains supported; its scope depends on the producer.
- Higher-order curved element QC is rejected instead of discarding midside nodes.
- Surface orientation is checked; volume measurement rejects open/nonmanifold/
  inconsistently oriented surfaces. Missing shape-quality measurements fail a
  requested quality gate.
- Float labels at the int64 boundary and affine normalization overflow fail explicitly.
- Subject/acquisition identifiers are portable across Linux and Windows; local
  Windows drive paths are recognized correctly.
- Schemas ship inside the wheel and both schema copies are checked for drift.
- Legacy ASCII triangular POLYDATA is geometry-only and bounded to 64 MiB;
  binary/nontriangular POLYDATA and curved-element QC remain unsupported.

## Remaining limits

This release is a tested anatomy infrastructure package, not a complete native
patient-image reconstruction system. Segmentation, template fitting, volume
meshing and validated LDRB methods still require the declared external tools,
weights, atlases and their own validation. Native QC checks one selected mesh;
passing its volume QC does not establish surface, valve-tag or boundary-condition
adequacy. Readiness is a software contract, not anatomical or clinical truth.
`requested_outputs` describes intent; callers must choose the required readiness
`--target`. Reference metric arrays must already be correctly aligned and share
units/grid; metrics cannot establish those assumptions independently.

The native export stage emits a pre-export snapshot. The CLI's `--output` is the
complete finalized bundle. Fingerprints include artifact paths and stage history;
independent builds on different machines are not guaranteed identical bundle
fingerprints. No live downstream solver run or independent patient-reference
accuracy/clinical validation is established by this audit.

Publication: audited source and fixtures committed to main as `4e7099ba44a2808d8c477855c7d0f5741a1e0838`. GitHub CI repeats software, packaged-schema, CPU data and seeded stress checks for the published revision.
