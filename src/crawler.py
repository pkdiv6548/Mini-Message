"""Bounded website crawler and basic SEO checks."""
from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag
import requests
from bs4 import BeautifulSoup

USER_AGENT = "WebsiteAuditAutomation/1.0 (+local audit)"


def crawl_website(start_url, max_pages=20, timeout=10):
    parsed_start = urlparse(start_url)
    if parsed_start.scheme not in ("http", "https") or not parsed_start.hostname:
        raise ValueError("A valid http(s) URL is required.")
    origin = (parsed_start.scheme, parsed_start.netloc)
    queue = deque([start_url])
    visited = set()
    pages = []
    findings = []
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    while queue and len(visited) < max_pages:
        url = urldefrag(queue.popleft())[0]
        if url in visited:
            continue
        visited.add(url)
        try:
            response = session.get(url, timeout=timeout, allow_redirects=True)
            content_type = response.headers.get("content-type", "")
            page = {"url": url, "final_url": response.url, "status": response.status_code,
                    "content_type": content_type, "title": None, "description": None,
                    "h1_count": 0, "links": []}
            if response.status_code >= 400:
                findings.append({"url": url, "type": "http_error", "severity": "high",
                                 "message": f"HTTP {response.status_code}"})
            if "text/html" in content_type.lower():
                soup = BeautifulSoup(response.text, "html.parser")
                page["title"] = soup.title.get_text(" ", strip=True) if soup.title else None
                meta = soup.find("meta", attrs={"name": lambda value: value and value.lower() == "description"})
                page["description"] = meta.get("content", "").strip() if meta else None
                page["h1_count"] = len(soup.find_all("h1"))
                if not page["title"]:
                    findings.append({"url": url, "type": "missing_title", "severity": "medium", "message": "Missing page title"})
                if not page["description"]:
                    findings.append({"url": url, "type": "missing_description", "severity": "low", "message": "Missing meta description"})
                if page["h1_count"] == 0:
                    findings.append({"url": url, "type": "missing_h1", "severity": "low", "message": "Missing H1 heading"})
                for anchor in soup.find_all("a", href=True):
                    target = urldefrag(urljoin(response.url, anchor["href"]))[0]
                    if urlparse(target).scheme in ("http", "https"):
                        page["links"].append(target)
                        target_parsed = urlparse(target)
                        if (target_parsed.scheme, target_parsed.netloc) == origin and target not in visited and len(visited) + len(queue) < max_pages:
                            queue.append(target)
            pages.append(page)
        except requests.RequestException as exc:
            findings.append({"url": url, "type": "request_error", "severity": "high", "message": str(exc)})
            pages.append({"url": url, "final_url": None, "status": None, "content_type": None,
                          "title": None, "description": None, "h1_count": 0, "links": []})
    return {"start_url": start_url, "pages": pages, "findings": findings}
