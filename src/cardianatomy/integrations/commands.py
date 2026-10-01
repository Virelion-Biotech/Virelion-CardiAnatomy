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
    )
    result = CommandResult(
        tuple(str(x) for x in command),
        process.returncode,
        process.stdout,
        process.stderr,
    )
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or f"Command failed: {' '.join(result.command)}")
    return result


def nnunet_predict_command(
    *,
    input_dir: str | Path,
    output_dir: str | Path,
    dataset: str,
    configuration: str = "3d_fullres",
    folds: Sequence[str] = ("all",),
    executable: str = "nnUNetv2_predict",
) -> list[str]:
    require_tool_policy("nnunet")
    return [
        executable,
        "-i",
        str(input_dir),
        "-o",
        str(output_dir),
        "-d",
        str(dataset),
        "-c",
        configuration,
        "-f",
        *[str(fold) for fold in folds],
    ]


def biv_me_command(
    *,
    main_script: str | Path,
    config_file: str | Path,
    case_name: str | None = None,
    python_executable: str = "python",
) -> list[str]:
    require_tool_policy("biv_me")
    command = [python_executable, str(main_script), "-config", str(config_file)]
    if case_name:
        command.extend(["-case", case_name])
    return command


def meshtool_command(executable: str, *arguments: str) -> list[str]:
    require_tool_policy("meshtool")
    return [executable, *arguments]
