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
    """Return score and previous-run comparison indexed by audit run/category."""
    rows = connection.execute("""
        SELECT lr.audit_run_id, ar.website_url, lr.category, lr.score
        FROM lighthouse_results lr
        JOIN audit_runs ar ON ar.id = lr.audit_run_id
        ORDER BY ar.id DESC
    """).fetchall()

    scores = {}
    by_website_category = {}
    for row in rows:
        run_id = row["audit_run_id"]
        category = row["category"]
        score = row["score"]
        if category not in {key for key, _ in LIGHTHOUSE_CATEGORIES} or score is None:
            continue
        scores[(run_id, category)] = float(score)
        by_website_category.setdefault((row["website_url"], category), []).append(
            (run_id, float(score))
        )

    deltas = {}
    for entries in by_website_category.values():
        for index, (run_id, score) in enumerate(entries):
            if index + 1 < len(entries):
                previous_score = entries[index + 1][1]
                deltas[(run_id, entries[index][0] if False else "")] = 0
                # The category is part of the grouping key; the run ID is unique.
                deltas[(run_id, next(
                    category for (website, category), values in by_website_category.items()
                    if values is entries
                ))] = score - previous_score
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
        "lighthouse_runs": len({
            run_id for (run_id, _category), _score in lighthouse_scores.items()
            if any(run["id"] == run_id for run in runs)
        }),
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
<p>Refresh this dashboard after running new audits to view updated history. Lighthouse history is saved only when a run uses <code>--lighthouse</code> and Lighthouse is available locally.</p></body></html>"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")
    return str(path)
