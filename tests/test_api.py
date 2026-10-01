from cardianatomy import AnatomyAPI


def test_health_has_versioned_capabilities() -> None:
    health = AnatomyAPI().health()
    assert health["contract_version"] == "2.0.0"
    assert "anatomy.build" in health["capabilities"]


def test_tools_marks_restricted_integrations() -> None:
    tools = {item["tool_id"]: item for item in AnatomyAPI().tools()["tools"]}
    assert tools["augmenta"]["license_class"] == "restricted"


def test_presets_expose_biventricular_and_ep_workflows() -> None:
    presets = AnatomyAPI().presets()["presets"]
    assert "cine_cmr_biventricular" in presets
    assert "presegmented_ep" in presets


def test_rigid_registration_api_returns_low_residual() -> None:
    source = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
    target = [[2, 3, 4], [3, 3, 4], [2, 4, 4]]
    result = AnatomyAPI().registration_rigid(
        {"source_points": source, "target_points": target}
    )
    assert result["rms_error"] < 1e-10


def test_segmentation_qc_api() -> None:
    result = AnatomyAPI().segmentation_qc(
        {
            "labels": [[[0, 1], [0, 1]], [[0, 1], [0, 1]]],
            "required_labels": [0, 1],
        }
    )
    assert result["passed"]


def test_manifest_audit_flags_unknown_license() -> None:
    result = AnatomyAPI().manifest_audit(
        {
            "tools": [{"tool_id": "cemrg-heartbuilder"}],
            "allow_restricted": True,
        }
    )
    assert not result["valid"]


def test_cine_phase_api_from_volume_curve() -> None:
    result = AnatomyAPI().cine_phases(
        {"volumes_ml": [120.0, 95.0, 70.0, 85.0, 110.0]}
    )
    assert result["ed_phase"] == 0
    assert result["es_phase"] == 2
    assert result["validation_status"] == "segmentation_derived_only"


def test_transform_api_composes_and_inverts() -> None:
    translate = [
        [1.0, 0.0, 0.0, 2.0],
        [0.0, 1.0, 0.0, -1.0],
        [0.0, 0.0, 1.0, 3.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
    composed = AnatomyAPI().transforms_compose(
        {"matrices": [translate]}
    )["matrix"]
    inverse = AnatomyAPI().transforms_invert(
        {"matrix": composed}
    )["matrix"]
    assert inverse[0][3] == -2.0
    assert inverse[1][3] == 1.0
    assert inverse[2][3] == -3.0


def test_correspondence_api_reports_connectivity() -> None:
    result = AnatomyAPI().correspondence_compare(
        {
            "reference_points": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
            "target_points": [[1, 0, 0], [2, 0, 0], [1, 1, 0]],
            "reference_cells": [[0, 1, 2]],
            "target_cells": [[0, 1, 2]],
        }
    )
    assert result["connectivity_identical"] is True
    assert result["validation_status"] == "index_correspondence_assumed"


def test_motion_api_reports_cyclic_closure() -> None:
    result = AnatomyAPI().motion_summarize(
        {
            "frames": [
                [[0, 0, 0], [1, 0, 0]],
                [[0.5, 0, 0], [1.5, 0, 0]],
                [[0, 0, 0], [1, 0, 0]],
            ],
            "cyclic": True,
        }
    )
    assert result["phase_count"] == 3
    assert result["cyclic_closure_error"]["max"] == 0.0


def test_segmentation_validation_api() -> None:
    result = AnatomyAPI().validation_segmentation(
        {
            "reference_labels": [1, 1, 0, 0],
            "prediction_labels": [1, 0, 0, 0],
        }
    )
    assert abs(result["metrics"]["1"]["dice"] - (2.0 / 3.0)) < 1e-12
    assert result["validation_status"] == "reference_dependent"


def test_point_validation_api() -> None:
    result = AnatomyAPI().validation_points(
        {
            "reference_points": [[0, 0, 0], [1, 0, 0]],
            "prediction_points": [[1, 0, 0], [2, 0, 0]],
            "units": "mm",
            "block_size": 1,
        }
    )
    assert result["hausdorff"] == 1.0
    assert result["units"] == "mm"
