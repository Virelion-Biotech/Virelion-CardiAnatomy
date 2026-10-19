"""Stricter readiness checks for patient-specific electrophysiology.

Generic ``AnatomyBundle.ep_ready`` intentionally answers a solver-oriented
question: does the bundle contain the geometry/microstructure artifacts needed
by an EP consumer and did mesh QC pass?  Patient-specific use needs additional
evidence guarantees.  This module adds those guarantees without changing the
existing generic EP contract used by synthetic fixtures and integration tests.
"""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Iterable

from .models import AnatomyBundle, ArtifactRef

_PATIENT_EP_KINDS = (
    "segmentation",
    "volume_mesh",
    "coordinate_field",
    "fiber_field",
)
_ALLOWED_LENGTH_UNITS = {"mm", "cm", "m"}
_REVIEWED_SEGMENTATION_STATES = {"expert_reviewed", "expert_corrected"}


def _selected_artifact(
    bundle: AnatomyBundle,
    kind: str,
    issues: list[str],
) -> ArtifactRef | None:
    candidates = [artifact for artifact in bundle.artifacts if artifact.kind == kind]
    if not candidates:
        issues.append(f"patient EP requires a {kind} artifact")
        return None

    explicitly_selected = [
        artifact
        for artifact in candidates
        if artifact.metadata.get("selected_for_patient_model") is True
    ]
    if len(explicitly_selected) > 1:
        issues.append(
            f"multiple {kind} artifacts are selected_for_patient_model; selection is ambiguous"
        )
        return None
    if len(explicitly_selected) == 1:
        return explicitly_selected[0]
    if len(candidates) == 1:
        return candidates[0]

    issues.append(
        f"multiple {kind} artifacts exist; mark exactly one selected_for_patient_model=true"
    )
    return None


def _check_artifact_lineage(
    bundle: AnatomyBundle,
    artifact: ArtifactRef,
    issues: list[str],
) -> None:
    if artifact.sha256 is None:
        issues.append(f"artifact {artifact.artifact_id!r} is not SHA-256 pinned")
    identity = {
        "subject_id": (artifact.subject_id, bundle.subject_id),
        "study_id": (artifact.study_id, bundle.study_id),
        "acquisition_id": (artifact.acquisition_id, bundle.acquisition_id),
    }
    for field_name, (actual, expected) in identity.items():
        if actual is None:
            issues.append(
                f"artifact {artifact.artifact_id!r} does not declare {field_name}"
            )
        elif actual != expected:
            issues.append(
                f"artifact {artifact.artifact_id!r} {field_name}={actual!r} does not match "
                f"bundle {field_name}={expected!r}"
            )
    if not artifact.frame_id:
        issues.append(f"artifact {artifact.artifact_id!r} does not declare frame_id")


def _frame_graph(bundle: AnatomyBundle, issues: list[str]) -> dict[str, set[str]]:
    frame_ids = {frame.frame_id for frame in bundle.frames}
    graph: dict[str, set[str]] = defaultdict(set)

    for frame in bundle.frames:
        if frame.units not in _ALLOWED_LENGTH_UNITS:
            issues.append(
                f"coordinate frame {frame.frame_id!r} uses unsupported length units "
                f"{frame.units!r}; expected one of {sorted(_ALLOWED_LENGTH_UNITS)}"
            )
        if frame.parent_frame_id is not None:
            if frame.parent_frame_id not in frame_ids:
                issues.append(
                    f"coordinate frame {frame.frame_id!r} references unknown parent frame "
                    f"{frame.parent_frame_id!r}"
                )
            elif frame.affine_to_parent is None:
                issues.append(
                    f"coordinate frame {frame.frame_id!r} declares a parent but no "
                    "affine_to_parent"
                )
            else:
                graph[frame.frame_id].add(frame.parent_frame_id)
                graph[frame.parent_frame_id].add(frame.frame_id)

    for registration in bundle.registrations:
        source = registration.source_frame
        target = registration.target_frame
        if source not in frame_ids:
            issues.append(
                f"registration {registration.registration_id!r} references unknown source "
                f"frame {source!r}"
            )
        if target not in frame_ids:
            issues.append(
                f"registration {registration.registration_id!r} references unknown target "
                f"frame {target!r}"
            )
        if source in frame_ids and target in frame_ids:
            graph[source].add(target)
            graph[target].add(source)

    return graph


