"""Generate a self-contained HTML audit report."""
import html
import json
from pathlib import Path


def write_report(result, output_dir="reports"):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"audit-{result.get('audit_run_id', 'latest')}.html"
    pages = result.get("pages", [])
    findings = result.get("findings", [])
    page_rows = "".join(
        "<tr><td>" + html.escape(str(p.get("status") or "ERR")) + "</td><td>" +
        html.escape(str(p.get("url", ""))) + "</td><td>" +
        html.escape(str(p.get("title") or "Missing")) + "</td><td>" +
        html.escape(str(p.get("description") or "Missing")) + "</td></tr>"
        for p in pages
    )
    finding_rows = "".join(
        "<tr><td>" + html.escape(str(f.get("severity", ""))) + "</td><td>" +
        html.escape(str(f.get("type", ""))) + "</td><td>" +
        html.escape(str(f.get("url", ""))) + "</td><td>" +
        html.escape(str(f.get("message", ""))) + "</td></tr>"
        for f in findings
    ) or "<tr><td colspan='4'>No findings.</td></tr>"
    summary = result.get("summary") or {}
    link_summary = (
        f"<p>Links checked: {html.escape(str(summary.get('links_checked', 0)))} · "
        f"Broken links: {html.escape(str(summary.get('broken_links', 0)))} · "
        f"Redirected links: {html.escape(str(summary.get('redirected_links', 0)))}</p>"
    )
    lighthouse = result.get("lighthouse")
    lighthouse_html = "<p>Lighthouse was not requested.</p>"
    if lighthouse:
        if lighthouse.get("available"):
            scores = lighthouse.get("categories", {})
            lighthouse_html = "<ul>" + "".join(
                f"<li>{html.escape(k)}: {html.escape(str(v.get('score')))} / 100</li>"
                for k, v in scores.items()
            ) + "</ul>"
        else:
            lighthouse_html = "<p>" + html.escape(str(lighthouse.get("error", "Unavailable"))) + "</p>"
    document = f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Website Audit Report</title><style>body{{font:16px system-ui;max-width:1200px;margin:2rem auto;padding:0 1rem;color:#182230}}table{{border-collapse:collapse;width:100%;margin:1rem 0}}th,td{{border:1px solid #ddd;padding:.6rem;text-align:left;overflow-wrap:anywhere}}th{{background:#f2f4f7}}.muted{{color:#667085}}</style>
<h1>Website Audit Report</h1><p>Target: {html.escape(str(result.get('start_url','')))}</p>
<p>Run ID: {html.escape(str(result.get('audit_run_id','')))} · Pages: {len(pages)} · Findings: {len(findings)}</p>
<h2>Link audit summary</h2>{link_summary}
<h2>Pages</h2><table><thead><tr><th>Status</th><th>URL</th><th>Title</th><th>Description</th></tr></thead><tbody>{page_rows}</tbody></table>
<h2>Findings</h2><table><thead><tr><th>Severity</th><th>Type</th><th>URL / target</th><th>Details (including source page and final destination)</th></tr></thead><tbody>{finding_rows}</tbody></table>
<h2>Lighthouse</h2>{lighthouse_html}</html>"""
    path.write_text(document, encoding="utf-8")
    (out / "latest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return str(path)
