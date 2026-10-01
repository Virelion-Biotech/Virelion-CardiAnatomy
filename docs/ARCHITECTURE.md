# CardiAnatomy architecture

## Design goal

CardiAnatomy is the canonical anatomy layer of HeartTwin. It should be stable even while segmentation networks, meshing tools, fiber generators, and registration algorithms change.

The core therefore owns **contracts, orchestration, provenance, coordinate semantics, QC, and readiness**. Heavy scientific engines live behind adapters.

## Canonical stages

1. `ingest` — validate and fingerprint source imaging/geometry.
2. `view_selection` — select/reject cine views or image series.
3. `phase_harmonization` — align SAX/LAX or multimodal temporal phases.
4. `segmentation` — produce labeled image masks.
5. `contours` — derive contours, guidepoints, and anatomical landmarks.
6. `surface_fit` — fit a parametric/statistical anatomical model where appropriate.
7. `surface_mesh` — produce labeled surfaces.
8. `volume_mesh` — produce solver-ready volumetric discretization.
9. `coordinates` — UVC/UAC or other anatomical coordinates.
10. `microstructure` — fibers, sheets, sheet-normal fields.
11. `scar` — map scar/core/border-zone labels or scalar fields.
12. `registration` — align imaging, EAM, anatomy, and solver frames.
13. `qc` — topology, geometry, finite values, orientation, provenance, registration quality.
14. `export` — emit solver-specific representations without making them canonical.

The stages can be skipped when upstream validated artifacts already exist.

## Artifact-first design

Large geometry is not serialized into HeartTwin JSON. `ArtifactRef` stores stable identity, URI, optional digest, coordinate frame, producer, lineage, and metadata. This keeps the canonical state small while retaining reproducibility.

## Multiple readiness gates

A single `ready` flag is inadequate. CardiEP requires microstructure/coordinates that CardiFlow may not, while some surface analyses do not require a volume mesh. `AnatomyBundle` therefore exposes separate readiness properties.

## Coordinate safety

Every spatial artifact should eventually carry a `frame_id`. Registrations connect frames explicitly. DICOM LPS and NIfTI RAS are treated as distinct conventions; coordinate transforms must be represented, not assumed.

## Scientific backend policy

Backends are selected explicitly. No backend may silently fabricate missing anatomical data. If required software, model weights, landmarks, or inputs are absent, the stage must fail or remain unresolved.
