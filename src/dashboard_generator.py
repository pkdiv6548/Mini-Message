"""Generate a self-contained dashboard from local SQLite audit history."""
import html
import json
from pathlib import Path

from src.database import get_connection, list_runs


def _e(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def _summary(run):
    try:
        return json.loads(run.get("summary_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def _delta(current, previous, key):
    now = int(current.get(key) or 0)
    before = int(previous.get(key) or 0)
    change = now - before
    if change < 0:
        return f"{change} (improved)" if key == "issue_count" or key == "broken_links" else str(change)
    if change > 0:
        return f"+{change}" + (" (more issues)" if key in ("issue_count", "broken_links") else "")
    return "0 (no change)"


def generate_dashboard(output_path="reports/dashboard.html", db_path=None, limit=50):
    """Write a history dashboard with same-site comparisons and Lighthouse scores."""
    runs = list_runs(limit=limit, db_path=db_path)
    finding_counts = {}
    lighthouse_scores = {}
    with get_connection(db_path) as connection:
        for row in connection.execute("""
            SELECT audit_run_id, severity, COUNT(*) AS total
            FROM audit_findings GROUP BY audit_run_id, severity
        """).fetchall():
            finding_counts.setdefault(row["audit_run_id"], {})[row["severity"]] = row["total"]
        for row in connection.execute("""
            SELECT audit_run_id, category, score
            FROM lighthouse_results ORDER BY audit_run_id DESC, category
        """).fetchall():
            lighthouse_scores.setdefault(row["audit_run_id"], {})[row["category"]] = row["score"]

    previous_by_site = {}
    rows = []
    for run in runs:
        run_id = run["id"]
        site = run.get("website_url", "")
        summary = _summary(run)
        counts = finding_counts.get(run_id, {})
        severity = " · ".join(
            f"{name.title()}: {counts.get(name, 0)}"
            for name in ("high", "medium", "low")
        )
        previous = previous_by_site.get(site)
        if previous:
            previous_summary = _summary(previous)
            comparison = (
                f"Issues: {_delta(run, previous, 'issue_count')}; "
                f"broken links: {_delta(summary, previous_summary, 'broken_links')}"
            )
            old_scores = lighthouse_scores.get(previous["id"], {})
            new_scores = lighthouse_scores.get(run_id, {})
            score_changes = []
            for category in sorted(set(old_scores) & set(new_scores)):
                delta = round(float(new_scores[category]) - float(old_scores[category]), 1)
                score_changes.append(f"{category}: {delta:+.1f} pts")
            if score_changes:
                comparison += "; Lighthouse " + ", ".join(score_changes)
        else:
            comparison = "No earlier run for this website in the displayed history"
        scores = lighthouse_scores.get(run_id, {})
        score_text = " · ".join(
            f"{name}: {round(float(score), 1)}"
            for name, score in sorted(scores.items())
        ) or "Not recorded"
        rows.append(
            "<tr><td>" + _e(run_id) + "</td><td>" +
            _e(run.get("started_at", "")) + "</td><td>" +
            _e(site) + "</td><td>" + _e(run.get("page_count", 0)) +
            "</td><td>" + _e(run.get("issue_count", 0)) + "</td><td>" +
            _e(severity) + "</td><td>" + _e(summary.get("broken_links", 0)) +
            "</td><td>" + _e(score_text) + "</td><td>" + _e(comparison) + "</td></tr>"
        )
        previous_by_site[site] = run

    body = "".join(rows) or "<tr><td colspan='9'>No audit history yet. Run an audit to populate this dashboard.</td></tr>"
    totals = {
        "runs": len(runs),
        "pages": sum(int(run.get("page_count") or 0) for run in runs),
        "issues": sum(int(run.get("issue_count") or 0) for run in runs),
    }
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Website Audit Dashboard</title>
<style>
body{{font:16px/1.55 system-ui,sans-serif;max-width:1500px;margin:2rem auto;padding:0 1rem}}
.cards{{display:flex;gap:1rem;flex-wrap:wrap}}.card{{border:1px solid #8886;border-radius:12px;padding:1rem;min-width:150px}}
.table-wrap{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;margin-top:1rem}}th,td{{padding:.7rem;border:1px solid #8886;text-align:left;overflow-wrap:anywhere;vertical-align:top}}th{{background:#8882}}
</style></head><body><h1>Website Audit Dashboard</h1>
<p>Recent audit runs from the local SQLite database (up to {len(runs)} shown). Each run is compared with the next older run for the same exact website URL when available.</p>
<div class="cards"><div class="card"><strong>Recent audit runs</strong><br>{totals["runs"]}</div>
<div class="card"><strong>Pages scanned across runs</strong><br>{totals["pages"]}</div>
<div class="card"><strong>Issues across runs</strong><br>{totals["issues"]}</div></div>
<div class="table-wrap"><table><thead><tr><th>Run</th><th>Started</th><th>Website</th><th>Pages</th><th>Issues</th><th>Severity breakdown</th><th>Broken links</th><th>Lighthouse scores / 100</th><th>Change vs previous run</th></tr></thead>
<tbody>{body}</tbody></table></div>
<p>Negative issue or broken-link changes indicate fewer reported problems. Lighthouse changes are score-point differences. Refresh this dashboard after running new audits to view updated history.</p>
</body></html>"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")
    return str(path)
