import numpy as np

from cardianatomy import (
    bounding_box,
    tetrahedral_volume,
    triangle_surface_area,
)


def test_tetrahedral_volume_and_bounds() -> None:
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    tetrahedra = np.array([[0, 1, 2, 3]])
    assert np.isclose(tetrahedral_volume(points, tetrahedra), 1.0 / 6.0)
    box = bounding_box(points)
    assert box["min"] == [0.0, 0.0, 0.0]
    assert box["max"] == [1.0, 1.0, 1.0]


def test_triangle_surface_area() -> None:
    points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    triangles = np.array([[0, 1, 2]])
    assert np.isclose(triangle_surface_area(points, triangles), 0.5)
