import os
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from cardianatomy import (
    ExternalAsset,
    ToolchainEntry,
    ToolchainManifest,
    audit_manifest_licenses,
)
from cardianatomy.integrations import (
    executable_available,
    run_command,
)


def test_run_command_does_not_interpret_shell_metacharacters(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "should-not-exist"
    payload = f"$(touch {marker}); touch {marker}; && touch {marker}"
    result = run_command(
        [
            sys.executable,
            "-c",
            "import sys; print(sys.argv[1])",
            payload,
        ]
    )
    assert result.stdout.strip() == payload
    assert not marker.exists()


def test_run_command_environment_is_explicitly_merged() -> None:
    result = run_command(
        [
            sys.executable,
            "-c",
            "import os; print(os.environ['CARDIANATOMY_STRESS'])",
        ],
        env={"CARDIANATOMY_STRESS": "isolated-value"},
    )
    assert result.stdout.strip() == "isolated-value"


@pytest.mark.parametrize("timeout", [0.0, -1.0, float("nan"), float("inf")])
def test_run_command_rejects_invalid_timeout(timeout: float) -> None:
    with pytest.raises(ValueError, match="timeout"):
        run_command([sys.executable, "-c", "print('x')"], timeout=timeout)


def test_run_command_timeout_is_enforced() -> None:
    with pytest.raises(subprocess.TimeoutExpired):
        run_command(
            [sys.executable, "-c", "import time; time.sleep(1)"],
            timeout=0.02,
        )


def test_run_command_nonzero_exit_is_not_silenced() -> None:
    with pytest.raises(RuntimeError, match="Command failed"):
        run_command(
            [
                sys.executable,
                "-c",
                "import sys; print('boom', file=sys.stderr); sys.exit(7)",
            ]
        )


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable-bit semantics")
def test_non_executable_file_is_not_reported_available(tmp_path: Path) -> None:
    path = tmp_path / "not-executable"
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o600)
    assert not executable_available(str(path))
    with pytest.raises(PermissionError):
        run_command([str(path)])


def test_manifest_rejects_duplicate_tools() -> None:
    with pytest.raises(ValidationError, match="duplicate tool_id"):
        ToolchainManifest(
            tools=[
                ToolchainEntry(tool_id="nnunet"),
                ToolchainEntry(tool_id="nnunet"),
            ]
        )


def test_manifest_rejects_duplicate_assets() -> None:
    asset = ExternalAsset(
        asset_id="weights",
        kind="model_weights",
        source="local://weights",
        sha256="a" * 64,
        license_name="example",
    )
    with pytest.raises(ValidationError, match="duplicate asset_id"):
        ToolchainManifest(assets=[asset, asset.model_copy()])


@pytest.mark.parametrize(
    "key",
    [
        "API_TOKEN",
        "password",
        "my_secret",
        "SERVICE_API_KEY",
        "authorization",
        "db_credential",
    ],
)
def test_manifest_rejects_credential_like_environment_keys(key: str) -> None:
    with pytest.raises(ValidationError, match="credentials"):
        ToolchainManifest(environment={key: "do-not-store-this"})


def test_manifest_allows_nonsecret_reproducibility_environment() -> None:
    manifest = ToolchainManifest(
        environment={
            "CUDA_VISIBLE_DEVICES": "0",
            "OMP_NUM_THREADS": "4",
        }
    )
    assert manifest.environment["OMP_NUM_THREADS"] == "4"


def test_asset_sha256_must_be_hex_digest() -> None:
    with pytest.raises(ValidationError):
        ExternalAsset(
            asset_id="weights",
            kind="model_weights",
            source="local://weights",
            sha256="z" * 64,
            license_name="example",
        )


def test_audit_still_flags_missing_asset_provenance() -> None:
    manifest = ToolchainManifest(
        assets=[
            ExternalAsset(
                asset_id="weights",
                kind="model_weights",
                source="local://weights",
            )
        ]
    )
    problems = audit_manifest_licenses(manifest)
    assert any("missing SHA-256" in item for item in problems)
    assert any("license is not recorded" in item for item in problems)
