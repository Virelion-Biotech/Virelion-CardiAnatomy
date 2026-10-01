from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


LicenseClass = Literal["permissive", "copyleft", "restricted", "unknown"]


@dataclass(frozen=True)
class ExternalToolDescriptor:
    tool_id: str
    project: str
    url: str
    license_name: str
    license_class: LicenseClass
    purpose: tuple[str, ...]
    notes: str = ""

    @property
    def default_allowed(self) -> bool:
        return self.license_class in {"permissive", "copyleft"}


TOOLS: dict[str, ExternalToolDescriptor] = {
    "totalsegmentator": ExternalToolDescriptor(
        tool_id="totalsegmentator",
        project="wasserth/TotalSegmentator",
        url="https://github.com/wasserth/TotalSegmentator",
        license_name="Apache-2.0",
        license_class="permissive",
        purpose=("whole_heart_segmentation", "ct_segmentation", "mr_segmentation"),
        notes=(
            "Useful for broader CT/MR anatomical context. Task/model terms and clinical "
            "validation remain separate from the software license."
        ),
    ),
    "atrialmtk": ExternalToolDescriptor(
        tool_id="atrialmtk",
        project="pcmlab/atrialmtk",
        url="https://github.com/pcmlab/atrialmtk",
        license_name="GPL-3.0",
        license_class="copyleft",
        purpose=("atrial_surface", "atrial_volume", "uac", "microstructure", "fibrosis"),
        notes="Atrial workflows may also depend on openCARP; review runtime licensing separately.",
    ),
    "nnunet": ExternalToolDescriptor(
        tool_id="nnunet",
        project="MIC-DKFZ/nnUNet",
        url="https://github.com/MIC-DKFZ/nnUNet",
        license_name="Apache-2.0",
        license_class="permissive",
        purpose=("segmentation",),
        notes=(
            "Model weights and downstream datasets can carry separate terms; "
            "verify them separately."
        ),
    ),
    "biv_me": ExternalToolDescriptor(
        tool_id="biv_me",
        project="UOA-Heart-Mechanics-Research/biv-me",
        url="https://github.com/UOA-Heart-Mechanics-Research/biv-me",
        license_name="Apache-2.0",
        license_class="permissive",
        purpose=("view_selection", "segmentation", "contours", "surface_fit", "model_fit"),
    ),
    "biv_volumetric": ExternalToolDescriptor(
        tool_id="biv_volumetric",
        project="cdttk/biv-volumetric-meshing",
        url="https://github.com/cdttk/biv-volumetric-meshing",
        license_name="Apache-2.0",
        license_class="permissive",
        purpose=(
            "segmentation",
            "contours",
            "surface_mesh",
            "volume_mesh",
            "coordinates",
            "microstructure",
        ),
        notes="Its openCARP-dependent stages inherit separate runtime licensing constraints.",
    ),
    "cardiac_geometriesx": ExternalToolDescriptor(
        tool_id="cardiac_geometriesx",
        project="ComputationalPhysiology/cardiac-geometriesx",
        url="https://github.com/ComputationalPhysiology/cardiac-geometriesx",
        license_name="MIT",
        license_class="permissive",
        purpose=("surface_mesh", "volume_mesh", "microstructure", "synthetic_geometry"),
    ),
    "myomesh": ExternalToolDescriptor(
        tool_id="myomesh",
        project="FISIOCOMP-UFJF/MyoMesh",
        url="https://github.com/FISIOCOMP-UFJF/MyoMesh",
        license_name="MIT",
        license_class="permissive",
        purpose=("surface_mesh", "volume_mesh", "microstructure", "scar", "registration"),
    ),
    "biventricular_ssm": ExternalToolDescriptor(
        tool_id="biventricular_ssm",
        project="LoreVanSantvliet/BiventricularSSM",
        url="https://github.com/LoreVanSantvliet/BiventricularSSM",
        license_name="MIT",
        license_class="permissive",
        purpose=("synthetic_geometry", "surface_mesh"),
    ),
    "meshtool": ExternalToolDescriptor(
        tool_id="meshtool",
        project="Meshtool",
        url="https://github.com/ElsevierSoftwareX/SOFTX_2019_291",
        license_name="GPL-3.0",
        license_class="copyleft",
        purpose=("volume_mesh", "mesh_qc", "conversion", "mapping", "smoothing"),
        notes="Prefer external-process integration and retain upstream license notices.",
    ),
    "ldrb": ExternalToolDescriptor(
        tool_id="ldrb",
        project="finsberg/ldrb",
        url="https://github.com/finsberg/ldrb",
        license_name="LGPL-3.0-or-later",
        license_class="copyleft",
        purpose=("microstructure",),
    ),
    "augmenta": ExternalToolDescriptor(
        tool_id="augmenta",
        project="KIT-IBT/AugmentA",
        url="https://github.com/KIT-IBT/AugmentA",
        license_name="Academic Public License / commercial license required",
        license_class="restricted",
        purpose=("atrial_surface", "orifice_labeling", "landmarks", "microstructure"),
        notes="Do not bundle or enable by default for commercial use.",
    ),
    "opencarp": ExternalToolDescriptor(
        tool_id="opencarp",
        project="openCARP",
        url="https://opencarp.org/",
        license_name="Academic Public License / commercial license available",
        license_class="restricted",
        purpose=("coordinates", "microstructure", "simulation"),
        notes="Runtime use in for-profit settings can require a commercial license.",
    ),
}


def tool_catalog() -> list[ExternalToolDescriptor]:
    return [TOOLS[key] for key in sorted(TOOLS)]


def require_tool_policy(tool_id: str, *, allow_restricted: bool = False) -> ExternalToolDescriptor:
    try:
        tool = TOOLS[tool_id]
    except KeyError as exc:
        raise KeyError(f"Unknown CardiAnatomy external tool: {tool_id}") from exc
    if tool.license_class == "restricted" and not allow_restricted:
        raise PermissionError(
            f"{tool.project} is not enabled by default because its license is {tool.license_name}. "
            "Set an explicit deployment policy only after confirming your use is permitted."
        )
    return tool
