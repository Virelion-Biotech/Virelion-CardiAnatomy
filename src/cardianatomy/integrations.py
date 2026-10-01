from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


LicenseClass = Literal["permissive", "copyleft", "restricted", "unknown"]


@dataclass(frozen=True)
class ToolSpec:
    tool_id: str
    project: str
    url: str
    license_name: str
    license_class: LicenseClass
    default_allowed: bool
    purpose: tuple[str, ...]
    notes: str = ""


_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        tool_id="nnunet",
        project="nnU-Net",
        url="https://github.com/MIC-DKFZ/nnUNet",
        license_name="Apache-2.0",
        license_class="permissive",
        default_allowed=True,
        purpose=("segmentation", "model-inference"),
        notes="Model weights and datasets require independent license/provenance review.",
    ),
    ToolSpec(
        tool_id="biv-me",
        project="biv-me",
        url="https://github.com/UOA-Heart-Mechanics-Research/biv-me",
        license_name="Apache-2.0",
        license_class="permissive",
        default_allowed=True,
        purpose=("dicom", "view-selection", "segmentation", "surface-fit", "function"),
        notes="Prefer adapter use so upstream models and optional GPU stack remain isolated.",
    ),
    ToolSpec(
        tool_id="biv-volumetric-meshing",
        project="BiV Volumetric Meshing",
        url="https://github.com/cdttk/biv-volumetric-meshing",
        license_name="Apache-2.0",
        license_class="permissive",
        default_allowed=True,
        purpose=("contours", "surface-mesh", "volume-mesh", "coordinates", "microstructure"),
        notes="Some optional runtime stages rely on separately licensed openCARP tooling.",
    ),
    ToolSpec(
        tool_id="cardiac-geometriesx",
        project="cardiac-geometriesx",
        url="https://github.com/ComputationalPhysiology/cardiac-geometriesx",
        license_name="MIT",
        license_class="permissive",
        default_allowed=True,
        purpose=("synthetic-geometry", "mesh", "markers", "solver-export"),
        notes=(\n            "Useful for fixtures and solver-ready geometry; synthetic output is not patient anatomy."\n        ),
    ),
    ToolSpec(
        tool_id="myomesh",
        project="MyoMesh",
        url="https://github.com/FISIOCOMP-UFJF/MyoMesh",
        license_name="MIT",
        license_class="permissive",
        default_allowed=True,
        purpose=("dicom-alignment", "surface-mesh", "volume-mesh", "scar", "microstructure"),
        notes="External pipeline; CardiAnatomy keeps canonical artifacts solver-neutral.",
    ),
    ToolSpec(
        tool_id="fenicsx-ldrb",
        project="fenicsx-ldrb",
        url="https://github.com/finsberg/fenicsx-ldrb",
        license_name="MIT",
        license_class="permissive",
        default_allowed=True,
        purpose=("microstructure", "fibers"),
        notes="Requires FEniCSx; best deployed as an optional backend/container.",
    ),
    ToolSpec(
        tool_id="meshtool",
        project="Meshtool",
        url="https://github.com/ElsevierSoftwareX/SOFTX_2019_291",
        license_name="GPL-3.0",
        license_class="copyleft",
        default_allowed=True,
        purpose=("mesh-convert", "mesh-extract", "mesh-map", "mesh-smooth"),
        notes=(\n            "Default integration is subprocess/adapter based; preserve upstream license obligations."\n        ),
    ),
    ToolSpec(
        tool_id="biventricular-ssm",
        project="BiventricularSSM",
        url="https://github.com/LoreVanSantvliet/BiventricularSSM",
        license_name="MIT",
        license_class="permissive",
        default_allowed=True,
        purpose=("synthetic-geometry", "statistical-shape-model"),
        notes="Generated cohorts must be marked synthetic and retain model/data provenance.",
    ),
    ToolSpec(
        tool_id="augmenta",
        project="AugmentA",
        url="https://github.com/KIT-IBT/AugmentA",
        license_name="Academic Public License / commercial license",
        license_class="restricted",
        default_allowed=False,
        purpose=("atria", "orifices", "ssm", "microstructure"),
        notes="Architecture reference only unless deployment has explicit license authorization.",
    ),
    ToolSpec(
        tool_id="opencarp",
        project="openCARP",
        url="https://opencarp.org/",
        license_name="Academic/commercial dual licensing",
        license_class="restricted",
        default_allowed=False,
        purpose=("coordinates", "mesh", "simulation-ecosystem"),
        notes="Requires explicit deployment/license review before enabling.",
    ),
    ToolSpec(
        tool_id="cemrg-heartbuilder",
        project="CEMRG HeartBuilder",
        url="https://github.com/OpenHeartDevelopers/cemrg-heartbuilder",
        license_name="No clear license text observed in repository review",
        license_class="unknown",
        default_allowed=False,
        purpose=("whole-heart", "segmentation", "meshing", "post-processing"),
        notes="Use as an architecture reference until redistribution/runtime terms are clarified.",
    ),
)


