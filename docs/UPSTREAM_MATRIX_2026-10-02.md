# Upstream cardiac-anatomy matrix — 2 October 2026

This matrix records the projects reviewed while expanding CardiAnatomy 0.3.0. It is an engineering synthesis, not a claim of source-code reuse. CardiAnatomy's core remains Virelion-authored unless a file explicitly says otherwise.

| Project | Strongest idea | CardiAnatomy response | License/deployment stance |
|---|---|---|---|
| biv-me | validated cine-CMR to time-varying biventricular model pipeline; view selection, segmentation, guidepoints, fitting, temporal consistency | staged cine-CMR preset, explicit view/phase stages, model-fit artifacts, manual-QC-friendly reporting | Apache-2.0; adapter-friendly |
| BiV volumetric meshing | explicit segmentation → contours → surface → volume → UVC/fibers | stage DAG, coordinate and microstructure artifacts, resumability | Apache-2.0 core; check openCARP-dependent stages separately |
| nnU-Net | self-configuring segmentation with model/data fingerprints | isolated segmentation backend and model-asset provenance | Apache-2.0 software; weights/datasets reviewed separately |
| cardiac-geometriesx | clean geometry/marker/fiber objects and synthetic fixtures | solver-neutral artifacts; synthetic geometry kept distinct from patient anatomy | MIT |
| fenicsx-ldrb | modern FEniCSx rule-based microstructure | optional microstructure backend and CLI command builder | MIT |
| MyoMesh | DICOM-space alignment, scar integration, fiber assignment, documented smoothing failure modes | explicit frame/registration contracts, scar artifacts, mesh QC | MIT |
| BiventricularSSM | reproducible synthetic ventricular cohorts with tags/fibers | synthetic/SSM backend category with provenance requirements | MIT; data/SSM assets separate |
| CEMRG HeartBuilder | modular whole-heart construction and external-tool orchestration | safe subprocess runner, toolchain manifest, whole-heart vocabulary | repository license text unclear during review; no source reuse by default |
| MorphiNetV2 | topology-preserving biventricular reconstruction with dense correspondence | future learned surface-reconstruction backend contract; correspondence should be preserved as metadata | review code and weights before deployment |
| Bi-PT | sparse-CMR four-chamber atlas deformation | future sparse-reconstruction backend; explicit experimental validation tier | emerging research code; review before deployment |
| AugmentA | atrial orifices, SSM fitting, atrial LDRB workflow | atrial structures and coordinate-family separation | restricted academic/commercial licensing; disabled by default |
| atrialmtk | atrial UAC, bilayer/volume models, fibrosis | shared artifact model with atrial-specific coordinate semantics | GPL-3.0 and layered runtime licenses |
| Meshtool | mesh extraction, mapping, conversion, smoothing | external-process tooling with explicit mesh QC | GPL-3.0 |
| openCARP | UVC/fiber/simulation ecosystem | external runtime boundary | academic/commercial licensing review required |

## New engineering conclusions

1. **Dense correspondence is valuable enough to preserve explicitly.** Learned surface methods such as MorphiNet and newer atlas-deformation approaches show why node correspondence should be carried as an artifact property instead of discarded during conversion.
2. **Whole-heart support must not collapse atrial and ventricular coordinates into one field.** UVC/UAC and future whole-heart coordinates should stay typed by coordinate family.
3. **Model weights are first-class external assets.** Their hashes, source, version, license, and training-domain notes belong beside executable provenance.
4. **Resumability must restore state, not only skip work.** Sidecars therefore persist complete stage output artifact metadata and QC.
5. **Metadata heuristics are not learned classifiers.** The built-in cine-series triage is intentionally labeled heuristic; biv-me/learned view selection remains a backend.
6. **Patient anatomy must remain distinguishable from sampled/synthetic geometry.** Statistical-shape and idealized geometry backends must set provenance accordingly.
7. **External-tool orchestration needs license policy as code.** Restricted/unclear tools are disabled by default.

## Scientific references

- Dillon J, et al. biv-me: open-source software for generating time-varying biventricular meshes from cine CMR with multi-cohort validation. Medical Image Analysis. 2026;114:104252.
- Deng Y, et al. MorphiNet: A Graph Subdivision Network for Adaptive Bi-ventricle Surface Reconstruction. IEEE Transactions on Medical Imaging. 2026.
- Bayer J, et al. Universal ventricular coordinates: A generic framework for describing position within the heart and transferring data. Medical Image Analysis. 2018;45:83-93.
- Bayer JD, et al. A novel rule-based algorithm for assigning myocardial fiber orientation to computational heart models. Ann Biomed Eng. 2012.
