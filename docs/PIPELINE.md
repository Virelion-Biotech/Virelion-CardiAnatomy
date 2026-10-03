# Staged and resumable anatomy pipelines

`PipelinePlan` declares ordered stages, the backend assigned to each stage, and stage-specific parameters.

Each stage receives the immutable request identity, all currently registered artifacts, a dedicated work directory, and explicit parameters. Each successful stage returns typed artifact references and optional QC.

## Deterministic resumability

CardiAnatomy records a deterministic stage fingerprint from:

- stage name;
- backend name;
- input artifact IDs, hashes, URIs, and kinds;
- stage parameters.

The stage sidecar persists the complete stage record, produced artifact metadata, and QC. Resume therefore restores pipeline state rather than merely skipping the command. A sidecar is reused only when the fingerprint exactly matches the current invocation.

Failed stages persist an error record and are never reused as successful output.

## Built-in stage backends

- `native/ingest`: verify local source existence and hash files.
- `native/qc`: inspect declared mesh geometry and emit a QC artifact.
- `native/export`: write bundle JSON and the self-contained HTML anatomy dossier.
- `external/*`: verify and hash an already-produced artifact without guessing output paths.
- `nnunet/segmentation`: execute an explicitly configured nnU-Net prediction command.
- `biv-volumetric-meshing/*`: execute selected surface/volume/UVC/fiber stages with explicit declared outputs.

Monolithic adapters are also available for biv-me and MyoMesh when those upstream workflows should own their internal staging.

## Canonical presets

`cine_cmr_biventricular` expresses the intended DICOM/cine → segmentation → contours → fit → surface → volume → coordinates → fibers → QC → export flow.

`presegmented_ep` starts from existing segmentation/geometry and builds the EP-required volume/coordinate/microstructure chain.

`mesh_qc_only` provides a minimal verification workflow for existing geometry.

Presets are templates, not claims that every upstream executable/model is installed or validated for a given cohort.

## Recommended production split

- Lightweight Python process: contracts, hashing, manifests, correspondence/motion summaries, orchestration, QC.
- GPU imaging service: nnU-Net or another validated segmentation/reconstruction model.
- Geometry service/container: model fitting, VTK/Gmsh processing, meshing, correspondence-preserving reconstruction.
- HPC geometry service: large volumetric mesh/UVC/microstructure operations.
- HeartTwin: workflow identity, service routing, typed state, and cross-component provenance.

Heavy artifacts remain external and are referenced by digest rather than embedded in orchestration payloads.
