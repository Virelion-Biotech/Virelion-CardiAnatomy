from __future__ import annotations

import re
from dataclasses import dataclass

from .models import DicomSeriesSummary


@dataclass(frozen=True)
class SeriesCandidate:
    series_uid_sha256: str
    predicted_view: str
    confidence: str
    reasons: tuple[str, ...]


_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("SAX", re.compile(r"\b(sax|short[ _-]?axis)\b", re.I)),
    ("2CH", re.compile(r"\b(2ch|two[ _-]?chamber)\b", re.I)),
    ("3CH", re.compile(r"\b(3ch|three[ _-]?chamber|lvot)\b", re.I)),
    ("4CH", re.compile(r"\b(4ch|four[ _-]?chamber)\b", re.I)),
)


def classify_cine_series(summary: DicomSeriesSummary) -> SeriesCandidate:
    """Metadata-only cine-view heuristic.

    This is intentionally weaker than biv-me's learned view-selection models and
    should be treated as a triage hint, not validated view classification.
    """
    description = summary.description or ""
    reasons: list[str] = []
    predicted = "UNKNOWN"
    for name, pattern in _PATTERNS:
        if pattern.search(description):
            predicted = name
            reasons.append(f"SeriesDescription matched {name}")
            break
    if summary.temporal_positions and summary.temporal_positions > 1:
        reasons.append("multiple temporal positions")
    cine_hint = any(
        token in description.lower()
        for token in ("cine", "bffe", "ssfp", "truefisp")
    )
    if cine_hint:
        reasons.append("cine sequence keyword")
    if predicted != "UNKNOWN" and (cine_hint or summary.temporal_positions):
        confidence = "metadata_supported"
    elif predicted != "UNKNOWN":
        confidence = "description_only"
    else:
        confidence = "unknown"
    return SeriesCandidate(
        series_uid_sha256=summary.series_uid_sha256,
        predicted_view=predicted,
        confidence=confidence,
        reasons=tuple(reasons),
    )


def rank_series_for_cine(summaries: list[DicomSeriesSummary]) -> list[SeriesCandidate]:
    candidates = [classify_cine_series(item) for item in summaries]
    rank = {"metadata_supported": 0, "description_only": 1, "unknown": 2}
    return sorted(
        candidates,
        key=lambda item: (rank[item.confidence], item.predicted_view, item.series_uid_sha256),
    )
