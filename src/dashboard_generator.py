"""Generate a self-contained dashboard from local SQLite audit history."""
import html
import json
from pathlib import Path

from src.database import get_connection, list_runs


def generate_dashboard(output_path="reports/dashboard.html", db_path=None, limit=50):
    """Write an HTML dashboard showing recent audits and issue severity counts."""
    runs = list_runs(limit=limit, db_path=db_path)
    finding_counts = {}
    with get_connection(db_path) as connection:
        for row in connection.execute("""
            SELECT audit_run_id, severity, COUNT(*) AS total
            FROM audit_findings GROUP BY audit_run_id, severity
        """).fetchall():
            finding_counts.setdefault(row["audit_run_id"], {})[row["severity"]] = row["total"]

    rows = []
    for run in runs:
        summary = {}
        try:
            summary = json.loads(run.get("summary_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            pass
        counts = finding_counts.get(run["id"], {})
        severity = " · ".join(
            f"{name.title()}: {counts.get(name, 0)}"
            for name in ("high", "medium", "low")
        )
        rows.append(
            "<tr><td>" + html.escape(str(run["id"])) + "</td><td>" +
            html.escape(str(run["started_at"])) + "</td><td>" +
            html.escape(str(run["website_url"])) + "</td><td>" +
            html.escape(str(run["page_count"])) + "</td><td>" +
            html.escape(str(run["issue_count"])) + "</td><td>" +
            html.escape(severity) + "</td><td>" +
            html.escape(str(summary.get("broken_links", 0))) + "</td></tr>"
        )
    body = "".join(rows) or "<tr><td colspan='7'>No audit history yet. Run an audit to populate this dashboard.</td></tr>"
    totals = {
        "runs": len(runs),
        "pages": sum(int(run.get("page_count") or 0) for run in runs),
        "issues": sum(int(run.get("issue_count") or 0) for run in runs),
    }
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Website Audit Dashboard</title>
<style>
:root{{color-scheme:light dark}}body{{font:16px/1.55 system-ui,sans-serif;max-width:1200px;margin:2rem auto;padding:0 1rem}}
.cards{{display:flex;gap:1rem;flex-wrap:wrap}}.card{{border:1px solid #8886;border-radius:12px;padding:1rem;min-width:150px}}
table{{border-collapse:collapse;width:100%;margin-top:1rem}}th,td{{padding:.7rem;border:1px solid #8886;text-align:left;overflow-wrap:anywhere}}th{{background:#8882}}
</style></head><body><h1>Website Audit Dashboard</h1>
<p>Recent audit runs from the local SQLite database (up to {len(runs)} shown).</p>
<div class="cards"><div class="card"><strong>Audit runs</strong><br>{totals["runs"]}</div>
<div class="card"><strong>Pages scanned</strong><br>{totals["pages"]}</div>
<div class="card"><strong>Issues found</strong><br>{totals["issues"]}</div></div>
<table><thead><tr><th>Run</th><th>Started</th><th>Website</th><th>Pages</th><th>Issues</th><th>Severity breakdown</th><th>Broken links</th></tr></thead>
<tbody>{body}</tbody></table>
<p>Refresh this dashboard after running new audits to view updated history.</p></body></html>"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")
    return str(path)
