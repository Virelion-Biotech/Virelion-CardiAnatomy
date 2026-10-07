import importlib.util
from pathlib import Path


def test_pinned_external_meshes_and_analytic_controls():
    path = Path(__file__).resolve().parents[1] / "scripts/run_cpu_validation.py"
    spec = importlib.util.spec_from_file_location("cpu_validation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.run_validation()
    assert report["status"] == "PASS"
    assert len(report["datasets"]) == 2
    assert not report["clinical_validation"]
