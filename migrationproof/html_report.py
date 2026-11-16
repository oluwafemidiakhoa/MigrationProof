"""Escaped offline HTML report."""
from datetime import datetime, timezone
from html import escape

def render_html(report):
    safe = lambda v: escape(str(v))
    findings = report.get("findings", [])
    rows = "".join("<tr><td>"+safe(f["code"])+"</td><td>"+safe(f["table"])+"</td><td>"+safe(f["detail"])+"</td></tr>" for f in findings)
    if not rows:
        rows = '<tr><td colspan="3">No differences in implemented checks</td></tr>'
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>MigrationProof</title>'
        '<style>body{font:16px system-ui;max-width:960px;margin:40px auto;padding:20px}'
        'table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:12px;text-align:left}</style>'
        '</head><body><h1>MigrationProof — Development Evidence Report</h1>'
        f'<p>Generated UTC: {safe(datetime.now(timezone.utc).isoformat())}</p>'
        f'<p>Status: <strong>{safe(report.get("status",""))}</strong></p>'
        f'<p>Source: {safe(report.get("source_database",""))} | Target: {safe(report.get("target_database",""))}</p>'
        f'<p>Source digest: <code>{safe(report.get("source_sha256",""))}</code></p>'
        f'<p>Target digest: <code>{safe(report.get("target_sha256",""))}</code></p>'
        '<h2>Findings</h2><table><tr><th>Code</th><th>Table</th><th>Detail</th></tr>'
        +rows+'</table><h2>Scope and limitations</h2><p>'+safe(report.get("scope",""))+'</p>'
        '<p>This is not a signed certificate or proof of complete database equivalence.</p></body></html>')
