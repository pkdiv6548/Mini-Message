"""Bounded HTTP checks for URLs discovered during a website crawl."""
from urllib.parse import urlparse
import requests


def check_links(urls, timeout=8, max_links=100):
    """Return findings for unreachable HTTP(S) links, checking each URL once."""
    findings = []
    checked = set()
    session = requests.Session()
    for url in urls:
        if url in checked or len(checked) >= max_links:
            continue
        checked.add(url)
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            continue
        try:
            response = session.head(url, timeout=timeout, allow_redirects=True)
            if response.status_code in (405, 501):
                response = session.get(url, timeout=timeout, allow_redirects=True, stream=True)
                response.close()
            if response.status_code >= 400:
                findings.append({
                    "url": url,
                    "type": "broken_link",
                    "severity": "high" if response.status_code >= 500 else "medium",
                    "message": f"Linked URL returned HTTP {response.status_code}",
                })
        except requests.RequestException as exc:
            findings.append({
                "url": url,
                "type": "broken_link",
                "severity": "medium",
                "message": f"Linked URL could not be reached: {exc.__class__.__name__}",
            })
    return findings
