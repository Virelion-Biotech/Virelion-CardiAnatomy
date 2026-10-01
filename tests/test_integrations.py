import pytest

from cardianatomy.integrations import (
    biv_me_command,
    biv_volumetric_command,
    myomesh_command,
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


def test_biv_volumetric_command_is_explicit() -> None:
    command = biv_volumetric_command(
        run_script="run.py",
        data_dir="/data",
        components=("surface", "volumetric"),
        subject="S1",
    )
    assert command == [
        "python",
        "run.py",
        "--data-dir",
        "/data",
        "--surface",
        "--volumetric",
        "--subject",
        "S1",
    ]


def test_myomesh_command_uses_argument_array() -> None:
    command = myomesh_command(
        input_mat="patient.mat",
        no_alg=True,
        no_align_dicom=True,
    )
    assert command == [
        "python",
        "execAll.py",
        "-i",
        "patient.mat",
        "--no_alg",
        "--no_align_dicom",
    ]
