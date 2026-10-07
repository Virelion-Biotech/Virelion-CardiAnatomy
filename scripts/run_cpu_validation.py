"""CPU geometry/format validation with pinned public meshes and analytic controls."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import gzip
import hashlib
from importlib.metadata import version
from pathlib import Path
import platform
import tempfile

import numpy as np

from cardianatomy import __version__
from cardianatomy.geometry import closed_surface_signed_volume, tetrahedral_volume
from cardianatomy.io import inspect_mesh_file
from cardianatomy.polydata import read_triangle_polydata
from cardianatomy.qc import qc_from_inspection
from cardianatomy.registration import estimate_rigid_transform
from cardianatomy.serialization import read_json, write_json_atomic
from cardianatomy.validation import point_set_distance_summary, segmentation_overlap_metrics


def run_validation():
    root = Path(__file__).resolve().parents[1]
    datasets = read_json(root / "validation/data/manifest.json")["datasets"]
    reports = []
    with tempfile.TemporaryDirectory() as directory:
        for dataset in datasets:
            raw = gzip.decompress((root / "validation/data" / dataset["fixture"]).read_bytes())
            assert hashlib.sha256(raw).hexdigest() == dataset["sha256"]
            path = Path(directory) / dataset["fixture"].removesuffix(".gz")
            path.write_bytes(raw)
            inspection = inspect_mesh_file(path)
            inspection.path = None
            qc = qc_from_inspection(inspection, require_watertight=True)
            # The negative controls must remain rejected, not be silently repaired.
            assert not qc.passed
            if dataset["fixture"] == "lv.vtk.gz":
                assert inspection.point_count == 4396
                assert inspection.metadata["duplicate_cell_count"] == 14
                assert inspection.nonmanifold_edge_count == 15
                assert "no_duplicate_cells" in qc.errors
            else:
                points, _ = read_triangle_polydata(path)
                assert len(points) == 6155 and inspection.boundary_edge_count == 251
                assert "watertight" in qc.errors
                selection = points[::61][:100]
                displacement = np.array([7.0, -3.0, 2.0])
                registered = estimate_rigid_transform(selection, selection + displacement)
                assert registered.rms_error < 1e-10
            reports.append(
                {
                    "source": dataset,
                    "inspection": inspection.model_dump(mode="json"),
                    "qc": qc.model_dump(mode="json"),
                }
            )
    tetra = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    triangles = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
    volume = tetrahedral_volume(tetra, np.array([[0, 1, 2, 3]]))
    surface_volume = closed_surface_signed_volume(tetra, triangles)
    assert np.isclose(volume, 1 / 6) and np.isclose(surface_volume, 1 / 6)
    for scale in (1e-4, 1.0, 1e4):
        assert np.isclose(
            tetrahedral_volume(tetra * scale, np.array([[0, 1, 2, 3]])),
            volume * scale**3,
            rtol=1e-12,
            atol=0,
        )
    overlap = segmentation_overlap_metrics(np.array([1, 1, 0]), np.array([1, 0, 1]))[1]
    assert overlap["dice"] == 0.5 and np.isclose(overlap["jaccard"], 1 / 3)
    distance = point_set_distance_summary(tetra, tetra)
    assert distance.hausdorff == 0
    return {
        "version": __version__,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "dependencies": {name: version(name) for name in
                         ("numpy", "pydantic", "meshio", "nibabel", "pydicom")},
        "status": "PASS",
        "validation_type": "computational controls and external negative QC fixtures",
        "clinical_validation": False,
        "datasets": reports,
        "analytic_controls": {
            "tetra_volume": volume,
            "closed_surface_volume": surface_volume,
            "overlap": overlap,
            "self_distance": asdict(distance),
        },
        "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_sha256": {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((root / "src/cardianatomy").rglob("*.py"))
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="validation/cpu/results.json")
    args = parser.parse_args()
    write_json_atomic(args.output, run_validation())
    print(f"CPU controls passed; evidence: {args.output}")


if __name__ == "__main__":
    main()
