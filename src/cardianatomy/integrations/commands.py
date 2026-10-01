from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .catalog import require_tool_policy


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def executable_available(executable: str) -> bool:
    return shutil.which(executable) is not None or Path(executable).is_file()


def run_command(
    command: Sequence[str],
    *,
    timeout: int = 3600,
    cwd: str | Path | None = None,
) -> CommandResult:
    if not command:
        raise ValueError("command must not be empty")
    process = subprocess.run(
        [str(item) for item in command],
        cwd=None if cwd is None else str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        shell=False,
    )
    result = CommandResult(
        command=tuple(str(item) for item in command),
        returncode=process.returncode,
        stdout=process.stdout,
        stderr=process.stderr,
    )
    if process.returncode:
        message = process.stderr.strip() or process.stdout.strip()
        raise RuntimeError(
            f"Command failed ({process.returncode}): "
            f"{' '.join(result.command)}\n{message}"
        )
    return result


def nnunet_predict_command(
    *,
    input_dir: str | Path,
    output_dir: str | Path,
    dataset: str,
    configuration: str = "3d_fullres",
    folds: Sequence[str] | None = None,
    device: str | None = None,
    executable: str = "nnUNetv2_predict",
) -> list[str]:
    require_tool_policy("nnunet")
    command = [
        executable,
        "-i",
        str(input_dir),
        "-o",
        str(output_dir),
        "-d",
        str(dataset),
        "-c",
        configuration,
    ]
    if folds:
        command += ["-f", *[str(fold) for fold in folds]]
    if device:
        command += ["-device", str(device)]
    return command


def biv_me_command(
    *,
    main_script: str | Path,
    config_file: str | Path,
    case_name: str | None = None,
    python_executable: str = "python",
) -> list[str]:
    require_tool_policy("biv_me")
    command = [
        python_executable,
        str(main_script),
        "-config",
        str(config_file),
    ]
    if case_name:
        command += ["-case", case_name]
    return command


def biv_volumetric_command(
    *,
    run_script: str | Path,
    data_dir: str | Path,
    components: tuple[str, ...],
    subject: str | None = None,
    instance: int | None = None,
    timeframe: int | None = None,
    workspace_dir: str | Path | None = None,
    carp_bin_dir: str | Path | None = None,
    python_executable: str = "python",
) -> list[str]:
    require_tool_policy("biv_volumetric")
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
        raise ValueError(
            f"Unknown BiV volumetric components: {sorted(unknown)}"
        )
    command = [
        python_executable,
        str(run_script),
        "--data-dir",
        str(data_dir),
    ]
    command.extend(allowed[item] for item in components)
    if subject:
        command += ["--subject", subject]
    if instance is not None:
        command += ["--instance", str(instance)]
    if timeframe is not None:
        command += ["--timeframe", str(timeframe)]
    if workspace_dir:
        command += ["--workspace-dir", str(workspace_dir)]
    if carp_bin_dir:
        command += ["--carp-bin-dir", str(carp_bin_dir)]
    return command


def myomesh_command(
    *,
    input_mat: str | Path,
    python_executable: str = "python",
    no_alg: bool = False,
    no_align_dicom: bool = False,
    extra_args: tuple[str, ...] = (),
) -> list[str]:
    require_tool_policy("myomesh")
    command = [
        python_executable,
        "execAll.py",
        "-i",
        str(input_mat),
    ]
    if no_alg:
        command.append("--no_alg")
    if no_align_dicom:
        command.append("--no_align_dicom")
    command.extend(str(item) for item in extra_args)
    return command


def meshtool_command(
    *,
    operation: str,
    input_mesh: str | Path,
    output_mesh: str | Path | None = None,
    extra_args: tuple[str, ...] = (),
    executable: str = "meshtool",
) -> list[str]:
    require_tool_policy("meshtool")
    command = [
        executable,
        operation,
        "-msh=" + str(input_mesh),
    ]
    if output_mesh is not None:
        command.append("-outmsh=" + str(output_mesh))
    command.extend(str(item) for item in extra_args)
    return command


def ldrb_command(
    *,
    mesh_path: str | Path,
    markers_file: str | Path,
    alpha_endo_lv: float = 60.0,
    alpha_epi_lv: float = -60.0,
    fiber_space: str = "P_1",
    executable: str = "ldrb",
) -> list[str]:
    require_tool_policy("fenicsx_ldrb")
    return [
        executable,
        str(mesh_path),
        "--markers-file",
        str(markers_file),
        "--fiber-space",
        fiber_space,
        "--alpha-endo-lv",
        str(alpha_endo_lv),
        "--alpha-epi-lv",
        str(alpha_epi_lv),
    ]


def geox_command(*args: str, executable: str = "geox") -> list[str]:
    require_tool_policy("cardiac_geometriesx")
    return [executable, *[str(item) for item in args]]
