# Cine-CMR scan workflow

This optional command invokes the separately installed Apache-2.0 biv-me project on a single cine-CMR DICOM study. It can produce moving LV/RV surface meshes, HTML review plots, and optional volume, mass, strain and wall-thickness tables. It is not by itself a calibrated full-heart digital twin.

## Install prerequisites

Use the upstream project's documented Python 3.11 environment. Install Git LFS if required by its model submodule, then run:

    git clone https://github.com/UOA-Heart-Mechanics-Research/biv-me.git /opt/biv-me
    cd /opt/biv-me
    git submodule update --init --recursive
    python -m pip install -e .
    python src/pyezzi/setup.py build_ext --inplace

Confirm the upstream view-selection and segmentation weights are present. Install CardiAnatomy I/O dependencies with:

    python -m pip install -e '.[io]'

The launcher does not download model files implicitly. Software licensing does not automatically grant rights to datasets, checkpoints, or external solver runtimes. Cite Dillon et al., Medical Image Analysis 114 (2026), 104252, DOI 10.1016/j.media.2026.104252.

## Run

Use a private local directory containing one study and a new output folder:

    cardianatomy-scan-to-twin /secure/deidentified/cine-case \
      --biv-me-root /opt/biv-me \
      --python-executable /opt/conda/envs/bivme311/bin/python \
      --output-root /secure/output/case-twin

The output directory must be empty and separate from the input. The source directory is exposed to upstream by a local symlink, avoiding a second full copy. A pseudonymous case ID is generated from an input hash if none is given.

Review mode defaults to adaptive. Use manual for interactive correction of view selection; automatic mode disables interactive correction and needs a separate review. To skip quantitative post-processing, pass --skip-metrics. The command verifies that surface files were produced, writes a hash-pinned manifest, and reports partial analysis failures instead of silently marking every step successful.

## Outputs and scope

The output workspace contains fitted surface files and HTML review plots, upstream intermediate files, analysis tables, logs, generated config and a manifest. Treat the entire workspace as private; intermediate outputs, logs and HTML may contain identifying information.

The generated meshes represent ventricles, not a fully personalized four-chamber simulation mesh. A fuller stack still needs a qualified volumetric mesh, reviewed cavity labels/fibres/scar, aligned ECG and electrode/lead-field data, explicit mechanics and circulation parameters, calibration, and independent held-out validation.

A separate volume-meshing option is cdttk/biv-volumetric-meshing. It requires four prepared NIfTI view files (SAX, LAX_2Ch, LAX_3Ch, LAX_4Ch), downloaded nnU-Net checkpoints, and openCARP tooling for volume-mesh/UVC/fibre stages. That tool is not called by the direct DICOM command; check model and runtime terms before enabling it.
