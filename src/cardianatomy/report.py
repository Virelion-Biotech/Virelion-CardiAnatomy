from __future__ import annotations

import html
import json

from .models import AnatomyBundle


def render_html_report(bundle: AnatomyBundle) -> str:
    def esc(value: object) -> str:
        return html.escape(str(value))

    artifacts = "".join(
        "<tr>"
        f"<td>{esc(a.artifact_id)}</td><td>{esc(a.kind)}</td>"
        f"<td>{esc(a.producer or '')}</td><td><code>{esc(a.sha256 or '')}</code></td>"
        f"<td>{esc(a.uri)}</td>"
        "</tr>"
        for a in bundle.artifacts
    )
    stages = "".join(
        "<tr>"
        f"<td>{esc(s.stage)}</td><td>{esc(s.backend)}</td><td>{esc(s.status)}</td>"
        f"<td><code>{esc(s.fingerprint[:16])}</code></td>"
        "</tr>"
        for s in bundle.stages
    )
    qc_payload = bundle.qc.model_dump(mode="json") if bundle.qc else {}
    qc_json = html.escape(json.dumps(qc_payload, indent=2))
    readiness = {
        "baseline": bundle.ready,
        "surface": bundle.surface_ready,
        "electrophysiology": bundle.ep_ready,
        "mechanics": bundle.mechanics_ready,
        "flow": bundle.flow_ready,
    }
    readiness_html = "".join(
        f"<span class='pill {'ok' if value else 'no'}'>{esc(name)}: {value}</span>"
        for name, value in readiness.items()
    )
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><title>CardiAnatomy report</title>
<style>
body{{font-family:Inter,system-ui,sans-serif;max-width:1200px;margin:40px auto;
    padding:0 24px;color:#18212b}}
h1{{font-size:2rem}} h2{{margin-top:2rem}} table{{border-collapse:collapse;width:100%}}
th,td{{border-bottom:1px solid #ddd;padding:8px;text-align:left;vertical-align:top}}
code,pre{{font-family:ui-monospace,monospace}} pre{{background:#f6f8fa;padding:16px;overflow:auto}}
.pill{{display:inline-block;padding:6px 10px;margin:3px;border-radius:999px;font-size:.85rem}}
.ok{{background:#dff7e8}} .no{{background:#fce8e8}} .muted{{color:#66717d}}
</style></head><body>
<h1>Virelion CardiAnatomy</h1>
<p class='muted'>Subject {esc(bundle.subject_id)} · study {esc(bundle.study_id)} ·<br>
acquisition {esc(bundle.acquisition_id)}</p>
<div>{readiness_html}</div>
<h2>Artifacts</h2><table><thead><tr><th>ID</th><th>Kind</th><th>Producer</th>
<th>SHA-256</th><th>URI</th></tr></thead><tbody>{artifacts}</tbody></table>
<h2>Pipeline stages</h2><table><thead><tr><th>Stage</th><th>Backend</th>
<th>Status</th><th>Fingerprint</th></tr></thead><tbody>{stages}</tbody></table>
<h2>Geometry QC</h2><pre>{qc_json}</pre>
<p class='muted'>Research software. Software readiness does not establish biological or
clinical validity.</p>
</body></html>"""
