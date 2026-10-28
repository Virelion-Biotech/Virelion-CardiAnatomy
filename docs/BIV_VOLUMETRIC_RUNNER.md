# Staged BiV volumetric-meshing adapter

This command connects CardiAnatomy to the external [cdttk/biv-volumetric-meshing](https://github.com/cdttk/biv-volumetric-meshing) pipeline. It reuses that project's implementation through a subprocess adapter; no upstream algorithm, checkpoint, sample dataset, or openCARP binary is vendored here.

## What it does

The runner requires four already prepared NIfTI views and copies/re-serializes them into the directory structure expected upstream. It runs stages as distinct sequential commands and writes a private run workspace containing:

- preflight-manifest.json: hashes and NIfTI geometry checks for the four source views;
- run-manifest.json: upstream commit when available, staged input hashes, stage status/timing, relative artifact paths and hashes, and mesh QC;
- logs/: stage stdout/stderr and invoked command;
- data/<pseudonymous-case>/Instance_<n>/: upstream intermediate and final artifacts.

The output root must be new or empty. Existing non-empty output is rejected; partial results are preserved after a failure rather than silently erased. The original four source files are not modified.

If the volume stage is selected, the adapter searches produced mesh files for tetrahedral geometry and runs CardiAnatomy's geometry QC. It fails closed when no tetrahedral mesh passes the QC checks. This is not a proof that the segmentation labels, spatial registration, valve/base anatomy, tissue boundaries, or mesh-to-image alignment are correct.

## Install

Install CardiAnatomy's I/O and development dependencies:

~~~~bash
python -m pip install -e ".[io,dev]"
~~~~

Install the upstream pipeline following its own current instructions, for example:

~~~~bash
git clone https://github.com/cdttk/biv-volumetric-meshing.git /opt/biv-volumetric-meshing
cd /opt/biv-volumetric-meshing
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
~~~~

The segmentation stage also requires the upstream nnU-Net workspace and the four model assets described in that repository. Volumetric and UVC/fiber stages require a separate openCARP runtime. The upstream README warns that its workflow may not work as expected on data from sources other than its intended UK Biobank setting. Review upstream docs and source revision before applying it to any other population or acquisition protocol.

## Run surface reconstruction stages

The default sequence stops after segmentation, contour extraction, and surface generation:

~~~~bash
cardianatomy-biv-volumetric-run \
  --sax /private/case/SAX.nii.gz \
  --lax-2ch /private/case/LAX_2Ch.nii.gz \
  --lax-3ch /private/case/LAX_3Ch.nii.gz \
  --lax-4ch /private/case/LAX_4Ch.nii.gz \
  --upstream-root /opt/biv-volumetric-meshing \
  --nnunet-workspace /private/nnunet-workspace \
  --output-root /private/cardianatomy-run \
  --subject-id case_001
~~~~

The runner checks that the input views are readable NIfTI files with finite, nonsingular affines, positive spacing, and matching affine axis-code conventions. This does **not** establish registration. Confirm spatial alignment, view quality, temporal compatibility, and anatomical coverage before accepting the generated geometry.

## Run volumetric meshing

Only after independently reviewing the prepared views and confirming the runtime terms, request the volume-mesh stage and explicitly acknowledge the openCARP runtime requirement:

~~~~bash
cardianatomy-biv-volumetric-run \
  --sax /private/case/SAX.nii.gz \
  --lax-2ch /private/case/LAX_2Ch.nii.gz \
  --lax-3ch /private/case/LAX_3Ch.nii.gz \
  --lax-4ch /private/case/LAX_4Ch.nii.gz \
  --upstream-root /opt/biv-volumetric-meshing \
  --nnunet-workspace /private/nnunet-workspace \
  --carp-bin-dir /opt/openCARP/usr/bin \
  --output-root /private/cardianatomy-run-volume \
  --subject-id case_001 \
  --stages segmentation contour surface volumetric \
  --allow-restricted-runtime
~~~~

Add uvc-fiber after volumetric in --stages to request the upstream UVC/fiber stage. The acknowledgement is a software guardrail, not a legal opinion or proof that your use is authorized; review the current openCARP terms for your research/commercial deployment first. Segmentation model weights and training/data assets have separate terms too.

## Status and interpretation

The manifest status completed_surface_pipeline_only means the selected upstream commands returned successfully and generated files were recorded. It does not establish a volume mesh.

The status completed_volume_mesh_qc_passed means a produced tetrahedral mesh passed CardiAnatomy's implemented geometric checks. If UVC/fiber is also selected, the resulting status explicitly leaves UVC/fiber quality unverified. Review outputs against source image overlays, confirm label semantics and coordinate frames, inspect boundary conditions, and independently validate the mesh before solver use.

Failures preserve artifacts and mark the failing stage in run-manifest.json. The run workspace and logs may expose case metadata and should be handled as private clinical data.

## Validation boundary

Automated tests use synthetic NIfTI inputs, a fake upstream process, and a single synthetic tetrahedron to test orchestration, provenance, license gates, and QC wiring. They do **not** run the full upstream neural segmentation/meshing workflow, validate its pretrained weights, or establish patient-level anatomical accuracy. A real cohort validation with reviewed segmentations and independent geometric/anatomical reference measurements remains required.
