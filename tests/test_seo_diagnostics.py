from unittest.mock import Mock, patch
from src.crawler import _duplicate_findings, _metadata_findings, crawl_website


def page(**kwargs):
    base = {"url": "https://example.com/", "title": "A useful page title for visitors",
            "description": "A useful description that tells visitors what this page is about and what they can expect to find here.",
            "h1_count": 1, "canonical": "https://example.com/", "canonical_count": 1,
            "canonical_valid": True, "robots": ""}
    base.update(kwargs)
    return base


def test_title_and_description_length_findings():
    kinds = {f["type"] for f in _metadata_findings(page(title="Tiny", description="Brief"))}
    assert {"short_title", "short_description"} <= kinds


def test_long_title_and_description_findings():
    kinds = {f["type"] for f in _metadata_findings(page(title="T" * 70, description="D" * 180))}
    assert {"long_title", "long_description"} <= kinds


def test_missing_canonical_h1_and_noindex():
    kinds = {f["type"] for f in _metadata_findings(page(canonical=None, canonical_count=0, h1_count=0, robots="index, noindex"))}
    assert {"missing_canonical", "missing_h1", "noindex_directive"} <= kinds


def test_multiple_canonical_and_multiple_h1():
    kinds = {f["type"] for f in _metadata_findings(page(canonical="https://example.com/", canonical_count=2, h1_count=2))}
    assert {"multiple_canonical", "multiple_h1"} <= kinds


def test_duplicate_titles_and_descriptions_report_each_url():
    findings = _duplicate_findings([page(url="https://example.com/a"),
        page(url="https://example.com/b", title="A USEFUL PAGE TITLE FOR VISITORS")])
    assert len([f for f in findings if f["type"] == "duplicate_title"]) == 2
    assert len([f for f in findings if f["type"] == "duplicate_description"]) == 2


@patch("src.crawler.requests.Session")
def test_crawler_extracts_canonical_robots_and_reports_seo(MockSession):
    session = Mock()
    session.headers = {}
    response = Mock(status_code=200, url="https://example.com/")
    response.headers = {"content-type": "text/html; charset=utf-8"}
    response.text = """<html><head><title>Useful page title with enough detail</title>
    <meta name="description" content="This description is long enough to explain the page clearly to readers and search engines alike.">
    <meta name="robots" content="noindex, follow"><link rel="canonical" href="/preferred">
    </head><body><h1>Heading</h1></body></html>"""
    session.get.return_value = response
    MockSession.return_value = session
    result = crawl_website("https://example.com/", max_pages=1)
    parsed = result["pages"][0]
    assert parsed["canonical"] == "https://example.com/preferred"
    assert parsed["canonical_valid"] is True
    assert parsed["robots"] == "noindex, follow"
    assert any(f["type"] == "noindex_directive" for f in result["findings"])
