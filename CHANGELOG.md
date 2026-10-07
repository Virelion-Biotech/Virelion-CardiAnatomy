# Changelog

## 0.5.0 — 2026-10-07

- Completed CLI pipeline build and reference metric operations with structured errors.
- Added source-content/request cache invalidation, strict atomic JSON artifacts,
  and portable filesystem identifiers.
- Scoped QC readiness to inspected geometry and revalidated mutable contracts.
- Rejected unsupported curved elements, missing quality measurements, open/
  inconsistent surfaces for volume, int64 label overflow, and affine overflow.
- Added bounded ASCII triangular POLYDATA ingestion and optional exact CPU KD-tree metrics.
- Packaged schemas and preserved pinned public cardiac meshes as negative QC controls.
- Added cross-platform end-to-end tests, CPU evidence and clean-wheel verification.

## 0.4.0 — 2026-10-02

### Anatomy and motion

- Added segmentation-derived cine chamber-volume curves and ED/ES selection.
- Added stroke-volume, ejection-fraction, and cine dynamic-range summaries.
- Added dense-correspondence mesh comparison with exact connectivity checks and hashes.
- Added 3D+t mesh-motion summaries with reference-phase displacement, inter-phase motion,
  vertex path length, and cyclic-closure diagnostics.
- Expanded canonical whole-heart structure names for atrial/ventricular myocardium,
  pulmonary veins, venae cavae, septum, and left atrial appendage.

### Geometry and coordinate safety

- Added validated affine composition, inversion, and round-trip diagnostics.
- Added paired-landmark rigid registration with residual reporting.
- Added solver-neutral surface/volume measurement helpers.
- Added tetrahedral mean-ratio and scaled-Jacobian shape-quality metrics.
- Added optional normalized shape-quality gates to native mesh QC.

### Pipeline and reproducibility

- Fixed resumability so skipped stages restore complete output artifacts and QC.
- Added native ingest, geometry-QC, and export stages.
- Added verified existing-artifact stages rather than guessing external output locations.
- Added toolchain manifests for binaries, containers, model weights, atlases, hashes,
  versions, and asset licenses.
- Added a unified safe external command runner using argument arrays and `shell=False`.
- Upgraded the HTML report into an anatomy/provenance dossier.

### External ecosystem

- Added executable adapters/builders for nnU-Net, biv-me, BiV volumetric meshing,
  MyoMesh, cardiac-geometriesx, fenicsx-ldrb, and Meshtool workflows.
- Added explicit command builders for MorphiNetV2 and Bi-PT learned inference.
- Reviewed CEMRG HeartBuilder, MorphiNetV2, Bi-PT, HeartVolMesh, MeshHeart, TetHeart,
  BiventricularSSM, AugmentA, atrialmtk, openCARP, and related geometry stacks.
- Corrected upstream license handling; unresolved-license projects remain fail-closed.

### HeartTwin

- CardiAnatomy is a required native service in the full-stack integration workflow.
- Added HeartTwin dispatch for anatomy presets, registration, geometry measurements,
  manifests, cine phases, affine transforms, correspondence, and 4D motion.
- HeartTwin pins a verified CardiAnatomy Git revision in `requirements-services.txt`.

## 0.3.0 — 2026-10-02

Initial expansion from the v0.2 anatomy-contract scaffold into a runnable staged pipeline
with external-tool cataloging, native QC/export, rigid registration, canonical presets,
and HeartTwin-native service integration.
