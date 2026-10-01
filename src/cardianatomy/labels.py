from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CanonicalStructure:
    key: str
    display_name: str
    aliases: tuple[str, ...]
    family: str


_STRUCTURES: tuple[CanonicalStructure, ...] = (
    CanonicalStructure(
        "lv_cavity",
        "Left ventricular cavity",
        ("lv", "left_ventricle"),
        "ventricle",
    ),
    CanonicalStructure(
        "rv_cavity",
        "Right ventricular cavity",
        ("rv", "right_ventricle"),
        "ventricle",
    ),
    CanonicalStructure(
        "lv_myocardium",
        "Left ventricular myocardium",
        ("myocardium", "lv_myo"),
        "ventricle",
    ),
    CanonicalStructure(
        "la_cavity",
        "Left atrial cavity",
        ("la", "left_atrium"),
        "atrium",
    ),
    CanonicalStructure(
        "ra_cavity",
        "Right atrial cavity",
        ("ra", "right_atrium"),
        "atrium",
    ),
    CanonicalStructure(
        "aorta",
        "Aorta",
        ("ao", "ascending_aorta"),
        "vessel",
    ),
    CanonicalStructure(
        "pulmonary_artery",
        "Pulmonary artery",
        ("pa", "pulmonary_trunk"),
        "vessel",
    ),
    CanonicalStructure("mitral_valve", "Mitral valve", ("mv",), "valve"),
    CanonicalStructure("tricuspid_valve", "Tricuspid valve", ("tv",), "valve"),
    CanonicalStructure("aortic_valve", "Aortic valve", ("av",), "valve"),
    CanonicalStructure("pulmonary_valve", "Pulmonary valve", ("pv",), "valve"),
    CanonicalStructure(
        "scar_core",
        "Scar core",
        ("dense_scar", "core"),
        "tissue",
    ),
    CanonicalStructure(
        "scar_border_zone",
        "Scar border zone",
        ("gray_zone", "border_zone"),
        "tissue",
    ),
)


def canonical_structures() -> tuple[CanonicalStructure, ...]:
    return _STRUCTURES


def normalize_structure_name(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    for item in _STRUCTURES:
        if normalized == item.key or normalized in item.aliases:
            return item.key
    return normalized


def validate_label_mapping(mapping: dict[int, str]) -> dict[int, str]:
    normalized = {
        int(value): normalize_structure_name(name)
        for value, name in mapping.items()
    }
    if any(value < 0 for value in normalized):
        raise ValueError("Label values must be non-negative")
    return normalized
