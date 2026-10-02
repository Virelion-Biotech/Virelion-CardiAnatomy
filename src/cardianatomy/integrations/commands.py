from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

import numpy as np
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Mapping, Sequence

from .catalog import require_tool_policy


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    executable: str | None


def executable_available(executable: str) -> bool:
    resolved = shutil.which(executable)
    if resolved is not None:
        return True
    path = Path(executable)
    return path.is_file() and os.access(path, os.X_OK)


def run_command(
    command: Sequence[str],
    *,
    timeout: float = 3600.0,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    max_output_chars: int = 1_000_000,
) -> CommandResult:
    if not command:
        raise ValueError("command must not be empty")
    if not np.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and strictly positive")
    if (
        isinstance(max_output_chars, bool)
        or not isinstance(max_output_chars, int)
        or max_output_chars < 1
    ):
        raise ValueError("max_output_chars must be a positive integer")
    argv = [str(item) for item in command]
    executable = shutil.which(argv[0])
    direct = Path(argv[0])
    if executable is None:
        if not direct.is_file():
            raise FileNotFoundError(f"Executable not found: {argv[0]}")
        if not os.access(direct, os.X_OK):
            raise PermissionError(f"File is not executable: {argv[0]}")
    process_env = os.environ.copy()
    if env:
        process_env.update({str(key): str(value) for key, value in env.items()})
    def read_bounded(handle) -> str:
        handle.seek(0)
        value = handle.read(max_output_chars + 1)
        if len(value) <= max_output_chars:
            return value
        return value[:max_output_chars] + "\n...[output truncated]"

    started = perf_counter()
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as stdout_file:
        with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as stderr_file:
            process = subprocess.run(
                argv,
                cwd=None if cwd is None else str(cwd),
                env=process_env,
                stdout=stdout_file,
                stderr=stderr_file,
                timeout=timeout,
                check=False,
                shell=False,
            )
            stdout = read_bounded(stdout_file)
            stderr = read_bounded(stderr_file)
    result = CommandResult(
        command=tuple(argv),
        returncode=process.returncode,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=perf_counter() - started,
        executable=executable or str(Path(argv[0]).resolve()),
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


def morphinet_inference_command(
    *,
    main_script: str | Path,
    test_dataset: str,
    template_mesh: str | Path,
    checkpoint_dir: str | Path,
    output_root: str | Path,
    ct_data_dir: str | Path | None = None,
    mr_data_dir: str | Path | None = None,
    ct_json: str | Path | None = None,
    mr_json: str | Path | None = None,
    python_executable: str = "python",
) -> list[str]:
    require_tool_policy("morphinetv2")
    allowed = {"acdc", "mmwhs", "cap", "scotheart"}
    if test_dataset not in allowed:
        raise ValueError(
            f"test_dataset must be one of {sorted(allowed)}"
        )
    command = [
        python_executable,
        str(main_script),
        "--inference_only",
        "--mode",
        "disabled",
        "--test_dataset",
        test_dataset,
        "--template_mesh_dir",
        str(template_mesh),
        "--use_ckpt",
        str(checkpoint_dir),
        "--output_root",
        str(output_root),
    ]
    optional = (
        ("--ct_data_dir", ct_data_dir),
        ("--mr_data_dir", mr_data_dir),
        ("--ct_json_dir", ct_json),
        ("--mr_json_dir", mr_json),
    )
    for flag, value in optional:
        if value is not None:
            command += [flag, str(value)]
    return command


def bipt_inference_command(
    *,
    infer_script: str | Path,
    checkpoint: str | Path,
    atlas_path: str | Path,
    output_dir: str | Path,
    spc: str | Path | None = None,
    spc_dir: str | Path | None = None,
    label_dim: int = 2,
    which_output: str = "l2",
    eval_cd: str = "none",
    strict_arch: bool = True,
    python_executable: str = "python",
) -> list[str]:
    require_tool_policy("bi-pt")
    if (spc is None) == (spc_dir is None):
        raise ValueError("Provide exactly one of spc or spc_dir")
    if label_dim not in {2, 3}:
        raise ValueError("label_dim must be 2 or 3")
    if which_output not in {"l1", "l2", "both"}:
        raise ValueError("which_output must be l1, l2, or both")
    if eval_cd not in {"none", "plain", "label", "pair2", "both", "three"}:
        raise ValueError("Unsupported Bi-PT eval_cd mode")

    atlas_flag = "--atlas-path-2" if label_dim == 2 else "--atlas-path-3"
    command = [
        python_executable,
        str(infer_script),
        "--ckpt",
        str(checkpoint),
        atlas_flag,
        str(atlas_path),
        "--label-dim",
        str(label_dim),
        "--out-dir",
        str(output_dir),
        "--which-output",
        which_output,
        "--eval-cd",
        eval_cd,
    ]
    if spc is not None:
        command += ["--spc", str(spc)]
    else:
        command += ["--spc-dir", str(spc_dir)]
    if strict_arch:
        command.append("--strict-arch")
    return command
