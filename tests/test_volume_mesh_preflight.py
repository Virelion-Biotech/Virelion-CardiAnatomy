from __future__ import annotations
import json
import numpy as np
import pytest
nib = pytest.importorskip("nibabel")
from cardianatomy.volume_mesh_preflight import validate_volume_mesh_inputs

def make_views(tmp_path, orientations=None):
    orientations = orientations or {}
    out = {}
    for name in ("SAX","LAX_2CH","LAX_3CH","LAX_4CH"):
        affine = np.eye(4)
        affine[:3,:3] = orientations.get(name, np.eye(3))
        path = tmp_path / f"{name}.nii.gz"
        nib.save(nib.Nifti1Image(np.zeros((8,9,10), dtype=np.uint8), affine), path)
        out[name] = path
    return out

def test_preflight_records_hashes_and_explicitly_does_not_claim_registration(tmp_path):
    views = make_views(tmp_path)
    dest = tmp_path / "manifest.json"
    result = validate_volume_mesh_inputs(views, output_manifest=dest)
    saved = json.loads(dest.read_text())
    assert result["status"] == "preflight_passed_registration_unverified"
    assert set(result["inputs"]) == {"SAX","LAX_2CH","LAX_3CH","LAX_4CH"}
    assert all(len(x["sha256"]) == 64 for x in result["inputs"].values())
    assert saved["checks"]["spatial_registration_verified"] is False
    assert saved["checks"]["mesh_quality_verified"] is False
    assert str(tmp_path) not in dest.read_text()

def test_rejects_missing_view(tmp_path):
    views = make_views(tmp_path)
    with pytest.raises(ValueError, match="Expected exactly"):
        validate_volume_mesh_inputs({k:v for k,v in views.items() if k != "LAX_4CH"})

def test_rejects_inconsistent_axis_codes(tmp_path):
    views = make_views(tmp_path, {"LAX_4CH":np.diag([-1.,1.,1.])})
    with pytest.raises(ValueError, match="inconsistent affine axis-code"):
        validate_volume_mesh_inputs(views)

def test_refuses_to_overwrite_manifest(tmp_path):
    views = make_views(tmp_path)
    dest = tmp_path / "manifest.json"
    dest.write_text("preserve")
    with pytest.raises(ValueError, match="Refusing to overwrite"):
        validate_volume_mesh_inputs(views, output_manifest=dest)
    assert dest.read_text() == "preserve"

def test_rejects_missing_file(tmp_path):
    views = make_views(tmp_path)
    views["SAX"] = tmp_path / "missing.nii.gz"
    with pytest.raises(ValueError, match="not a readable file"):
        validate_volume_mesh_inputs(views)
