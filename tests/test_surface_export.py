import json

import meshio
import numpy as np

from cardianatomy.cli import main
from cardianatomy.polydata import read_triangle_polydata


def test_export_surface_from_tetra_volume_and_cli(tmp_path, capsys):
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    source = tmp_path / "volume.vtu"
    output = tmp_path / "surface.vtk"
    meshio.write_points_cells(source, points, [("tetra", np.array([[0, 1, 2, 3]]))])

    assert main(["export-surface", str(source), str(output)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["geometry_only"] is True
    assert result["surface_triangle_count"] == 4
    assert result["output_format"] == "legacy_ascii_vtk_polydata"

    rendered_points, triangles = read_triangle_polydata(output)
    assert rendered_points.shape == (4, 3)
    assert triangles.shape == (4, 3)
    assert output.read_text().splitlines()[3] == "DATASET POLYDATA"


def test_export_surface_removes_internal_shared_face(tmp_path):
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, -1.0],
        ]
    )
    source = tmp_path / "two-tetra.vtu"
    output = tmp_path / "outside.vtk"
    meshio.write_points_cells(
        source,
        points,
        [("tetra", np.array([[0, 1, 2, 3], [0, 2, 1, 4]]))],
    )

    from cardianatomy.surface_export import export_surface_mesh

    result = export_surface_mesh(source, output)
    assert result["surface_triangle_count"] == 6
    _, triangles = read_triangle_polydata(output)
    assert triangles.shape == (6, 3)


def test_export_surface_requires_vtk_output(tmp_path):
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    source = tmp_path / "volume.vtu"
    meshio.write_points_cells(source, points, [("tetra", np.array([[0, 1, 2, 3]]))])

    from cardianatomy.surface_export import export_surface_mesh

    try:
        export_surface_mesh(source, tmp_path / "surface.stl")
    except ValueError as exc:
        assert "Output must use the .vtk extension" in str(exc)
    else:
        raise AssertionError("Unsupported output format was accepted")
