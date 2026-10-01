from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Mapping


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    executable: str | None


def run_command(
    command: list[str] | tuple[str, ...],
    *,
    cwd: str | Path | None = None,
    timeout: float = 3600.0,
    env: Mapping[str, str] | None = None,
    check: bool = True,
) -> CommandResult:
    if not command:
        raise ValueError("command must not be empty")
    argv = [str(item) for item in command]
    executable = shutil.which(argv[0])
    if executable is None:
        raise FileNotFoundError(f"Executable not found: {argv[0]}")
    process_env = os.environ.copy()
    if env:
        process_env.update({str(key): str(value) for key, value in env.items()})
    started = perf_counter()
    process = subprocess.run(
        argv,
        cwd=None if cwd is None else str(cwd),
        env=process_env,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
        check=False,
    )
    result = CommandResult(
        command=tuple(argv),
        returncode=int(process.returncode),
        stdout=process.stdout,
        stderr=process.stderr,
        duration_seconds=perf_counter() - started,
        executable=executable,
    )
    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"External command failed ({result.returncode}): "
            f"{' '.join(argv)}\n{message}"
        )
    return result
