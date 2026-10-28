"""Bounded HTTP checks for links discovered during a website crawl."""
from urllib.parse import urlparse

import requests


def _normalise_reference(item):
    """Accept a URL string or a mapping with source_url and target_url/url."""
    if isinstance(item, str):
        return None, item
    if isinstance(item, dict):
        return item.get("source_url"), item.get("target_url") or item.get("url")
    return None, None


def _scope(url, base_url):
    if not base_url:
        return "unknown"
    target_host = (urlparse(url).hostname or "").lower()
    base_host = (urlparse(base_url).hostname or "").lower()
    return "internal" if target_host and target_host == base_host else "external"


def check_links(urls, timeout=8, max_links=100, base_url=None):
    """Check unique HTTP(S) targets and report source, scope and redirects.

    urls may contain strings or dictionaries with source_url and target_url.
    Request count is bounded by max_links. Successful redirect chains are
    reported as low-severity redirected_link findings for cleanup.
    """
    if max_links < 1:
        return []
    references = {}
    for item in urls:
        source_url, target_url = _normalise_reference(item)
        if not isinstance(target_url, str):
            continue
        target_url = target_url.strip()
        parsed = urlparse(target_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            continue
        entry = references.setdefault(target_url, {"sources": []})
        if source_url and source_url not in entry["sources"]:
            entry["sources"].append(source_url)

    findings = []
    session = requests.Session()
    try:
        for target_url, reference in list(references.items())[:max_links]:
            source_urls = reference["sources"]
            scope = _scope(target_url, base_url)
            metadata = {
                "url": target_url,
                "target_url": target_url,
                "source_url": source_urls[0] if source_urls else None,
                "source_urls": source_urls,
                "link_scope": scope,
            }
            try:
                response = session.head(target_url, timeout=timeout, allow_redirects=True)
                if response.status_code in (403, 405, 501):
                    response = session.get(
                        target_url, timeout=timeout, allow_redirects=True, stream=True
                    )
                    response.close()

                final_url = getattr(response, "url", None) or target_url
                status_code = response.status_code
                redirect_count = len(getattr(response, "history", []) or [])
                metadata.update({
                    "final_url": final_url,
                    "status_code": status_code,
                    "redirect_count": redirect_count,
                })

                if status_code >= 400:
                    findings.append({
                        **metadata,
                        "type": "broken_link",
                        "severity": "high" if status_code >= 500 else "medium",
                        "message": (
                            f"Linked URL returned HTTP {status_code}; final destination: {final_url}; "
                            f"scope: {scope}; referenced by: {', '.join(source_urls) or 'unknown source'}"
                        ),
                    })
                elif redirect_count or final_url.rstrip("/") != target_url.rstrip("/"):
                    findings.append({
                        **metadata,
                        "type": "redirected_link",
                        "severity": "low",
                        "message": (
                            f"Link redirects {redirect_count} time(s) to {final_url}; scope: {scope}; "
                            f"referenced by: {', '.join(source_urls) or 'unknown source'}"
                        ),
                    })
            except requests.RequestException as exc:
                findings.append({
                    **metadata,
                    "type": "broken_link",
                    "severity": "medium",
                    "final_url": None,
                    "status_code": None,
                    "redirect_count": 0,
                    "message": (
                        f"Linked URL could not be reached: {exc.__class__.__name__}; scope: {scope}; "
                        f"referenced by: {', '.join(source_urls) or 'unknown source'}"
                    ),
                })
    finally:
        session.close()
    return findings
