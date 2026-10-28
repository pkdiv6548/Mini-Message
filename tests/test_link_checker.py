from unittest.mock import Mock, patch
import requests
from src.link_checker import check_links


@patch("src.link_checker.requests.Session")
def test_reports_http_error(MockSession):
    session = Mock()
    session.head.return_value = Mock(status_code=404)
    MockSession.return_value = session

    findings = check_links(["https://example.com/missing"])

    assert len(findings) == 1
    assert findings[0]["type"] == "broken_link"
    assert "404" in findings[0]["message"]


@patch("src.link_checker.requests.Session")
def test_head_not_supported_falls_back_to_get(MockSession):
    session = Mock()
    session.head.return_value = Mock(status_code=405)
    response = Mock(status_code=200)
    session.get.return_value = response
    MockSession.return_value = session

    assert check_links(["https://example.com/page"]) == []
    session.get.assert_called_once()
    response.close.assert_called_once()


@patch("src.link_checker.requests.Session")
def test_duplicate_urls_checked_once(MockSession):
    session = Mock()
    session.head.return_value = Mock(status_code=200)
    MockSession.return_value = session

    assert check_links(["https://example.com", "https://example.com"]) == []
    session.head.assert_called_once()


@patch("src.link_checker.requests.Session")
def test_request_failure_is_a_finding(MockSession):
    session = Mock()
    session.head.side_effect = requests.Timeout()
    MockSession.return_value = session

    findings = check_links(["https://example.com"])

    assert findings[0]["type"] == "broken_link"
    assert "Timeout" in findings[0]["message"]
