import pytest
from src.crawler import crawl_website


def test_invalid_url_rejected():
    with pytest.raises(ValueError):
        crawl_website("file:///etc/passwd")


def test_invalid_scheme_rejected():
    with pytest.raises(ValueError):
        crawl_website("ftp://example.com")
