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
    "nnunet": ExternalToolDescriptor(
        tool_id="nnunet",
        project="MIC-DKFZ/nnUNet",
        url="https://github.com/MIC-DKFZ/nnUNet",
        license_name="Apache-2.0",
        license_class="permissive",
        purpose=("segmentation", "model_inference"),
        notes=(
            "Model weights and datasets can carry separate terms; "
            "record them independently."
        ),
    ),
    "totalsegmentator": ExternalToolDescriptor(
        tool_id="totalsegmentator",
        project="wasserth/TotalSegmentator",
        url="https://github.com/wasserth/TotalSegmentator",
        license_name="Apache-2.0",
        license_class="permissive",
        purpose=("whole_heart_segmentation", "ct_segmentation", "mr_segmentation"),
        notes=(
            "Useful for broad anatomical context. Task/model assets and intended-use "
            "validation remain separate from the software license."
        ),
    ),
    "biv_me": ExternalToolDescriptor(
        tool_id="biv_me",
        project="UOA-Heart-Mechanics-Research/biv-me",
        url="https://github.com/UOA-Heart-Mechanics-Research/biv-me",
        license_name="Apache-2.0",
        license_class="permissive",
        purpose=(
            "dicom",
            "view_selection",
            "phase_harmonization",
            "segmentation",
            "surface_fit",
            "function",
        ),
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
        notes=(
            "Some UVC/fiber and volumetric stages require separately licensed "
            "openCARP runtime tooling."
        ),
    ),
    "cardiac_geometriesx": ExternalToolDescriptor(
        tool_id="cardiac_geometriesx",
        project="ComputationalPhysiology/cardiac-geometriesx",
        url="https://github.com/ComputationalPhysiology/cardiac-geometriesx",
        license_name="MIT",
        license_class="permissive",
        purpose=("surface_mesh", "volume_mesh", "microstructure", "synthetic_geometry"),
        notes=(
            "Useful for solver-ready fixtures. Synthetic output must not be presented "
            "as patient anatomy."
        ),
    ),
    "fenicsx_ldrb": ExternalToolDescriptor(
        tool_id="fenicsx_ldrb",
        project="finsberg/fenicsx-ldrb",
        url="https://github.com/finsberg/fenicsx-ldrb",
        license_name="MIT",
        license_class="permissive",
        purpose=("microstructure", "fibers"),
        notes="Requires FEniCSx and is best isolated as an optional backend/container.",
    ),
    "myomesh": ExternalToolDescriptor(
        tool_id="myomesh",
        project="FISIOCOMP-UFJF/MyoMesh",
        url="https://github.com/FISIOCOMP-UFJF/MyoMesh",
        license_name="MIT",
        license_class="permissive",
        purpose=(
            "dicom_alignment",
            "surface_mesh",
            "volume_mesh",
            "microstructure",
            "scar",
        ),
    ),
    "biventricular_ssm": ExternalToolDescriptor(
        tool_id="biventricular_ssm",
        project="LoreVanSantvliet/BiventricularSSM",
        url="https://github.com/LoreVanSantvliet/BiventricularSSM",
        license_name="MIT",
        license_class="permissive",
        purpose=("synthetic_geometry", "statistical_shape_model"),
        notes=(
            "Generated cohorts must remain explicitly synthetic and retain "
            "model/data provenance."
        ),
    ),
    "atrialmtk": ExternalToolDescriptor(
        tool_id="atrialmtk",
        project="pcmlab/atrialmtk",
        url="https://github.com/pcmlab/atrialmtk",
        license_name="GPL-3.0",
        license_class="copyleft",
        purpose=("atrial_surface", "atrial_volume", "uac", "microstructure", "fibrosis"),
        notes="Atrial workflows may also depend on openCARP; review runtime licensing.",
    ),
    "meshtool": ExternalToolDescriptor(
        tool_id="meshtool",
        project="Meshtool",
        url="https://github.com/ElsevierSoftwareX/SOFTX_2019_291",
        license_name="GPL-3.0",
        license_class="copyleft",
        purpose=("mesh_convert", "mesh_extract", "mesh_map", "mesh_smooth", "mesh_qc"),
        notes=(
            "Prefer external-process integration and preserve upstream license notices."
        ),
    ),
    "augmenta": ExternalToolDescriptor(
        tool_id="augmenta",
        project="KIT-IBT/AugmentA",
        url="https://github.com/KIT-IBT/AugmentA",
        license_name="Academic Public License / commercial license required",
        license_class="restricted",
        purpose=("atrial_surface", "orifice_labeling", "landmarks", "microstructure"),
        notes="Disabled by default pending explicit deployment/license authorization.",
    ),
    "opencarp": ExternalToolDescriptor(
        tool_id="opencarp",
        project="openCARP",
        url="https://opencarp.org/",
        license_name="Academic Public License / commercial license available",
        license_class="restricted",
        purpose=("coordinates", "microstructure", "simulation"),
        notes="Deployment requires an explicit license review.",
    ),
    "cemrg-heartbuilder": ExternalToolDescriptor(
        tool_id="cemrg-heartbuilder",
        project="OpenHeartDevelopers/cemrg-heartbuilder",
        url="https://github.com/OpenHeartDevelopers/cemrg-heartbuilder",
        license_name="No clear license text observed in repository review",
        license_class="unknown",
        purpose=("whole_heart", "segmentation", "meshing", "post_processing"),
        notes="Architecture reference only until software terms are clarified.",
    ),
    "morphinetv2": ExternalToolDescriptor(
        tool_id="morphinetv2",
        project="MalikTeng/MorphiNetV2",
        url="https://github.com/MalikTeng/MorphiNetV2",
        license_name="Code/model terms require deployment review",
        license_class="unknown",
        purpose=("surface_reconstruction", "dense_correspondence"),
        notes="Research backend candidate; review code and model-weight terms separately.",
    ),
    "bi-pt": ExternalToolDescriptor(
        tool_id="bi-pt",
        project="Chenchuhui/Bi-PT",
        url="https://github.com/Chenchuhui/Bi-PT",
        license_name="Code/model terms require deployment review",
        license_class="unknown",
        purpose=("sparse_cmr", "four_chamber_reconstruction", "atlas_deformation"),
        notes="Experimental backend candidate pending independent validation and license review.",
    ),
}


def tool_catalog() -> list[ExternalToolDescriptor]:
    return [TOOLS[key] for key in sorted(TOOLS)]


def tool_spec(tool_id: str) -> ExternalToolDescriptor:
    try:
        return TOOLS[tool_id]
    except KeyError as exc:
        raise KeyError(f"Unknown CardiAnatomy external tool: {tool_id}") from exc


def require_tool_policy(
    tool_id: str,
    *,
    allow_restricted: bool = False,
) -> ExternalToolDescriptor:
    tool = tool_spec(tool_id)
    if tool.license_class == "unknown":
        raise PermissionError(
            f"{tool.project} has unresolved license terms: {tool.license_name}. "
            "It cannot be enabled through the generic restricted-tool override."
        )
    if tool.license_class == "restricted" and not allow_restricted:
        raise PermissionError(
            f"{tool.project} is not enabled by default because its license is "
            f"{tool.license_name}. Confirm permitted use before enabling it."
        )
    return tool
