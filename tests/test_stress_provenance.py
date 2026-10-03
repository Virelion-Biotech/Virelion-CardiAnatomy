from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from cardianatomy import (
    ExternalAsset,
    ToolchainEntry,
    ToolchainManifest,
    canonical_json,
    file_sha256,
    sha256,
)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_canonical_json_rejects_nonstandard_numbers(value: float) -> None:
    with pytest.raises(ValueError):
        canonical_json({"value": value})


@pytest.mark.parametrize("chunk_size", [0, -1, True, 1.5])
def test_file_hash_rejects_invalid_chunk_size(
    tmp_path: Path,
    chunk_size,
) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"abcdef")
    with pytest.raises(ValueError):
        file_sha256(path, chunk_size=chunk_size)


def test_file_hash_is_independent_of_valid_chunk_size(tmp_path: Path) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"abcdef" * 10000)
    expected = file_sha256(path, chunk_size=1)
    assert file_sha256(path, chunk_size=17) == expected
    assert file_sha256(path, chunk_size=4096) == expected


def test_sha256_is_deterministic_for_dict_key_order() -> None:
    assert sha256({"a": 1, "b": 2}) == sha256({"b": 2, "a": 1})


def test_finalized_manifest_round_trip_verifies_hash() -> None:
    manifest = ToolchainManifest(
        tools=[
            ToolchainEntry(
                tool_id="nnunet",
                version="2",
                configuration={"dataset": "100"},
            )
        ],
        assets=[
            ExternalAsset(
                asset_id="weights",
                kind="model_weights",
                source="local://weights",
                sha256="a" * 64,
                license_name="example",
            )
        ],
        environment={"CUDA_VISIBLE_DEVICES": "0"},
    ).finalized()

    payload = manifest.model_dump(mode="json")
    restored = ToolchainManifest.model_validate(payload)
    assert restored.manifest_sha256 == manifest.manifest_sha256


def test_manifest_hash_detects_tampering() -> None:
    manifest = ToolchainManifest(
        tools=[ToolchainEntry(tool_id="nnunet", version="2")]
    ).finalized()
    payload = manifest.model_dump(mode="json")
    payload["tools"][0]["version"] = "tampered"

    with pytest.raises(ValidationError, match="does not match"):
        ToolchainManifest.model_validate(payload)


def test_manifest_hash_ignores_created_at_by_design() -> None:
    manifest = ToolchainManifest(
        tools=[ToolchainEntry(tool_id="nnunet")]
    ).finalized()
    payload = manifest.model_dump(mode="json")
    payload["created_at"] = "2030-01-01T00:00:00Z"
    restored = ToolchainManifest.model_validate(payload)
    assert restored.manifest_sha256 == manifest.manifest_sha256
