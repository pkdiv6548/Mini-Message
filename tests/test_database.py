import pytest
from src.database import initialize_database, create_audit_run, save_findings, list_runs


def test_database_run_and_findings(tmp_path):
    db = tmp_path / "audit.db"
    initialize_database(db)
    run_id = create_audit_run("https://example.com", 2, 1, {"findings": 1}, db)
    save_findings(run_id, [{"url": "https://example.com", "type": "missing_title",
                            "severity": "medium", "message": "Missing title"}], db)
    runs = list_runs(db_path=db)
    assert len(runs) == 1
    assert runs[0]["website_url"] == "https://example.com"
    from src.database import get_connection
    with get_connection(db) as connection:
        row = connection.execute("SELECT * FROM audit_findings WHERE audit_run_id=?", (run_id,)).fetchone()
    assert row["finding_type"] == "missing_title"


def test_lighthouse_scores_validate(tmp_path):
    from src.lighthouse_history import save_lighthouse_scores
    db = tmp_path / "audit.db"
    initialize_database(db)
    run_id = create_audit_run("https://example.com", 1, 0, {}, db)
    with pytest.raises(ValueError):
        save_lighthouse_scores(run_id, {"available": True, "categories": {"seo": {"score": 150}}}, db)
