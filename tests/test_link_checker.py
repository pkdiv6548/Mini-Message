from unittest.mock import Mock, patch

import requests

from src.link_checker import check_links


@patch("src.link_checker.requests.Session")
def test_reports_http_error_with_source_and_scope(MockSession):
    session = Mock()
    response = Mock(status_code=404)
    response.url = "https://example.com/missing"
    response.history = []
    session.head.return_value = response
    MockSession.return_value = session

    findings = check_links(
        [{"source_url": "https://example.com/", "target_url": "https://example.com/missing"}],
        base_url="https://example.com",
    )

    assert len(findings) == 1
    assert findings[0]["type"] == "broken_link"
    assert findings[0]["status_code"] == 404
    assert findings[0]["link_scope"] == "internal"
    assert findings[0]["final_scope"] == "internal"
    assert findings[0]["source_url"] == "https://example.com/"
    assert "404" in findings[0]["message"]
    assert "final destination" in findings[0]["message"]


@patch("src.link_checker.requests.Session")
def test_head_not_supported_falls_back_to_get(MockSession):
    session = Mock()
    session.head.return_value = Mock(status_code=405)
    response = Mock(status_code=200)
    response.url = "https://example.com/page"
    response.history = []
    session.get.return_value = response
    MockSession.return_value = session

    assert check_links(["https://example.com/page"]) == []
    session.get.assert_called_once()
    response.close.assert_called_once()


@patch("src.link_checker.requests.Session")
def test_duplicate_targets_checked_once_and_sources_are_preserved(MockSession):
    session = Mock()
    response = Mock(status_code=200)
    response.url = "https://example.com/page"
    response.history = []
    session.head.return_value = response
    MockSession.return_value = session

    findings = check_links([
        {"source_url": "https://example.com/a", "target_url": "https://example.com/page"},
        {"source_url": "https://example.com/b", "target_url": "https://example.com/page"},
    ], base_url="https://example.com")

    assert findings == []
    session.head.assert_called_once_with(
        "https://example.com/page", timeout=8, allow_redirects=True
    )


@patch("src.link_checker.requests.Session")
def test_successful_redirect_is_reported_with_final_destination_and_scope(MockSession):
    session = Mock()
    response = Mock(status_code=200)
    response.url = "https://cdn.example.net/new"
    response.history = [Mock(status_code=301)]
    session.head.return_value = response
    MockSession.return_value = session

    findings = check_links([
        {"source_url": "https://example.com/page", "target_url": "https://example.com/old"}
    ], base_url="https://example.com")

    assert len(findings) == 1
    assert findings[0]["type"] == "redirected_link"
    assert findings[0]["severity"] == "low"
    assert findings[0]["final_url"] == "https://cdn.example.net/new"
    assert findings[0]["redirect_count"] == 1
    assert findings[0]["link_scope"] == "internal"
    assert findings[0]["final_scope"] == "external"


@patch("src.link_checker.requests.Session")
def test_request_failure_is_a_finding(MockSession):
    session = Mock()
    session.head.side_effect = requests.Timeout()
    MockSession.return_value = session

    findings = check_links([
        {"source_url": "https://example.com/", "target_url": "https://example.com/slow"}
    ], base_url="https://example.com")

    assert findings[0]["type"] == "broken_link"
    assert "Timeout" in findings[0]["message"]
    assert findings[0]["final_url"] is None


@patch("src.link_checker.requests.Session")
def test_max_links_bounds_requests_and_ignores_non_http_links(MockSession):
    session = Mock()
    response = Mock(status_code=200)
    response.url = "https://external.example/path"
    response.history = []
    session.head.return_value = response
    MockSession.return_value = session

    findings = check_links([
        "https://external.example/path",
        "https://second.example/path",
        "mailto:hello@example.com",
        "not-a-url",
    ], base_url="https://example.com", max_links=1)

    assert findings == []
    session.head.assert_called_once()
    assert session.head.call_args.args[0] == "https://external.example/path"


@patch("src.link_checker.requests.Session")
def test_get_fallback_reports_server_error(MockSession):
    session = Mock()
    session.head.return_value = Mock(status_code=501)
    response = Mock(status_code=503)
    response.url = "https://example.com/outage"
    response.history = []
    session.get.return_value = response
    MockSession.return_value = session

    findings = check_links(["https://example.com/outage"], base_url="https://example.com")

    assert findings[0]["type"] == "broken_link"
    assert findings[0]["severity"] == "high"
    assert findings[0]["status_code"] == 503
