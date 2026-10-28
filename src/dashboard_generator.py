"""Generate a self-contained dashboard from local SQLite audit history."""
import html
import json
from pathlib import Path

from src.database import get_connection, list_runs

LIGHTHOUSE_CATEGORIES = (
    ("performance", "Performance"),
    ("accessibility", "Accessibility"),
    ("best-practices", "Best practices"),
    ("seo", "SEO"),
)


def _lighthouse_scores(connection):
    """Return scores and changes against the previous run for each site/category."""
    rows = connection.execute("""
        SELECT lr.audit_run_id, ar.website_url, lr.category, lr.score
        FROM lighthouse_results lr
        JOIN audit_runs ar ON ar.id = lr.audit_run_id
        ORDER BY ar.id DESC
    """).fetchall()

    scores = {}
    by_website_category = {}
    valid_categories = {key for key, _label in LIGHTHOUSE_CATEGORIES}
    for row in rows:
        run_id, category, score = row["audit_run_id"], row["category"], row["score"]
        if category not in valid_categories or score is None:
            continue
        score = float(score)
        scores[(run_id, category)] = score
        by_website_category.setdefault((row["website_url"], category), []).append(
            (run_id, score)
        )

    deltas = {}
    for (_website_url, category), entries in by_website_category.items():
        for index, (run_id, score) in enumerate(entries):
            if index + 1 < len(entries):
                deltas[(run_id, category)] = score - entries[index + 1][1]
    return scores, deltas


def _format_score(score, delta):
    if score is None:
        return "—"
    if delta is None:
        return f"{score:.1f} (first)"
    return f"{score:.1f} (Δ {delta:+.1f})"


def generate_dashboard(output_path="reports/dashboard.html", db_path=None, limit=50):
    """Write an HTML dashboard with audit findings and Lighthouse score trends."""
    runs = list_runs(limit=limit, db_path=db_path)
    finding_counts = {}
    with get_connection(db_path) as connection:
        for row in connection.execute("""
            SELECT audit_run_id, severity, COUNT(*) AS total
            FROM audit_findings GROUP BY audit_run_id, severity
        """).fetchall():
            finding_counts.setdefault(row["audit_run_id"], {})[row["severity"]] = row["total"]
        lighthouse_scores, lighthouse_deltas = _lighthouse_scores(connection)

    visible_run_ids = {run["id"] for run in runs}
    lighthouse_run_ids = {
        run_id for run_id, _category in lighthouse_scores if run_id in visible_run_ids
    }
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
        cells = [
            run["id"], run["started_at"], run["website_url"], run["page_count"],
            run["issue_count"], severity, summary.get("broken_links", 0),
        ]
        row_html = "".join(f"<td>{html.escape(str(value))}</td>" for value in cells)
        score_cells = []
        for category, _label in LIGHTHOUSE_CATEGORIES:
            score = lighthouse_scores.get((run["id"], category))
            delta = lighthouse_deltas.get((run["id"], category))
            score_cells.append(f"<td>{html.escape(_format_score(score, delta))}</td>")
        rows.append("<tr>" + row_html + "".join(score_cells) + "</tr>")

    body = "".join(rows) or (
        "<tr><td colspan='11'>No audit history yet. Run an audit to populate this dashboard.</td></tr>"
    )
    totals = {
        "runs": len(runs),
        "pages": sum(int(run.get("page_count") or 0) for run in runs),
        "issues": sum(int(run.get("issue_count") or 0) for run in runs),
        "lighthouse_runs": len(lighthouse_run_ids),
    }
    headings = "".join(f"<th>{html.escape(label)} (Δ)</th>" for _key, label in LIGHTHOUSE_CATEGORIES)
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Website Audit Dashboard</title>
<style>
:root{{color-scheme:light dark}}body{{font:16px/1.55 system-ui,sans-serif;max-width:1600px;margin:2rem auto;padding:0 1rem}}
.cards{{display:flex;gap:1rem;flex-wrap:wrap}}.card{{border:1px solid #8886;border-radius:12px;padding:1rem;min-width:150px}}
.table-wrap{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;margin-top:1rem}}th,td{{padding:.7rem;border:1px solid #8886;text-align:left;overflow-wrap:anywhere;white-space:nowrap}}th{{background:#8882}}
</style></head><body><h1>Website Audit Dashboard</h1>
<p>Recent audit runs from the local SQLite database (up to {len(runs)} shown).</p>
<div class="cards"><div class="card"><strong>Audit runs</strong><br>{totals["runs"]}</div>
<div class="card"><strong>Pages scanned</strong><br>{totals["pages"]}</div>
<div class="card"><strong>Issues found</strong><br>{totals["issues"]}</div>
<div class="card"><strong>Runs with Lighthouse scores</strong><br>{totals["lighthouse_runs"]}</div></div>
<p>Lighthouse columns show the score out of 100 and the change versus the previous recorded score for the same website and category. “first” means no older score exists.</p>
<div class="table-wrap"><table><thead><tr><th>Run</th><th>Started</th><th>Website</th><th>Pages</th><th>Issues</th><th>Severity breakdown</th><th>Broken links</th>{headings}</tr></thead>
<tbody>{body}</tbody></table></div>
<p>Refresh this dashboard after running new audits to view updated history. Lighthouse history is saved only when a run uses the --lighthouse option and Lighthouse is available locally.</p></body></html>"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")
    return str(path)
