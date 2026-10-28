# From scan to a simulation-ready patient-specific HeartTwin

**Status: staged engineering plan, not a claim of completed or clinically validated functionality.**

## What the current automated path actually does

The current adapter runs the separately installed Apache-2.0 [biv-me](https://github.com/UOA-Heart-Mechanics-Research/biv-me) cine-CMR workflow. It is designed to generate moving left-ventricular endocardial, right-ventricular endocardial and epicardial **surface** meshes, review visualizations, and optional upstream volume/mass, strain and wall-thickness analyses. The user must review contours and image overlays. Passing the software checks is not evidence that the model is anatomically correct.

It does **not** yet turn an arbitrary CT/MRI study into a complete whole-heart twin automatically. The direct backend is cine-CMR-specific; the upstream model weights/environment are separate prerequisites; and output is not a labeled, simulation-grade volume mesh.

## Target pipeline and explicit gates

| Stage | Input → output | Candidate implementation/reuse | Gate before proceeding |
|---|---|---|---|
| 0. Intake and provenance | DICOM study → validated pseudonymous case | CardiAnatomy DICOM checks, input hashes, manifest | One intended patient/study; modality and acquisition scope supported; source remains local/private |
| 1. Dynamic ventricular reconstruction | Cine-CMR → moving LV/RV/epicardial surfaces | Existing biv-me adapter | All three surface classes exist; review view selection, segmentation and fit against source images; record failures and reviewed edits |
| 2. Labelled volume segmentation | SAX/LAX images → aligned structure labelmaps | Reuse biv-me intermediates where compatible; evaluate [BiV volumetric meshing](https://github.com/cdttk/biv-volumetric-meshing) and licensed segmentation backends | Explicit voxel geometry, image orientation, labels and registration are verified; no blind assumption that separate pipelines share coordinate frames |
| 3. Simulation-grade volume mesh | Labelmaps/surfaces → tetrahedral ventricular tissue and blood cavities | BiV volumetric meshing; CardiAnatomy mesh QC; meshio readers/writers | Complete wall, separate blood cavities, valve/base treatment and tissue tags; no inverted/degenerate elements; boundary, connectedness and scaled-Jacobian metrics pass declared thresholds |
| 4. Anatomical coordinates and fibres | Volume mesh → apex/base and transmural coordinates, fibre/sheet directions | Rule-based ventricular coordinates; [fenicsx-ldrb](https://github.com/finsberg/fenicsx-ldrb) as a candidate backend | Coordinate-frame chain recorded; fibre vectors finite, normalized and aligned with anatomy; independent visual/quantitative QC |
| 5. Scar and pathology | LGE-CMR/other suitable imaging → registered scar/core/border-zone labels | CardiAnatomy label utilities plus a separately validated segmentation/registration method | No scar inferred without suitable image evidence; registration error and threshold provenance recorded; scar labels remain separate from healthy tissue |
| 6. Electrophysiology | Volume mesh + fibres + Purkinje assumptions + ECG/electrode geometry → activation/ECG predictions | [openCARP](https://opencarp.org/) or another qualified solver, behind an adapter | Solver/runtime licensing reviewed; conductivities, ionic model and Purkinje assumptions explicit; patient-specific ECG/activation calibration and held-out validation |
| 7. Mechanics | Volume mesh + fibres + pressure/loading + strain observations → deformation/pressure-volume response | Qualified mechanics solver and explicit constitutive model | Boundary conditions, material parameters and active stress calibrated; strain/volume/pressure errors reported on data not used for fitting |
| 8. Flow/haemodynamics (optional) | Cavity surfaces/volume + inflow/outflow and pressure → flow fields | Compatible CFD/FSI backend | Mesh and boundary-condition suitability established; units, conservation and sensitivity checks pass |
| 9. Twin bundle and audit | Geometry + fields + observations + parameters → versioned HeartTwin bundle | CardiAnatomy contracts, stage records and artifact hashes; HeartTwin integration | Reproducible build, complete provenance, uncertainty/sensitivity report, independent held-out validation and clear intended-use limits |

## How we should reuse other GitHub projects

Use **adapters and pinned external dependencies**, not indiscriminate copying. Keep each upstream project's license, notices, citation, source commit, model-weight hashes and data terms attached to the run. A repository's software license does not automatically cover its trained weights, sample data, statistical atlases or external solver binaries. Re-check licenses and commercial-use terms at the exact revision used.

Priority order:

1. **Finish and qualify the biv-me adapter** as the first real patient-scan entry point.
2. **Bridge surfaces to the volume-meshing pipeline** only after a tested conversion path exists for its four required views (SAX, LAX 2CH, LAX 3CH and LAX 4CH) and their orientations/spacing are preserved. The current direct DICOM command does not do that bridge.
3. Add volume-mesh quality checks and an anatomical review bundle before wiring any solver.
4. Add fibres and scar as separately auditable stages; never silently invent either from insufficient imaging.
5. Add EP/mechanics/flow adapters individually with explicit parameter files, solver versions, validation datasets and calibration reports.
6. Call the result a **full digital twin** only after geometry, fields and at least one intended physiological model are calibrated to patient observations and independently evaluated. Until then, call it a patient-specific anatomical model or research prototype.

## Immediate acceptance criteria

- A de-identified research cine-CMR test case can run through the pipeline on a documented machine with pinned upstream commit and model assets.
- The three required surface classes are present for the expected cardiac phases; all failures are surfaced in the manifest.
- Every output has a source hash, relative path, byte count, format, and SHA-256; raw identifiers and original source paths are not copied into the manifest.
- Visual review records contour quality and corrections; geometry QC reports measurable topology/element-quality metrics.
- A subsequent volume-mesh stage produces complete ventricular wall and separate LV/RV cavity labels with valid registration and coordinates.
- EP/mechanics results are not labelled patient-specific until model parameters are fitted and checked against independent observations.
- All tests use synthetic/public fixtures; a successful CI run is not a substitute for a real scan end-to-end test or clinical validation.

## Safety and scope

This is research software. Do not use outputs for diagnosis, intervention planning or clinical decisions without appropriate validation, governance and regulatory review. Keep patient imaging and all intermediate files in a trusted environment; HTML reports and logs may also expose sensitive data.
