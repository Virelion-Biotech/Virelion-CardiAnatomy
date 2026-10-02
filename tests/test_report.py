from cardianatomy import AnatomyBundle
from cardianatomy.report import render_html_report


def test_report_is_self_contained_html() -> None:
    bundle = AnatomyBundle(subject_id="S1", study_id="ST", acquisition_id="A1")
    html = render_html_report(bundle)
    assert "Virelion CardiAnatomy" in html
    assert "S1" in html


def test_report_escapes_untrusted_text_and_json() -> None:
    bundle = AnatomyBundle(
        subject_id="<script>alert(1)</script>",
        study_id="ST",
        acquisition_id="A1",
        provenance={
            "payload": "</pre><script>window.pwned=true</script><pre>"
        },
    )
    rendered = render_html_report(bundle)
    assert "<script>alert(1)</script>" not in rendered
    assert "<script>window.pwned=true</script>" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert "&lt;/pre&gt;&lt;script&gt;" in rendered
