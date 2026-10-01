# Third-party notices and architectural influences

CardiAnatomy v0.2.0 was designed after reviewing open cardiac anatomy, segmentation, meshing, coordinate, and microstructure projects. The core implementation in this repository is Virelion-authored unless a future file explicitly states otherwise.

No source code from the projects below is copied into the v0.2.0 core package. Their algorithms, interfaces, data-flow patterns, and publications informed the architecture.

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
| LDRB | https://github.com/finsberg/ldrb | LGPL-3.0-or-later | methodology reference / optional backend |
| AugmentA | https://github.com/KIT-IBT/AugmentA | Academic Public License; commercial license required | architectural ideas only; restricted adapter policy |
| openCARP | https://opencarp.org/ | Academic Public License; commercial licensing available | external runtime only after deployment/license review |

## Model weights and datasets

Software license compatibility does not imply that model weights, training data, sample datasets, atlases, or derived statistical shape models can be redistributed under the same terms. Deployments must record and review those assets independently.

## Publications informing core concepts

- Bayer et al. (2012), rule-based myocardial fiber orientation.
- Bayer et al. (2018), Universal Ventricular Coordinates.
- Neic et al. / Meshtool work on automated image-based mesh manipulation.
- Dillon et al. / biv-me work on automated DICOM-to-biventricular-model pipelines.
- PyMeshTool (2026) work on Python-native anatomical twinning and reduced intermediate-file overhead.

See `docs/RESEARCH_SURVEY_2026-10-01.md` for the engineering synthesis.
