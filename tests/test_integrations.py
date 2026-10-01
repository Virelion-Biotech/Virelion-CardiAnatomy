import pytest

from cardianatomy.integrations import (
    biv_me_command,
    nnunet_predict_command,
    require_tool_policy,
    tool_catalog,
)


def test_catalog_exposes_license_policy() -> None:
    tools = {tool.tool_id: tool for tool in tool_catalog()}
    assert tools["nnunet"].default_allowed
    assert not tools["augmenta"].default_allowed


def test_restricted_tool_requires_explicit_policy() -> None:
    with pytest.raises(PermissionError):
        require_tool_policy("augmenta")


def test_command_builders_do_not_use_shell_strings() -> None:
    nn = nnunet_predict_command(input_dir="in", output_dir="out", dataset="100")
    assert nn[:2] == ["nnUNetv2_predict", "-i"]
    biv = biv_me_command(main_script="main.py", config_file="config.toml", case_name="case1")
    assert biv == ["python", "main.py", "-config", "config.toml", "-case", "case1"]
