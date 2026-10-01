# Staged and resumable anatomy pipelines

`PipelinePlan` declares ordered stages, the backend assigned to each stage, and stage-specific parameters.

Each stage receives:

- the immutable request identity;
- all currently registered artifacts;
- a dedicated work directory;
- explicit parameters.

Each successful stage returns typed artifact references and optional QC. CardiAnatomy records a deterministic fingerprint from the stage name, backend, input artifact identities/digests, and parameters.

A JSON stage sidecar makes long pipelines resumable. A sidecar is reused only when its fingerprint exactly matches the current invocation.

This design was motivated by large cardiac pipelines where segmentation, fitting, meshing, coordinate generation, and fiber generation have very different runtimes and dependencies. It avoids rerunning every upstream step after a downstream change.

## Recommended production split

- Lightweight Python process: contracts, hashing, manifests, orchestration, QC summaries.
- GPU image service: nnU-Net or another validated segmentation model.
- Geometry service/container: model fitting, VTK/Gmsh/meshing.
- HPC geometry service: large volumetric mesh/UVC/microstructure operations.
- HeartTwin: workflow identity and canonical state, not large artifact payloads.