def _frames_connected(
    graph: dict[str, set[str]],
    source: str,
    target: str,
) -> bool:
    if source == target:
        return True
    queue: deque[str] = deque([source])
    seen = {source}
    while queue:
        current = queue.popleft()
        for neighbour in graph.get(current, set()):
            if neighbour == target:
                return True
            if neighbour not in seen:
                seen.add(neighbour)
                queue.append(neighbour)
    return False


def _require_declared_frames(
    bundle: AnatomyBundle,
    artifacts: Iterable[ArtifactRef],
    issues: list[str],
) -> None:
    frame_ids = {frame.frame_id for frame in bundle.frames}
    for artifact in artifacts:
        if artifact.frame_id and artifact.frame_id not in frame_ids:
            issues.append(
                f"artifact {artifact.artifact_id!r} references undeclared frame "
                f"{artifact.frame_id!r}"
            )


def patient_ep_readiness_issues(bundle: AnatomyBundle) -> list[str]:
    """Return blocking issues for patient-specific EP anatomy use.

    The result is deterministic and fail-closed.  An empty list means the
    anatomy bundle satisfies *software-level* patient EP provenance/readiness
    requirements; it does not establish anatomical accuracy or clinical
    validity.
    """
    bundle = AnatomyBundle.model_validate(bundle.model_dump(mode="json"))
    issues: list[str] = []

    if not bundle.ep_ready:
        issues.append(
            "bundle does not satisfy generic EP readiness (surface/volume mesh, coordinate "
            "field, fibre field, and volume-mesh QC are required)"
        )

    selected: dict[str, ArtifactRef] = {}
    for kind in _PATIENT_EP_KINDS:
        artifact = _selected_artifact(bundle, kind, issues)
        if artifact is not None:
            selected[kind] = artifact
            _check_artifact_lineage(bundle, artifact, issues)

    segmentation = selected.get("segmentation")
    if segmentation is not None:
        review_status = str(segmentation.metadata.get("review_status", "")).strip().lower()
        if review_status not in _REVIEWED_SEGMENTATION_STATES:
            issues.append(
                "selected segmentation must declare metadata.review_status as "
                "expert_reviewed or expert_corrected"
            )
        reviewer_role = segmentation.metadata.get("reviewer_role")
        if not isinstance(reviewer_role, str) or not reviewer_role.strip():
            issues.append(
                "selected segmentation must declare a non-empty metadata.reviewer_role"
            )

    if not bundle.frames:
        issues.append("patient EP bundle must declare coordinate frames")
        return sorted(set(issues))

    graph = _frame_graph(bundle, issues)
    _require_declared_frames(bundle, selected.values(), issues)

    if segmentation is not None and segmentation.frame_id:
        for kind in ("volume_mesh", "coordinate_field", "fiber_field"):
            artifact = selected.get(kind)
            if artifact is None or not artifact.frame_id:
                continue
            if not _frames_connected(graph, segmentation.frame_id, artifact.frame_id):
                issues.append(
                    f"no traceable coordinate-frame path connects segmentation frame "
                    f"{segmentation.frame_id!r} to selected {kind} frame "
                    f"{artifact.frame_id!r}"
                )

    volume_mesh = selected.get("volume_mesh")
    if volume_mesh is not None and bundle.qc is not None:
        if bundle.qc.artifact_id not in {None, volume_mesh.artifact_id}:
            issues.append(
                "bundle QC does not cover the selected patient-model volume mesh"
            )

    return sorted(set(issues))


def patient_ep_ready(bundle: AnatomyBundle) -> bool:
    """Whether ``bundle`` passes the stricter patient-specific EP gate."""
    return not patient_ep_readiness_issues(bundle)
