from cardianatomy import AnatomyAPI


def test_health_has_versioned_capabilities() -> None:
    health = AnatomyAPI().health()
    assert health["contract_version"] == "2.0.0"
    assert "anatomy.build" in health["capabilities"]


def test_tools_marks_restricted_integrations() -> None:
    tools = {item["tool_id"]: item for item in AnatomyAPI().tools()["tools"]}
    assert tools["augmenta"]["license_class"] == "restricted"


def test_presets_expose_biventricular_and_ep_workflows() -> None:
    presets = AnatomyAPI().presets()["presets"]
    assert "cine_cmr_biventricular" in presets
    assert "presegmented_ep" in presets


def test_rigid_registration_api_returns_low_residual() -> None:
    source = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
    target = [[2, 3, 4], [3, 3, 4], [2, 4, 4]]
    result = AnatomyAPI().registration_rigid(
        {"source_points": source, "target_points": target}
    )
    assert result["rms_error"] < 1e-10


def test_segmentation_qc_api() -> None:
    result = AnatomyAPI().segmentation_qc(
        {
            "labels": [[[0, 1], [0, 1]], [[0, 1], [0, 1]]],
            "required_labels": [0, 1],
        }
    )
    assert result["passed"]


def test_manifest_audit_flags_unknown_license() -> None:
    result = AnatomyAPI().manifest_audit(
        {
            "tools": [{"tool_id": "cemrg-heartbuilder"}],
            "allow_restricted": True,
        }
    )
    assert not result["valid"]
