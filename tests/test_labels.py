from cardianatomy import (
    canonical_structures,
    normalize_structure_name,
    validate_label_mapping,
)


def test_whole_heart_aliases_normalize() -> None:
    assert normalize_structure_name("LAA") == "left_atrial_appendage"
    assert normalize_structure_name("RSPV") == "right_superior_pulmonary_vein"
    assert normalize_structure_name("RV Myo") == "rv_myocardium"
    assert normalize_structure_name("septum") == "interventricular_septum"


def test_structure_catalog_includes_four_chambers_and_great_vessels() -> None:
    keys = {item.key for item in canonical_structures()}
    required = {
        "lv_cavity",
        "rv_cavity",
        "la_cavity",
        "ra_cavity",
        "aorta",
        "pulmonary_artery",
        "superior_vena_cava",
        "inferior_vena_cava",
    }
    assert required <= keys


def test_label_mapping_normalizes_names() -> None:
    mapping = validate_label_mapping({1: "LV", 2: "RSPV", 3: "LAA"})
    assert mapping == {
        1: "lv_cavity",
        2: "right_superior_pulmonary_vein",
        3: "left_atrial_appendage",
    }
