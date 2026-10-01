# Virelion-CardiAnatomy

Patient-specific cardiac anatomy layer for the Virelion HeartTwin stack.

CardiAnatomy defines the contracts and orchestration needed to turn imaging-derived inputs into traceable cardiac geometry artifacts: segmentation references, surfaces, volumetric meshes, coordinate systems, myocardial microstructure, scar/border-zone labels, spatial registrations, and geometry quality-control results.

## Scope

CardiAnatomy owns:
- imaging-study and acquisition identity;
- anatomical artifact references and content hashes;
- segmentation/surface/mesh/microstructure/scar contracts;
- coordinate-frame and registration metadata;
- geometry QC and fail-closed readiness checks;
- backend interfaces for future CMR/CT segmentation and meshing engines;
- a stable Python/CLI surface for HeartTwin.

CardiAnatomy does **not** invent anatomy from incomplete data. The initial package is an integration skeleton: scientific backends must explicitly produce artifacts and validation evidence before a bundle can be marked ready for downstream personalization.

## Architecture

```text
DICOM / derived imaging
        |
        v
 acquisition identity
        |
        v
 segmentation artifact
        |
        v
 surfaces -> volumetric mesh
        |
        +-> coordinate systems / fibers
        +-> scar / border zone
        +-> registrations
        |
        v
     geometry QC
        |
        v
 AnatomyBundle -> HeartTwin / CardiEP / CardiMech / CardiFlow
```

## Quick start

```bash
python -m pip install -e '.[dev]'
pytest -q
cardianatomy doctor
```

## Scientific boundary

Passing schema or QC checks establishes software consistency only. It does not establish segmentation accuracy, anatomical fidelity, solver suitability, or clinical validity. Patient-specific claims require validated imaging pipelines, reviewed registrations, independent QC, and appropriate external validation.

## License

AGPL-3.0-or-later.
