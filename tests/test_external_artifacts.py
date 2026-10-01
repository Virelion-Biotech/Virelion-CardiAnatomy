from pathlib import Path

from cardianatomy import (
    AnatomyRequest,
    ArtifactRef,
    CardiAnatomyService,
    ImagingAcquisition,
    PipelinePlan,
)


def test_external_artifact_stage_verifies_and_hashes_file(tmp_path: Path) -> None:
    mesh = tmp_path / "surface.vtk"
    mesh.write_text("fixture", encoding="utf-8")
    request = AnatomyRequest(
        subject_id="S1",
        acquisition=ImagingAcquisition(
            subject_id="S1",
            study_id="ST1",
            acquisition_id="A1",
            modality="CMR",
            source=ArtifactRef(
                artifact_id="seg",
                kind="segmentation",
                uri="file:///seg.nii.gz",
            ),
        ),
        output_root=str(tmp_path / "work"),
        plan=PipelinePlan(
            stages=["surface_mesh"],
            backends={"surface_mesh": "external"},
            stage_parameters={
                "surface_mesh": {
                    "path": str(mesh),
                    "artifact_id": "surface",
                    "producer": "fixture",
                    "frame_id": "model",
                }
            },
        ),
    )
    bundle = CardiAnatomyService().build(request)
    surface = next(item for item in bundle.artifacts if item.artifact_id == "surface")
    assert surface.sha256
    assert surface.size_bytes == len("fixture")
    assert surface.frame_id == "model"


def test_service_advertises_native_and_external_backends() -> None:
    backends = CardiAnatomyService().backends()
    assert "native" in backends["staged"]["qc"]
    assert "external" in backends["staged"]["surface_mesh"]
    assert "biv-me" in backends["monolithic"]
    assert "myomesh" in backends["monolithic"]
