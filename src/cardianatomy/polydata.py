"""Geometry-only reader for bounded legacy ASCII triangular VTK POLYDATA."""

from pathlib import Path

import numpy as np


def read_triangle_polydata(path):
    path = Path(path)
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("Legacy POLYDATA exceeds the 64 MiB reader limit")
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 5 or not lines[0].startswith("# vtk DataFile Version"):
        raise ValueError("Invalid legacy VTK header")
    if lines[2].strip() != "ASCII" or lines[3].strip() != "DATASET POLYDATA":
        raise ValueError("Only legacy ASCII POLYDATA is supported by this reader")
    tokens = iter(" ".join(lines[4:]).split())
    try:
        if next(tokens) != "POINTS":
            raise ValueError("POLYDATA must start with POINTS")
        count = int(next(tokens))
        if not 1 <= count <= 1_000_000:
            raise ValueError("POLYDATA point count outside supported range")
        next(tokens)  # scalar type, coordinates converted explicitly below
        points = np.fromiter(
            (float(next(tokens)) for _ in range(count * 3)), dtype=float, count=count * 3
        ).reshape(count, 3)
        if next(tokens) != "POLYGONS":
            raise ValueError("Only triangular POLYGONS are supported")
        polygons, total = int(next(tokens)), int(next(tokens))
        if not 1 <= polygons <= 2_000_000 or total != 4 * polygons:
            raise ValueError("POLYDATA requires nonempty triangular polygons")
        cells = np.fromiter(
            (int(next(tokens)) for _ in range(total)), dtype=np.int64, count=total
        ).reshape(polygons, 4)
        if not np.all(cells[:, 0] == 3):
            raise ValueError("Only triangular POLYGONS are supported")
    except (StopIteration, RuntimeError, OverflowError) as exc:
        raise ValueError("Truncated or invalid POLYDATA geometry") from exc
    # Attribute arrays are deliberately not interpreted as cardiac structure labels.
    return points, cells[:, 1:]
