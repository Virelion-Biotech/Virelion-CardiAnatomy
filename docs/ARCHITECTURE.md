# CardiAnatomy architecture

## Design goal

CardiAnatomy is the canonical anatomy and spatial-geometry layer of HeartTwin. Its public contract should remain stable while segmentation networks, reconstruction models, meshing tools, fiber generators, and registration algorithms change.

The core therefore owns **contracts, orchestration, provenance, coordinate semantics, correspondence semantics, numerical QC, and downstream readiness**. Heavy scientific engines live behind explicit adapters.

## Canonical stages

1. `ingest` — validate/fingerprint source imaging or geometry.
2. `view_selection` — select or reject cine views/series.
3. `phase_harmonization` — align SAX/LAX or multimodal temporal phases.
4. `segmentation` — produce labeled image masks.
5. `contours` — derive contours, guidepoints, or landmarks.
6. `surface_fit` — fit a parametric/statistical/learned anatomical model when appropriate.
7. `surface_mesh` — produce labeled surfaces.
8. `volume_mesh` — produce solver-ready volumetric discretization.
9. `coordinates` — UVC/UAC or other anatomical coordinates.
10. `microstructure` — fibers, sheets, and sheet-normal fields.
11. `scar` — map scalar or labeled scar/core/border-zone fields.
12. `registration` — align imaging, EAM, anatomy, and solver frames.
13. `qc` — geometry, topology, element quality, finite values, orientation, and provenance.
14. `export` — emit solver-specific representations without making them canonical.

Stages may be skipped when validated upstream artifacts already exist. The `external` stage backend verifies a declared artifact, hashes it, and records its provenance instead of guessing where another program wrote its output.

## Artifact-first design

Large geometry is not serialized into HeartTwin JSON. `ArtifactRef` stores stable identity, URI, digest, coordinate frame, producer, lineage, and metadata. This keeps canonical state compact while preserving reproducibility.

External models, atlases, weights, containers, and binaries are recorded through `ToolchainManifest`; software license and asset license are treated separately.

## Correspondence and 4D anatomy

Modern learned mesh methods often preserve point correspondence by deforming a shared template. CardiAnatomy does not assume that property from filenames.

The native correspondence layer can:

- verify equal point indexing;
- compare connectivity exactly and fingerprint it;
- summarize pointwise displacement;
- transfer point data through an explicit index map.

The motion layer treats a 3D+t mesh as an array shaped `(phase, point, xyz)` and summarizes reference-phase displacement, inter-phase motion, per-vertex path length, and optional cyclic-closure error.

**Identical connectivity is not treated as proof of diffeomorphism or absence of self-intersection.**

## Multiple readiness gates

A single `ready` flag is inadequate. CardiEP requires coordinates and microstructure that CardiFlow may not, while some surface workflows do not require a volume mesh. `AnatomyBundle` therefore exposes separate readiness properties for baseline, surface, EP, mechanics, and flow use.

## Coordinate safety

Every spatial artifact should carry a `frame_id` when known. Registrations connect frames explicitly. DICOM LPS and NIfTI RAS are distinct conventions; transforms are represented and validated rather than assumed.

Native affine helpers validate homogeneous transforms, reject singular transforms, compose frame chains in application order, invert them, and support numerical round-trip checks.

## Scientific backend policy

Backends are selected explicitly. No backend may silently fabricate missing anatomy, landmarks, coordinate frames, or acquisition metadata.

Permissively licensed tools may receive adapters. Copyleft tools remain isolated processes unless deliberately integrated under compatible terms. Restricted or unresolved-license tools are fail-closed. Model weights and datasets are always reviewed independently of source-code licenses.

A passing software test or geometry-QC gate is not a biological or clinical validation claim.
