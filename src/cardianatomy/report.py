from __future__ import annotations

import html
import json

from .models import AnatomyBundle


def render_html_report(bundle: AnatomyBundle) -> str:
    def esc(value: object) -> str:
        return html.escape(str(value))

    def badge(label: str, value: bool) -> str:
        css = "ok" if value else "no"
        return f"<span class='pill {css}'>{esc(label)}: {esc(value)}</span>"

    artifacts = "".join(
        "<tr>"
        f"<td>{esc(item.artifact_id)}</td>"
        f"<td>{esc(item.kind)}</td>"
        f"<td>{esc(item.producer or '')}</td>"
        f"<td>{esc(item.frame_id or '')}</td>"
        f"<td>{esc(item.size_bytes or '')}</td>"
        f"<td><code>{esc((item.sha256 or '')[:16])}</code></td>"
        f"<td>{esc(item.uri)}</td>"
        "</tr>"
        for item in bundle.artifacts
    )

    stages = "".join(
        "<tr>"
        f"<td>{esc(item.stage)}</td>"
        f"<td>{esc(item.backend)}</td>"
        f"<td>{esc(item.status)}</td>"
        f"<td>{esc(round(item.duration_seconds or 0.0, 3))}</td>"
        f"<td><code>{esc(item.fingerprint[:16])}</code></td>"
        f"<td>{esc('; '.join(item.warnings))}</td>"
        "</tr>"
        for item in bundle.stages
    )

    frames = "".join(
        "<tr>"
        f"<td>{esc(item.frame_id)}</td>"
        f"<td>{esc(item.convention)}</td>"
        f"<td>{esc(item.units)}</td>"
        f"<td>{esc(item.parent_frame_id or '')}</td>"
        f"<td>{esc(item.description or '')}</td>"
        "</tr>"
        for item in bundle.frames
    )

    registrations = "".join(
        "<tr>"
        f"<td>{esc(item.registration_id)}</td>"
        f"<td>{esc(item.source_frame)}</td>"
        f"<td>{esc(item.target_frame)}</td>"
        f"<td>{esc(item.method)}</td>"
        f"<td>{esc(item.quality_metric_name or '')}</td>"
        f"<td>{esc(item.quality_metric or '')}</td>"
        "</tr>"
        for item in bundle.registrations
    )

    labels = "".join(
        "<tr>"
        f"<td>{esc(item.value)}</td>"
        f"<td>{esc(item.name)}</td>"
        f"<td>{esc(item.structure)}</td>"
        f"<td>{esc(item.ontology_id or '')}</td>"
        "</tr>"
        for item in bundle.labels
    )

    qc_payload = bundle.qc.model_dump(mode="json") if bundle.qc else {}
    qc_json = esc(json.dumps(qc_payload, indent=2, sort_keys=True))
    provenance_json = esc(
        json.dumps(bundle.provenance, indent=2, sort_keys=True)
    )

    readiness = "".join(
        (
            badge("baseline", bundle.ready),
            badge("surface", bundle.surface_ready),
            badge("electrophysiology", bundle.ep_ready),
            badge("mechanics", bundle.mechanics_ready),
            badge("flow", bundle.flow_ready),
        )
    )

    fingerprint = bundle.bundle_fingerprint or "not finalized"
    return f"""<!doctype html>
<html>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>CardiAnatomy report</title>
<style>
:root{{--bg:#f6f8fb;--card:#fff;--ink:#17202a;--muted:#697586;--line:#dce2e8}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
font-family:Inter,ui-sans-serif,system-ui,-apple-system,sans-serif}}
main{{max-width:1280px;margin:0 auto;padding:36px 24px 64px}}
.hero{{background:linear-gradient(135deg,#fff,#eef4fa);border:1px solid var(--line);
border-radius:20px;padding:28px;box-shadow:0 10px 30px rgba(20,35,50,.06)}}
h1{{margin:0 0 8px;font-size:2.2rem;letter-spacing:-.03em}}
h2{{margin:34px 0 12px;font-size:1.2rem}}
.meta{{color:var(--muted);line-height:1.6}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;
margin-top:18px}}
.pill{{display:inline-block;padding:7px 11px;margin:3px;border-radius:999px;
font-size:.82rem;font-weight:600}}
.ok{{background:#dff6e8;color:#155b36}} .no{{background:#fde8e8;color:#8d2525}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;
padding:16px;overflow:auto}}
table{{border-collapse:collapse;width:100%;min-width:760px;font-size:.9rem}}
th,td{{border-bottom:1px solid #edf0f3;padding:9px 10px;text-align:left;
vertical-align:top}}
th{{font-size:.78rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}}
code,pre{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}}
pre{{white-space:pre-wrap;background:#0d1722;color:#e7edf4;padding:16px;
border-radius:12px;overflow:auto;font-size:.82rem}}
.small{{font-size:.82rem;color:var(--muted)}} .empty{{color:var(--muted);font-style:italic}}
</style>
</head>
<body><main>
<section class='hero'>
<h1>Virelion CardiAnatomy</h1>
<div class='meta'>
Subject <strong>{esc(bundle.subject_id)}</strong> · study <strong>{esc(bundle.study_id)}</strong>
· acquisition <strong>{esc(bundle.acquisition_id)}</strong><br>
Contract {esc(bundle.contract_version)} · bundle fingerprint <code>{esc(fingerprint)}</code>
</div>
<div class='grid'><div>{readiness}</div></div>
</section>

<h2>Artifacts</h2>
<div class='card'><table>
<thead><tr><th>ID</th><th>Kind</th><th>Producer</th><th>Frame</th>
<th>Bytes</th><th>SHA-256</th><th>URI</th></tr></thead>
<tbody>{artifacts or "<tr><td colspan='7' class='empty'>No artifacts</td></tr>"}</tbody>
</table></div>

<h2>Pipeline</h2>
<div class='card'><table>
<thead><tr><th>Stage</th><th>Backend</th><th>Status</th><th>Seconds</th>
<th>Fingerprint</th><th>Warnings</th></tr></thead>
<tbody>{stages or "<tr><td colspan='6' class='empty'>No stages</td></tr>"}</tbody>
</table></div>

<h2>Coordinate frames</h2>
<div class='card'><table>
<thead><tr><th>Frame</th><th>Convention</th><th>Units</th><th>Parent</th>
<th>Description</th></tr></thead>
<tbody>{frames or "<tr><td colspan='5' class='empty'>No frames</td></tr>"}</tbody>
</table></div>

<h2>Registrations</h2>
<div class='card'><table>
<thead><tr><th>ID</th><th>Source</th><th>Target</th><th>Method</th>
<th>Metric</th><th>Value</th></tr></thead>
<tbody>{registrations or "<tr><td colspan='6' class='empty'>No registrations</td></tr>"}</tbody>
</table></div>

<h2>Anatomical labels</h2>
<div class='card'><table>
<thead><tr><th>Value</th><th>Name</th><th>Structure</th><th>Ontology</th></tr></thead>
<tbody>{labels or "<tr><td colspan='4' class='empty'>No labels</td></tr>"}</tbody>
</table></div>

<h2>Geometry QC</h2>
<div class='card'><pre>{qc_json}</pre></div>

<h2>Provenance</h2>
<div class='card'><pre>{provenance_json}</pre></div>

<p class='small'>Research software. Software readiness, numerical QC, and successful pipeline
execution do not establish anatomical, biological, clinical, or regulatory validity.</p>
</main></body></html>"""
