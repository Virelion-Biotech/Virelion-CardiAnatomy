from cardianatomy import AnatomyBundle
from cardianatomy.report import render_html_report


def test_report_is_self_contained_html() -> None:
    bundle = AnatomyBundle(subject_id="S1", study_id="ST", acquisition_id="A1")
    html = render_html_report(bundle)
    assert "Virelion CardiAnatomy" in html
    assert "S1" in html
