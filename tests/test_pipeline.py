from pathlib import Path

from cardianatomy import (
    AnatomyRequest,
    ArtifactRef,
    ImagingAcquisition,
    PipelineExecutor,
    PipelinePlan,
)
from cardianatomy.backends import StageOutput


class SegmentationBackend:
    name = "fixture"
    stage = "segmentation"

    def available(self) -> bool:
        return True

    def run(self, request, bundle, workdir: Path, parameters):
        return StageOutput(
            artifacts=[
                ArtifactRef(
                    artifact_id="seg",
                    kind="segmentation",
                    uri=str(workdir / "seg.nii.gz"),
                    producer=self.name,
                )
            ]
        )


def test_pipeline_executor_records_stage(tmp_path) -> None:
    acquisition = ImagingAcquisition(
        subject_id="S1",
        study_id="ST1",
        acquisition_id="A1",
        modality="CMR",
        source=ArtifactRef(artifact_id="raw", kind="nifti_image", uri="file:///raw.nii.gz"),
    )
    request = AnatomyRequest(subject_id="S1", acquisition=acquisition, output_root=str(tmp_path))
    executor = PipelineExecutor()
    executor.register(SegmentationBackend())
    bundle = executor.execute(
        request,
        PipelinePlan(stages=["segmentation"], backends={"segmentation": "fixture"}),
    )
    assert bundle.stages[0].status == "ok"
    assert "segmentation" in bundle.artifact_kinds()
    assert bundle.bundle_fingerprint
