from src.database import create_audit_run, initialize_database, save_findings
from src.dashboard_generator import generate_dashboard


def test_dashboard_contains_run_and_severity(tmp_path):
    db = tmp_path / "audit.db"
    initialize_database(db)
    run_id = create_audit_run(
        "https://example.com", 3, 2, {"broken_links": 1}, db_path=db
    )
    save_findings(run_id, [
        {"url": "https://example.com/a", "type": "http_error",
         "severity": "high", "message": "HTTP 500"},
        {"url": "https://example.com/b", "type": "broken_link",
         "severity": "medium", "message": "HTTP 404"},
    ], db_path=db)

    output = tmp_path / "dashboard.html"
    result = generate_dashboard(output, db_path=db)

    content = output.read_text(encoding="utf-8")
    assert result == str(output)
    assert "https://example.com" in content
    assert "Severity breakdown" in content
    assert "Broken links" in content
    assert "High: 1" in content
    assert "Medium: 1" in content


def test_dashboard_empty_database_is_informative(tmp_path):
    output = tmp_path / "dashboard.html"
    generate_dashboard(output, db_path=tmp_path / "empty.db")
    assert "No audit history yet" in output.read_text(encoding="utf-8")
