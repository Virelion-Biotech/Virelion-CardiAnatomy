from cardianatomy import AnatomyBundle, ArtifactRef, GeometryQC


def artifact(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=f"a-{kind}", kind=kind, uri=f"file:///{kind}")


def test_bundle_readiness_requires_core_geometry_and_qc() -> None:
    bundle = AnatomyBundle(
        subject_id="S1",
        study_id="ST1",
        acquisition_id="A1",
        artifacts=[
            artifact("segmentation"),
            artifact("surface_mesh"),
            artifact("volume_mesh"),
        ],
        qc=GeometryQC(passed=True, checks={"mesh_nonempty": True}),
    )
    assert bundle.ready


def test_bundle_without_qc_is_not_ready() -> None:
    bundle = AnatomyBundle(
        subject_id="S1",
        study_id="ST1",
        acquisition_id="A1",
        artifacts=[artifact("segmentation")],
    )
    assert not bundle.ready
