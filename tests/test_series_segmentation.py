import numpy as np

from cardianatomy import (
    DicomSeriesSummary,
    classify_cine_series,
    label_volumes_ml,
    segmentation_qc,
)


def test_metadata_series_classifier_is_explicitly_heuristic() -> None:
    summary = DicomSeriesSummary(
        series_uid_sha256="0" * 64,
        description="cine short axis",
        file_count=25,
        temporal_positions=25,
    )
    candidate = classify_cine_series(summary)
    assert candidate.predicted_view == "SAX"
    assert candidate.confidence == "metadata_supported"


def test_segmentation_volume_and_qc() -> None:
    labels = np.zeros((2, 2, 2), dtype=np.uint8)
    labels[0] = 1
    volumes = label_volumes_ml(labels, (1.0, 1.0, 1.0))
    assert volumes[1] == 0.004
    qc = segmentation_qc(labels, required_labels={0, 1})
    assert qc["passed"]


def test_volume_rejects_unsliced_4d_cine_segmentation() -> None:
    labels = np.zeros((2, 2, 2, 3), dtype=np.uint8)
    try:
        label_volumes_ml(labels, (1.0, 1.0, 1.0, 40.0))
    except ValueError as exc:
        assert "select a cine phase" in str(exc)
    else:
        raise AssertionError("4D cine segmentation should require phase selection")
