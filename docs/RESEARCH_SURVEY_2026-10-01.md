# Cardiac anatomy software survey — 1 October 2026

This audit was used to redesign CardiAnatomy v0.2.0. It focuses on reusable engineering ideas, scientific boundaries, and licensing.

## 1. biv-me

Repository: https://github.com/UOA-Heart-Mechanics-Research/biv-me

Strengths used conceptually:

- end-to-end DICOM → guidepoints → time-varying biventricular models;
- explicit view selection before segmentation;
- phase mismatch correction across cine views;
- temporal smoothing/consistency of landmarks;
- visualization as a QC tool rather than an afterthought;
- separation of preprocessing, fitting, and analysis;
- external model-weight management.

CardiAnatomy response: dedicated view/phase stages, model-fit artifact type, explicit acquisition metadata, HTML QC/report surface, and an external command adapter pattern.

License observed: Apache-2.0.

## 2. cdttk/biv-volumetric-meshing

Repository: https://github.com/cdttk/biv-volumetric-meshing

Strengths used conceptually:

- highly explicit stage boundaries: segmentation → contours → surface → volume → UVC/fibers;
- batch/subject/timeframe selection;
- stage-specific logging and outputs;
- volumetric meshes, UVC, and fiber structure as separate artifacts.

CardiAnatomy response: canonical stage order, stage fingerprints, resumable sidecars, first-class coordinate/microstructure artifacts.

License observed: Apache-2.0. Note that some runtime stages depend on openCARP, whose licensing is separate.

## 3. nnU-Net

Repository: https://github.com/MIC-DKFZ/nnUNet

Strengths used conceptually:

- segmentation is a backend with its own dataset/model configuration rather than hard-coded anatomy logic;
- model/data fingerprints and configuration matter as much as the network name;
- image segmentation stacks should remain isolated from lightweight orchestration.

CardiAnatomy response: explicit external command builder, no bundled weights, no implicit GPU dependency, artifact provenance prepared for model/dataset hashes.

License observed: Apache-2.0. Model weights and datasets require separate review.

## 4. cardiac-geometriesx

Repository: https://github.com/ComputationalPhysiology/cardiac-geometriesx

Strengths used conceptually:

- clean geometry abstraction;
- optional idealized/synthetic geometry generation;
- solver-specific exports without making a solver format the universal data model;
- separate geometry, mesh markers, and fiber fields.

CardiAnatomy response: solver-neutral artifacts and target-specific readiness. Synthetic geometry remains explicitly non-patient data.

License observed: MIT.

## 5. MyoMesh

Repository: https://github.com/FISIOCOMP-UFJF/MyoMesh

Strengths used conceptually:

- DICOM-space alignment is explicit;
- respiratory/slice alignment issues are treated as geometry problems;
- scar/core/gray-zone handling is integrated with mesh generation;
- fiber-angle parameters are exposed rather than buried;
- surface smoothing and mesh-quality failure modes are documented.

CardiAnatomy response: coordinate-frame contracts, registration artifacts, scar maps, exposed microstructure profiles, and mesh QC.

License observed: MIT.

## 6. Meshtool and PyMeshTool

Meshtool source: https://github.com/ElsevierSoftwareX/SOFTX_2019_291

The 2026 PyMeshTool work reports a Python-native interface for image-based anatomical twinning that reduces intermediate output and simplifies integration with NumPy-heavy pipelines. This reinforces CardiAnatomy's direction: Python orchestration with heavy mesh manipulation delegated to optimized libraries/backends.

Meshtool concepts worth preserving:

- query mesh properties before expensive simulation;
- extraction/insertion/mapping as explicit operations;
- conversion is an adapter concern;
- smoothing should preserve mesh quality;
- large anatomical workflows need fewer unnecessary intermediate files.

License observed for Meshtool repository: GPL-3.0.

## 7. Universal Ventricular Coordinates and LDRB

UVC publication: Bayer et al., Medical Image Analysis 2018, DOI 10.1016/j.media.2018.01.005.

LDRB implementation reviewed: https://github.com/finsberg/ldrb

CardiAnatomy treats coordinate fields and microstructure as distinct artifacts. The included `reference_rule_based_microstructure` function only rotates an already-defined local basis across a supplied transmural coordinate. It does **not** solve the Laplace problems or replace full UVC/LDRB implementations.

LDRB license observed: LGPL-3.0-or-later.

## 8. AugmentA and atrial workflows

Repository: https://github.com/KIT-IBT/AugmentA

Strong ideas:

- atrial orifices and appendages are first-class anatomical structures;
- curvature/landmark-assisted preprocessing;
- statistical-shape-model fitting;
- atrial-specific fiber rules;
- volumetric vs bilayer representations.

License observed: Academic Public License with commercial licensing requirement. CardiAnatomy therefore borrows **architecture only** and marks AugmentA as restricted/external by default.

## 9. Biventricular statistical shape models

Repository: https://github.com/LoreVanSantvliet/BiventricularSSM

Strengths:

- synthetic cohorts are useful for geometry/software validation;
- anatomical tags, fibers, and UVC can travel with mesh cohorts;
- shape-model sampling must never be confused with patient reconstruction.

CardiAnatomy response: SSM/synthetic tools belong behind explicit synthetic backends and should be labeled as such in provenance.

License observed: MIT.

## Engineering decisions produced by this review

1. Keep the CardiAnatomy core lightweight.
2. Never make one research pipeline the canonical public API.
3. Use stage records and artifact fingerprints so workflows are resumable and auditable.
4. Treat coordinate frames and registrations as first-class data.
5. Separate surface, volume, coordinate, microstructure, scar, and QC artifacts.
6. Keep segmentation model weights external and versioned.
7. Enforce license-aware backend policy.
8. Support ventricles, atria, and future whole-heart anatomy in one contract without pretending one algorithm covers all of them.
9. Make synthetic geometry useful for testing but impossible to mistake for patient anatomy through provenance/status labels.
10. Push empirical validation to frozen CardiBench/CardiEval datasets rather than hard-coding claims in the geometry package.

## 10. TotalSegmentator and whole-heart context

Repository: https://github.com/wasserth/TotalSegmentator

TotalSegmentator provides broad CT/MR segmentation across many anatomical structures and is built on nnU-Net. It is useful as a context/whole-heart segmentation backend rather than as the canonical ventricular-meshing solution.

License observed: Apache-2.0. Individual task/model assets and intended-use validation still require separate review.

## 11. atrialmtk

Repository: https://github.com/pcmlab/atrialmtk

Atrial Modelling Toolkit provides scalable bilayer/volumetric atrial-model construction, universal atrial coordinates, fibers, fibrosis, and multiple source modalities. It reinforces CardiAnatomy's decision to keep atrial coordinates and representations distinct from ventricular UVC while sharing one artifact/registration framework.

License observed: GPL-3.0. Some workflows also depend on openCARP, so deployment licensing remains layered.
