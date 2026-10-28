"""Generate a self-contained HTML audit report."""
import html
import json
from collections import Counter
from pathlib import Path


def _e(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def write_report(result, output_dir="reports"):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"audit-{result.get('audit_run_id', 'latest')}.html"
    pages = result.get("pages", [])
    findings = result.get("findings", [])
    severity_counts = Counter(str(f.get("severity", "unknown")).lower() for f in findings)
    type_counts = Counter(str(f.get("type", "unknown")) for f in findings)

    page_rows = "".join(
        "<tr><td>" + _e(p.get("status") or "ERR") + "</td><td>" +
        _e(p.get("url", "")) + "</td><td>" + _e(p.get("title") or "Missing") +
        "</td><td>" + _e(p.get("description") or "Missing") +
        "</td><td>" + _e(p.get("canonical") or "Missing") +
        "</td><td>" + _e(p.get("robots") or "—") +
        "</td><td>" + _e(p.get("h1_count", "—")) + "</td></tr>"
        for p in pages
    ) or "<tr><td colspan='7'>No pages were scanned.</td></tr>"

    finding_rows = "".join(
        "<tr><td>" + _e(f.get("severity", "")) + "</td><td>" +
        _e(f.get("type", "")) + "</td><td>" + _e(f.get("url", "")) +
        "</td><td>" + _e(f.get("message", "")) + "</td></tr>"
        for f in findings
    ) or "<tr><td colspan='4'>No findings. Great work!</td></tr>"

    severity_rows = "".join(
        "<tr><td>" + _e(level.title()) + "</td><td>" + str(count) + "</td></tr>"
        for level, count in sorted(severity_counts.items(),
                                   key=lambda item: ({"high": 0, "medium": 1, "low": 2}.get(item[0], 3), item[0]))
    ) or "<tr><td colspan='2'>No findings</td></tr>"
    category_rows = "".join(
        "<tr><td>" + _e(kind) + "</td><td>" + str(count) + "</td></tr>"
        for kind, count in sorted(type_counts.items(), key=lambda item: (-item[1], item[0]))
    ) or "<tr><td colspan='2'>No findings</td></tr>"

    lighthouse = result.get("lighthouse")
    lighthouse_html = "<p>Lighthouse was not requested.</p>"
    if lighthouse:
        if lighthouse.get("available"):
            scores = lighthouse.get("categories", {})
            lighthouse_html = "<ul>" + "".join(
                f"<li>{_e(key)}: {_e(value.get('score'))} / 100</li>"
                for key, value in scores.items()
            ) + "</ul>"
        else:
            lighthouse_html = "<p>" + _e(lighthouse.get("error", "Unavailable")) + "</p>"

    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Website Audit Report</title>
<style>
body{{font:16px system-ui,sans-serif;max-width:1400px;margin:2rem auto;padding:0 1rem;color:#182230}}
table{{border-collapse:collapse;width:100%;margin:1rem 0;table-layout:auto}}
th,td{{border:1px solid #ddd;padding:.6rem;text-align:left;overflow-wrap:anywhere;vertical-align:top}}
th{{background:#f2f4f7}}.cards{{display:flex;flex-wrap:wrap;gap:.75rem}}
.card{{border:1px solid #ddd;border-radius:.5rem;padding:.8rem 1rem;min-width:130px}}
.muted{{color:#667085}}h2{{margin-top:2rem}}
</style></head><body>
<h1>Website Audit Report</h1>
<p>Target: <strong>{_e(result.get('start_url', ''))}</strong></p>
<p class="muted">Run ID: {_e(result.get('audit_run_id', '—'))}</p>
<div class="cards">
<div class="card"><strong>Pages scanned</strong><br>{len(pages)}</div>
<div class="card"><strong>Total findings</strong><br>{len(findings)}</div>
<div class="card"><strong>High severity</strong><br>{severity_counts.get('high', 0)}</div>
<div class="card"><strong>Medium severity</strong><br>{severity_counts.get('medium', 0)}</div>
<div class="card"><strong>Low severity</strong><br>{severity_counts.get('low', 0)}</div>
</div>
<h2>Findings by severity</h2>
<table><thead><tr><th>Severity</th><th>Count</th></tr></thead><tbody>{severity_rows}</tbody></table>
<h2>Findings by category</h2>
<table><thead><tr><th>Finding type</th><th>Count</th></tr></thead><tbody>{category_rows}</tbody></table>
<h2>Scanned pages</h2>
<table><thead><tr><th>Status</th><th>URL</th><th>Title</th><th>Meta description</th><th>Canonical URL</th><th>Robots meta</th><th>H1 count</th></tr></thead><tbody>{page_rows}</tbody></table>
<h2>All findings</h2>
<table><thead><tr><th>Severity</th><th>Category</th><th>URL</th><th>Details</th></tr></thead><tbody>{finding_rows}</tbody></table>
<h2>Lighthouse</h2>{lighthouse_html}
<p class="muted">SEO thresholds are guidance, not guaranteed ranking rules. Review warnings in context before changing a site.</p>
</body></html>"""
    path.write_text(document, encoding="utf-8")
    (out / "latest.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)
