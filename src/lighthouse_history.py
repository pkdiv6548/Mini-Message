"""Persist Lighthouse category scores."""
from src.database import get_connection

VALID_CATEGORIES = {"performance", "accessibility", "best-practices", "seo"}


def save_lighthouse_scores(audit_run_id, lighthouse_result, db_path=None):
    if not isinstance(audit_run_id, int) or isinstance(audit_run_id, bool) or audit_run_id < 1:
        raise ValueError("audit_run_id must be a positive integer.")
    if not lighthouse_result or not lighthouse_result.get("available"):
        return 0
    rows = []
    for category, details in lighthouse_result.get("categories", {}).items():
        if category not in VALID_CATEGORIES or not isinstance(details, dict):
            continue
        score = details.get("score")
        if score is None:
            continue
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 100:
            raise ValueError(f"Invalid score for {category}")
        rows.append((audit_run_id, category, float(score)))
    with get_connection(db_path) as connection:
        if connection.execute("SELECT id FROM audit_runs WHERE id=?", (audit_run_id,)).fetchone() is None:
            raise ValueError(f"Audit run {audit_run_id} does not exist")
        connection.executemany("""INSERT INTO lighthouse_results(audit_run_id,category,score)
            VALUES(?,?,?) ON CONFLICT(audit_run_id,category) DO UPDATE SET score=excluded.score,
            created_at=CURRENT_TIMESTAMP""", rows)
    return len(rows)


def get_lighthouse_history(limit=20, db_path=None):
    with get_connection(db_path) as connection:
        rows = connection.execute("""SELECT ar.id AS audit_run_id, ar.website_url, ar.started_at,
            lr.category, lr.score FROM lighthouse_results lr JOIN audit_runs ar ON ar.id=lr.audit_run_id
            ORDER BY ar.id DESC, lr.category LIMIT ?""", (limit * 4,)).fetchall()
    return [dict(row) for row in rows]
