import json
from pathlib import Path

from src.report_generator import write_report


def test_report_has_severity_category_and_seo_page_summary(tmp_path):
    result = {
        "start_url": "https://example.com/",
        "audit_run_id": 7,
        "pages": [{
            "url": "https://example.com/", "status": 200, "title": "Example",
            "description": "Example description", "canonical": "https://example.com/",
            "robots": "index, follow", "h1_count": 1
        }],
        "findings": [
            {"severity": "high", "type": "http_error", "url": "https://example.com/bad", "message": "HTTP 404"},
            {"severity": "low", "type": "missing_h1", "url": "https://example.com/", "message": "Missing H1 heading"},
            {"severity": "low", "type": "missing_h1", "url": "https://example.com/other", "message": "Missing H1 heading"}
        ],
        "lighthouse": None
    }
    report_path = write_report(result, output_dir=tmp_path)
    report = Path(report_path).read_text(encoding="utf-8")
    assert "Findings by severity" in report
    assert "Findings by category" in report
    assert "High severity" in report
    assert "Canonical URL" in report
    assert "Robots meta" in report
    assert "H1 count" in report
    assert "<td>2</td>" in report
    saved = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert saved["audit_run_id"] == 7


def test_report_escapes_untrusted_html_and_handles_empty_data(tmp_path):
    result = {"start_url": "https://example.com/?q=<script>", "pages": [],
              "findings": [{"severity": "low", "type": "unsafe", "url": "<img src=x>",
                            "message": "<script>alert('x')</script>"}]}
    report_path = write_report(result, output_dir=tmp_path)
    report = Path(report_path).read_text(encoding="utf-8")
    assert "&lt;script&gt;" in report
    assert "&lt;img src=x&gt;" in report
    assert "<script>alert" not in report
    assert "No pages were scanned." in report
