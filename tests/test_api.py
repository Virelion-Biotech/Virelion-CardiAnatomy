from cardianatomy import AnatomyAPI


def test_health_has_versioned_capabilities() -> None:
    health = AnatomyAPI().health()
    assert health["contract_version"] == "2.0.0"
    assert "anatomy.build" in health["capabilities"]


def test_tools_marks_restricted_integrations() -> None:
    tools = {item["tool_id"]: item for item in AnatomyAPI().tools()["tools"]}
    assert tools["augmenta"]["license_class"] == "restricted"
