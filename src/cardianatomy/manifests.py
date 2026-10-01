from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .integrations import tool_spec
from .provenance import sha256


class ExternalAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str
    kind: str
    source: str
    version: str | None = None
    sha256: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-fA-F]{64}$",
    )
    license_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolchainEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_id: str
    version: str | None = None
    executable: str | None = None
    image: str | None = None
    commit: str | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)


class ToolchainManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    tools: list[ToolchainEntry] = Field(default_factory=list)
    assets: list[ExternalAsset] = Field(default_factory=list)
    environment: dict[str, str] = Field(default_factory=dict)
    manifest_sha256: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-fA-F]{64}$",
    )

    @model_validator(mode="after")
    def validate_manifest_integrity(self) -> "ToolchainManifest":
        tool_ids = [item.tool_id for item in self.tools]
        if len(tool_ids) != len(set(tool_ids)):
            raise ValueError("toolchain manifest contains duplicate tool_id values")
        asset_ids = [item.asset_id for item in self.assets]
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("toolchain manifest contains duplicate asset_id values")
        sensitive_tokens = (
            "token",
            "password",
            "passwd",
            "secret",
            "api_key",
            "apikey",
            "credential",
            "authorization",
        )
        sensitive = sorted(
            key
            for key in self.environment
            if any(token in key.lower() for token in sensitive_tokens)
        )
        if sensitive:
            raise ValueError(
                "toolchain manifest environment must not store credentials: "
                + ", ".join(sensitive)
            )
        return self

    def finalized(self) -> "ToolchainManifest":
        payload = self.model_dump(
            mode="json",
            exclude={"manifest_sha256", "created_at"},
        )
        return self.model_copy(update={"manifest_sha256": sha256(payload)})


def audit_manifest_licenses(
    manifest: ToolchainManifest,
    *,
    allow_restricted: bool = False,
) -> list[str]:
    problems: list[str] = []
    for entry in manifest.tools:
        try:
            spec = tool_spec(entry.tool_id)
        except KeyError:
            problems.append(f"Unknown external tool: {entry.tool_id}")
            continue
        if spec.license_class == "unknown":
            problems.append(
                f"{entry.tool_id}: license terms are unresolved "
                f"({spec.license_name})"
            )
        elif not spec.default_allowed and not allow_restricted:
            problems.append(
                f"{entry.tool_id}: deployment review required "
                f"({spec.license_name})"
            )
    for asset in manifest.assets:
        if not asset.sha256:
            problems.append(
                f"{asset.asset_id}: external asset is missing SHA-256"
            )
        if not asset.license_name:
            problems.append(
                f"{asset.asset_id}: external asset license is not recorded"
            )
    return problems
