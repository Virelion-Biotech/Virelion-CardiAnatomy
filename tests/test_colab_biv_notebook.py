from __future__ import annotations

import ast
import json
from pathlib import Path


NOTEBOOK = (
    Path(__file__).resolve().parents[1]
    / "notebooks"
    / "colab_biv_volumetric_end_to_end.ipynb"
)


def test_colab_notebook_is_valid_json_and_has_cells():
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    assert notebook["nbformat"] == 4
    assert notebook["cells"]
    assert any(
        cell.get("cell_type") == "markdown"
        and "end-to-end BiV volumetric meshing" in "".join(cell.get("source", []))
        for cell in notebook["cells"]
    )


def test_all_python_code_cells_parse_without_colab_execution():
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    for index, cell in enumerate(notebook["cells"]):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        # The notebook intentionally uses regular Python cells, no IPython magic syntax.
        ast.parse(source, filename=f"colab_cell_{index}")


def test_notebook_lets_user_choose_data_and_keeps_license_gate():
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") in {"code", "markdown"}
    )
    assert "SAX_PATH" in source
    assert "MODEL_ASSET_SOURCE" in source
    assert "DATA_TERMS_REVIEWED" in source
    assert "OPENCARP_TERMS_REVIEWED" in source
    assert "run-manifest.json" in source
    assert "https://opencarp.org/download/license" in source