def tool_catalog() -> tuple[ToolSpec, ...]:
    return _TOOLS


def tool_spec(tool_id: str) -> ToolSpec:
    for item in _TOOLS:
        if item.tool_id == tool_id:
            return item
    raise KeyError(f"Unknown CardiAnatomy tool: {tool_id}")


def require_tool_policy(tool_id: str, *, allow_restricted: bool = False) -> ToolSpec:
    item = tool_spec(tool_id)
    if not item.default_allowed and not allow_restricted:
        raise PermissionError(
            f"Tool {tool_id!r} is not enabled by default: {item.license_name}. "
            "Pass allow_restricted=True only after deployment/license review."
        )
    return item


def nnunet_predict_command(
    *,
    input_dir: str,
    output_dir: str,
    dataset: str,
    configuration: str = "3d_fullres",
    folds: tuple[str, ...] | None = None,
    device: str | None = None,
) -> list[str]:
    require_tool_policy("nnunet")
    command = [
        "nnUNetv2_predict",
        "-i",
        input_dir,
        "-o",
        output_dir,
        "-d",
        str(dataset),
        "-c",
        configuration,
    ]
    if folds:
        command += ["-f", *[str(value) for value in folds]]
    if device:
        command += ["-device", device]
    return command


def biv_me_command(
    *,
    main_script: str,
    config_file: str,
    case_name: str | None = None,
    python_executable: str = "python",
) -> list[str]:
    require_tool_policy("biv-me")
    command = [python_executable, main_script, "-config", config_file]
    if case_name:
        command += ["-case", case_name]
    return command


def meshtool_command(
    *,
    operation: str,
    input_mesh: str,
    output_mesh: str | None = None,
    extra_args: tuple[str, ...] = (),
) -> list[str]:
    require_tool_policy("meshtool")
    command = ["meshtool", operation, "-msh=" + input_mesh]
    if output_mesh is not None:
        command.append("-outmsh=" + output_mesh)
    command.extend(extra_args)
    return command


def ldrb_command(
    *,
    mesh_path: str,
    markers_file: str,
    alpha_endo_lv: float = 60.0,
    alpha_epi_lv: float = -60.0,
    fiber_space: str = "P_1",
) -> list[str]:
    require_tool_policy("fenicsx-ldrb")
    return [
        "ldrb",
        mesh_path,
        "--markers-file",
        markers_file,
        "--fiber-space",
        fiber_space,
        "--alpha-endo-lv",
        str(alpha_endo_lv),
        "--alpha-epi-lv",
        str(alpha_epi_lv),
    ]


def geox_command(*args: str) -> list[str]:
    require_tool_policy("cardiac-geometriesx")
    return ["geox", *args]


def biv_volumetric_command(
    *,
    run_script: str,
    data_dir: str,
    components: tuple[str, ...],
    subject: str | None = None,
    instance: int | None = None,
    timeframe: int | None = None,
    workspace_dir: str | None = None,
    carp_bin_dir: str | None = None,
    python_executable: str = "python",
) -> list[str]:
    require_tool_policy("biv-volumetric-meshing")
    allowed = {
        "segmentation": "--segmentation",
        "contour": "--contour",
        "surface": "--surface",
        "volumetric": "--volumetric",
        "uvc-fiber": "--uvc-fiber",
        "all": "--all-components",
    }
    if not components:
        raise ValueError("At least one BiV volumetric component is required")
    unknown = set(components) - set(allowed)
    if unknown:
        raise ValueError(f"Unknown BiV volumetric components: {sorted(unknown)}")
    command = [python_executable, run_script, "--data-dir", data_dir]
    command.extend(allowed[item] for item in components)
    if subject:
        command += ["--subject", subject]
    if instance is not None:
        command += ["--instance", str(instance)]
    if timeframe is not None:
        command += ["--timeframe", str(timeframe)]
    if workspace_dir:
        command += ["--workspace-dir", workspace_dir]
    if carp_bin_dir:
        command += ["--carp-bin-dir", carp_bin_dir]
    return command


def myomesh_command(
    *,
    input_mat: str,
    python_executable: str = "python",
    no_alg: bool = False,
    no_align_dicom: bool = False,
    extra_args: tuple[str, ...] = (),
) -> list[str]:
    require_tool_policy("myomesh")
    command = [python_executable, "execAll.py", "-i", input_mat]
    if no_alg:
        command.append("--no_alg")
    if no_align_dicom:
        command.append("--no_align_dicom")
    command.extend(extra_args)
    return command
