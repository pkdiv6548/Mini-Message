from src.database import create_audit_run, initialize_database, save_findings
from src.dashboard_generator import generate_dashboard
from src.lighthouse_history import save_lighthouse_scores


def test_dashboard_contains_run_and_severity(tmp_path):
    db = tmp_path / "audit.db"
    initialize_database(db)
    run_id = create_audit_run("https://example.com", 3, 2, {"broken_links": 1}, db_path=db)
    save_findings(run_id, [
        {"url": "https://example.com/a", "type": "http_error", "severity": "high", "message": "HTTP 500"},
        {"url": "https://example.com/b", "type": "broken_link", "severity": "medium", "message": "HTTP 404"},
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
    assert "Change vs previous run" in content
    assert "No earlier run" in content


def test_dashboard_empty_database_is_informative(tmp_path):
    output = tmp_path / "dashboard.html"
    generate_dashboard(output, db_path=tmp_path / "empty.db")
    assert "No audit history yet" in output.read_text(encoding="utf-8")


def test_dashboard_compares_same_site_runs_and_lighthouse_scores(tmp_path):
    db = tmp_path / "audit.db"
    initialize_database(db)
    older = create_audit_run("https://example.com", 4, 5, {"broken_links": 3}, db_path=db)
    save_findings(older, [{"url": "https://example.com/a", "type": "broken_link",
                           "severity": "high", "message": "Old broken link"}], db_path=db)
    save_lighthouse_scores(older, {"available": True, "categories": {
        "seo": {"score": 70}, "performance": {"score": 80}}}, db_path=db)
    newer = create_audit_run("https://example.com", 5, 2, {"broken_links": 1}, db_path=db)
    save_findings(newer, [{"url": "https://example.com/b", "type": "missing_title",
                           "severity": "low", "message": "Missing title"}], db_path=db)
    save_lighthouse_scores(newer, {"available": True, "categories": {
        "seo": {"score": 90}, "performance": {"score": 75}}}, db_path=db)

    output = tmp_path / "dashboard.html"
    generate_dashboard(output, db_path=db)
    content = output.read_text(encoding="utf-8")
    assert "Issues: -3 (improved)" in content
    assert "broken links: -2 (improved)" in content
    assert "performance: -5.0 pts" in content
    assert "seo: +20.0 pts" in content


def test_dashboard_escapes_site_values(tmp_path):
    db = tmp_path / "audit.db"
    initialize_database(db)
    create_audit_run("https://example.com/?q=<script>", 1, 0, {}, db_path=db)
    output = tmp_path / "dashboard.html"
    generate_dashboard(output, db_path=db)
    content = output.read_text(encoding="utf-8")
    assert "&lt;script&gt;" in content
    assert "<script>" not in content
