# Third-party notices and architectural influences

CardiAnatomy v0.4.0 was designed after reviewing open cardiac anatomy, segmentation, meshing, coordinate, and microstructure projects. The core implementation in this repository is Virelion-authored unless a future file explicitly states otherwise.

No source code from the projects below is copied into the v0.4.0 core package. Their algorithms, interfaces, data-flow patterns, and publications informed the architecture.

| Project | Repository / site | License observed during review | CardiAnatomy use |
|---|---|---|---|
| biv-me | https://github.com/UOA-Heart-Mechanics-Research/biv-me | Apache-2.0 | architecture + planned external adapter |
| BiV Volumetric Meshing | https://github.com/cdttk/biv-volumetric-meshing | Apache-2.0 | staged pipeline architecture + planned adapter |
| nnU-Net | https://github.com/MIC-DKFZ/nnUNet | Apache-2.0 | segmentation command adapter |
| TotalSegmentator | https://github.com/wasserth/TotalSegmentator | Apache-2.0 | whole-heart/context segmentation backend candidate |
| cardiac-geometriesx | https://github.com/ComputationalPhysiology/cardiac-geometriesx | MIT | geometry API/fixture architecture |
| MyoMesh | https://github.com/FISIOCOMP-UFJF/MyoMesh | MIT | architecture for alignment/fiber/scar/meshing |
| BiventricularSSM | https://github.com/LoreVanSantvliet/BiventricularSSM | MIT | synthetic geometry/SSM architecture |
| atrialmtk | https://github.com/pcmlab/atrialmtk | GPL-3.0 | atrial/UAC architecture and external-backend candidate |
| Meshtool | https://github.com/ElsevierSoftwareX/SOFTX_2019_291 | GPL-3.0 | external-process integration only by default |
| fenicsx-ldrb | https://github.com/finsberg/fenicsx-ldrb | MIT | methodology reference / optional FEniCSx backend |
| AugmentA | https://github.com/KIT-IBT/AugmentA | Academic Public License; commercial license required | architectural ideas only; restricted adapter policy |
| openCARP | https://opencarp.org/ | Academic Public License; commercial licensing available | external runtime only after deployment/license review |
| CEMRG HeartBuilder | https://github.com/OpenHeartDevelopers/cemrg-heartbuilder | repository license text unresolved during review | architecture reference only by default |
| MorphiNetV2 | https://github.com/MalikTeng/MorphiNetV2 | MIT | dense-correspondence reconstruction architecture; optional learned-backend candidate |
| Bi-PT | https://github.com/Chenchuhui/Bi-PT | MIT | sparse-CMR four-chamber correspondence/deformation architecture; optional learned-backend candidate |
| HeartVolMesh | https://github.com/ccmim/HeartVolMesh | Apache-2.0 | volumetric correspondence and scaled-Jacobian QC concepts; code/templates not yet released per upstream README |
| MeshHeart | https://github.com/MengyunQ/MeshHeart | MIT | 3D+t mesh representation and generative-model architecture reference |
| TetHeart | https://github.com/Scalsol/TetHeart | no repository license file observed during review | 4D tetrahedral recovery architecture reference only |

## Model weights and datasets

Software license compatibility does not imply that model weights, training data, sample datasets, atlases, or derived statistical shape models can be redistributed under the same terms. Deployments must record and review those assets independently.

## Publications informing core concepts

- Bayer et al. (2012), rule-based myocardial fiber orientation.
- Bayer et al. (2018), Universal Ventricular Coordinates.
- Neic et al. / Meshtool work on automated image-based mesh manipulation.
- Dillon et al. / biv-me work on automated DICOM-to-biventricular-model pipelines.
- PyMeshTool (2026) work on Python-native anatomical twinning and reduced intermediate-file overhead.

See `docs/RESEARCH_SURVEY_2026-10-01.md` for the engineering synthesis.


## 2026-10-02 integration policy

CardiAnatomy 0.4.0 adds command adapters and toolchain manifests but does not vendor source code from the upstream projects listed above. Permissively licensed tools are invoked through explicit adapters. Copyleft, restricted, or unresolved-license projects remain separate processes or architecture references unless their deployment terms are explicitly reviewed.

The license of a software repository does not automatically cover pretrained weights, atlases, statistical shape models, example clinical datasets, or other external assets. Those assets are tracked separately by `ToolchainManifest`.

## CardioMesh validation fixtures

Two unchanged, gzip-compressed public geometry fixtures from
`ccmim/CardioMesh` revision `211710420e3504563fe18ba73980e2663ce68fc6`
are retained under `validation/data`. The repository's MIT license and copyright
notice (CISTIB-RSE, 2020) are preserved in `CardioMesh-LICENSE.txt`.
The data manifest records exact source URLs and uncompressed SHA-256 checksums.
No separate data license was found in the reviewed repository. These are
software format and negative QC fixtures, not clinical reference annotations.
