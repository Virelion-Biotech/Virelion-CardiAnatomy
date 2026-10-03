from __future__ import annotations

from .models import PipelinePlan


def cine_cmr_biventricular_plan() -> PipelinePlan:
    return PipelinePlan(
        stages=[
            "ingest",
            "view_selection",
            "phase_harmonization",
            "segmentation",
            "contours",
            "surface_fit",
            "surface_mesh",
            "volume_mesh",
            "coordinates",
            "microstructure",
            "qc",
            "export",
        ],
        backends={
            "ingest": "native",
            "view_selection": "biv-me",
            "phase_harmonization": "biv-me",
            "segmentation": "nnunet",
            "contours": "biv-me",
            "surface_fit": "biv-me",
            "surface_mesh": "biv-me",
            "volume_mesh": "biv-volumetric-meshing",
            "coordinates": "biv-volumetric-meshing",
            "microstructure": "fenicsx-ldrb",
            "qc": "native",
            "export": "native",
        },
    )


def presegmented_ep_plan() -> PipelinePlan:
    return PipelinePlan(
        stages=[
            "surface_mesh",
            "volume_mesh",
            "coordinates",
            "microstructure",
            "qc",
            "export",
        ],
        backends={
            "surface_mesh": "external",
            "volume_mesh": "biv-volumetric-meshing",
            "coordinates": "biv-volumetric-meshing",
            "microstructure": "fenicsx-ldrb",
            "qc": "native",
            "export": "native",
        },
    )


def mesh_qc_only_plan() -> PipelinePlan:
    return PipelinePlan(
        stages=["qc"],
        backends={"qc": "native"},
    )


def preset_catalog() -> dict[str, PipelinePlan]:
    return {
        "cine_cmr_biventricular": cine_cmr_biventricular_plan(),
        "presegmented_ep": presegmented_ep_plan(),
        "mesh_qc_only": mesh_qc_only_plan(),
    }
