from src.database import create_audit_run, initialize_database, save_findings
from src.dashboard_generator import generate_dashboard
from src.lighthouse_history import save_lighthouse_scores


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
    assert "Performance (Δ)" in content
    assert "Runs with Lighthouse scores" in content


def test_dashboard_compares_lighthouse_scores_with_previous_run(tmp_path):
    db = tmp_path / "audit.db"
    initialize_database(db)
    older = create_audit_run("https://example.com", 2, 3, {}, db_path=db)
    save_lighthouse_scores(older, {
        "available": True,
        "categories": {
            "performance": {"score": 70},
            "accessibility": {"score": 90},
            "seo": {"score": 80},
        },
    }, db_path=db)
    newer = create_audit_run("https://example.com", 4, 1, {}, db_path=db)
    save_lighthouse_scores(newer, {
        "available": True,
        "categories": {
            "performance": {"score": 85},
            "accessibility": {"score": 88},
            "seo": {"score": 80},
        },
    }, db_path=db)

    output = tmp_path / "dashboard.html"
    generate_dashboard(output, db_path=db)
    content = output.read_text(encoding="utf-8")

    assert "85.0 (Δ +15.0)" in content
    assert "88.0 (Δ -2.0)" in content
    assert "80.0 (Δ +0.0)" in content
    assert "70.0 (first)" in content
    assert "90.0 (first)" in content


def test_dashboard_empty_database_is_informative(tmp_path):
    output = tmp_path / "dashboard.html"
    generate_dashboard(output, db_path=tmp_path / "empty.db")
    assert "No audit history yet" in output.read_text(encoding="utf-8")
