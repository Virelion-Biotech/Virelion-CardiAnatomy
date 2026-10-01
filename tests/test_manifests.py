from cardianatomy import (
    ExternalAsset,
    ToolchainEntry,
    ToolchainManifest,
    audit_manifest_licenses,
)


def test_manifest_requires_asset_license_and_digest() -> None:
    manifest = ToolchainManifest(
        tools=[ToolchainEntry(tool_id="nnunet", version="2")],
        assets=[
            ExternalAsset(
                asset_id="weights",
                kind="model_weights",
                source="example",
            )
        ],
    )
    problems = audit_manifest_licenses(manifest)
    assert any("SHA-256" in item for item in problems)
    assert any("license" in item for item in problems)


def test_restricted_tool_is_flagged() -> None:
    manifest = ToolchainManifest(
        tools=[ToolchainEntry(tool_id="augmenta")],
    )
    assert audit_manifest_licenses(manifest)
    assert not audit_manifest_licenses(manifest, allow_restricted=True)
