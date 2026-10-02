from pathlib import Path

import pytest

from cardianatomy import inspect_dicom_directory


def _write_minimal_dicom(
    path: Path,
    *,
    malformed_geometry: bool,
    series_uid: str | None = None,
    description: str = "stress cine",
) -> str:
    pytest.importorskip("pydicom")
    from pydicom.dataset import FileDataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, MRImageStorage, generate_uid

    series_uid = series_uid or generate_uid()
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = MRImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    dataset = FileDataset(
        str(path),
        {},
        file_meta=file_meta,
        preamble=b"\0" * 128,
    )
    dataset.SOPClassUID = MRImageStorage
    dataset.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    dataset.SeriesInstanceUID = series_uid
    dataset.Modality = "MR"
    dataset.SeriesDescription = description
    dataset.PatientName = "SECRET^PATIENT"
    dataset.PatientID = "SHOULD-NOT-LEAK"
    dataset.Rows = 16
    dataset.Columns = 16

    if malformed_geometry:
        dataset.PixelSpacing = [-1.0, 1.5]
        dataset.SliceThickness = -8.0
        dataset.ImageOrientationPatient = [1.0, 0.0, 0.0]
        dataset.NumberOfTemporalPositions = 0
    else:
        dataset.PixelSpacing = [1.25, 1.5]
        dataset.SliceThickness = 8.0
        dataset.ImageOrientationPatient = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        dataset.NumberOfTemporalPositions = 20

    dataset.save_as(str(path), enforce_file_format=True)
    return series_uid


def test_dicom_scan_survives_many_garbage_files(tmp_path: Path) -> None:
    for index in range(100):
        (tmp_path / f"garbage-{index:03d}.bin").write_bytes(
            b"not-a-dicom" + bytes([index % 255])
        )
    _write_minimal_dicom(tmp_path / "valid.dcm", malformed_geometry=False)

    summaries = inspect_dicom_directory(tmp_path)
    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.file_count == 1
    assert summary.pixel_spacing_mm == (1.25, 1.5)
    assert summary.temporal_positions == 20


def test_malformed_dicom_geometry_degrades_to_warnings(tmp_path: Path) -> None:
    _write_minimal_dicom(tmp_path / "malformed.dcm", malformed_geometry=True)

    summaries = inspect_dicom_directory(tmp_path)
    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.pixel_spacing_mm is None
    assert summary.slice_thickness_mm is None
    assert summary.temporal_positions is None
    assert summary.image_orientation_patient is None
    assert "invalid PixelSpacing" in summary.warnings
    assert "invalid SliceThickness" in summary.warnings
    assert "invalid NumberOfTemporalPositions" in summary.warnings
    assert "invalid ImageOrientationPatient" in summary.warnings


def test_dicom_inspection_does_not_expose_direct_patient_identifiers(
    tmp_path: Path,
) -> None:
    _write_minimal_dicom(tmp_path / "valid.dcm", malformed_geometry=False)
    payload = inspect_dicom_directory(tmp_path)[0].model_dump(mode="json")
    serialized = repr(payload)
    assert "SECRET" not in serialized
    assert "SHOULD-NOT-LEAK" not in serialized
    assert "PatientName" not in serialized
    assert "PatientID" not in serialized


def test_dicom_scan_of_pure_garbage_returns_empty_list(tmp_path: Path) -> None:
    for index in range(20):
        (tmp_path / f"bad-{index}.dcm").write_text("garbage", encoding="utf-8")
    assert inspect_dicom_directory(tmp_path) == []


def test_many_files_in_one_series_are_aggregated(tmp_path: Path) -> None:
    from pydicom.uid import generate_uid

    series_uid = generate_uid()
    for index in range(50):
        _write_minimal_dicom(
            tmp_path / f"cine-{index:03d}.dcm",
            malformed_geometry=False,
            series_uid=series_uid,
        )
    summaries = inspect_dicom_directory(tmp_path)
    assert len(summaries) == 1
    assert summaries[0].file_count == 50


def test_dicom_free_text_is_redacted_by_default(tmp_path: Path) -> None:
    _write_minimal_dicom(
        tmp_path / "phi-description.dcm",
        malformed_geometry=False,
        description="cine John Doe MRN-123456",
    )
    summary = inspect_dicom_directory(tmp_path)[0]
    assert summary.description is None


def test_dicom_free_text_requires_explicit_opt_in(tmp_path: Path) -> None:
    description = "cine John Doe MRN-123456"
    _write_minimal_dicom(
        tmp_path / "phi-description.dcm",
        malformed_geometry=False,
        description=description,
    )
    summary = inspect_dicom_directory(
        tmp_path,
        include_free_text=True,
    )[0]
    assert summary.description == description
