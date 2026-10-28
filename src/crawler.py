"""Bounded website crawler and practical SEO diagnostics."""
from collections import deque, defaultdict
from urllib.parse import urljoin, urlparse, urldefrag
import requests
from bs4 import BeautifulSoup

USER_AGENT = "WebsiteAuditAutomation/1.0 (+local audit)"
TITLE_MIN, TITLE_MAX = 30, 60
DESCRIPTION_MIN, DESCRIPTION_MAX = 70, 160


def _finding(url, kind, severity, message):
    return {"url": url, "type": kind, "severity": severity, "message": message}


def _metadata_findings(page):
    """Return SEO recommendations for one parsed HTML page."""
    url = page["url"]
    findings = []
    title = page.get("title") or ""
    description = page.get("description") or ""
    if not title:
        findings.append(_finding(url, "missing_title", "medium", "Missing page title"))
    else:
        if len(title) < TITLE_MIN:
            findings.append(_finding(url, "short_title", "low", f"Title is {len(title)} characters; suggested range is {TITLE_MIN}-{TITLE_MAX}."))
        elif len(title) > TITLE_MAX:
            findings.append(_finding(url, "long_title", "low", f"Title is {len(title)} characters; suggested maximum is {TITLE_MAX}."))
    if not description:
        findings.append(_finding(url, "missing_description", "low", "Missing meta description"))
    else:
        if len(description) < DESCRIPTION_MIN:
            findings.append(_finding(url, "short_description", "low", f"Meta description is {len(description)} characters; suggested range is {DESCRIPTION_MIN}-{DESCRIPTION_MAX}."))
        elif len(description) > DESCRIPTION_MAX:
            findings.append(_finding(url, "long_description", "low", f"Meta description is {len(description)} characters; suggested maximum is {DESCRIPTION_MAX}."))
    if page.get("h1_count", 0) == 0:
        findings.append(_finding(url, "missing_h1", "low", "Missing H1 heading"))
    elif page.get("h1_count", 0) > 1:
        findings.append(_finding(url, "multiple_h1", "low", f"Found {page['h1_count']} H1 headings; review heading structure."))
    if not page.get("canonical"):
        findings.append(_finding(url, "missing_canonical", "low", "No canonical link was found; confirm whether a canonical URL is needed."))
    elif page.get("canonical_count", 0) > 1:
        findings.append(_finding(url, "multiple_canonical", "medium", f"Found {page['canonical_count']} canonical links; keep one unambiguous canonical."))
    elif not page.get("canonical_valid"):
        findings.append(_finding(url, "invalid_canonical", "medium", "Canonical URL is not a valid absolute HTTP(S) URL after resolution."))
    robots = (page.get("robots") or "").lower()
    if "noindex" in {token.strip() for token in robots.replace(",", " ").split()}:
        findings.append(_finding(url, "noindex_directive", "low", "Robots meta contains noindex; verify this page is intentionally excluded from search results."))
    return findings


def _duplicate_findings(pages):
    findings = []
    for field, kind, label in (("title", "duplicate_title", "title"), ("description", "duplicate_description", "meta description")):
        grouped = defaultdict(list)
        for page in pages:
            value = (page.get(field) or "").strip().casefold()
            if value:
                grouped[value].append(page["url"])
        for urls in grouped.values():
            if len(urls) > 1:
                joined = ", ".join(urls)
                for url in urls:
                    findings.append(_finding(url, kind, "low", f"Duplicate {label} appears on {len(urls)} pages: {joined}"))
    return findings


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
                    "h1_count": 0, "canonical": None, "canonical_count": 0,
                    "canonical_valid": False, "robots": None, "links": []}
            if response.status_code >= 400:
                findings.append(_finding(url, "http_error", "high", f"HTTP {response.status_code}"))
            if "text/html" in content_type.lower():
                soup = BeautifulSoup(response.text, "html.parser")
                page["title"] = soup.title.get_text(" ", strip=True) if soup.title else None
                meta = soup.find("meta", attrs={"name": lambda value: value and value.lower() == "description"})
                page["description"] = (meta.get("content") or "").strip() if meta else None
                page["h1_count"] = len(soup.find_all("h1"))
                robots_meta = soup.find("meta", attrs={"name": lambda value: value and value.lower() == "robots"})
                page["robots"] = (robots_meta.get("content") or "").strip() if robots_meta else None
                canonicals = soup.find_all("link", attrs={"rel": lambda value: value and "canonical" in ([x.lower() for x in value] if isinstance(value, list) else value.lower().split())})
                page["canonical_count"] = len(canonicals)
                if canonicals:
                    raw_canonical = (canonicals[0].get("href") or "").strip()
                    resolved = urljoin(response.url, raw_canonical) if raw_canonical else ""
                    cp = urlparse(resolved)
                    page["canonical"] = resolved or None
                    page["canonical_valid"] = cp.scheme in ("http", "https") and bool(cp.netloc)
                findings.extend(_metadata_findings(page))
                for anchor in soup.find_all("a", href=True):
                    target = urldefrag(urljoin(response.url, anchor["href"]))[0]
                    if urlparse(target).scheme in ("http", "https"):
                        page["links"].append(target)
                        target_parsed = urlparse(target)
                        if (target_parsed.scheme, target_parsed.netloc) == origin and target not in visited and len(visited) + len(queue) < max_pages:
                            queue.append(target)
            pages.append(page)
        except requests.RequestException as exc:
            findings.append(_finding(url, "request_error", "high", str(exc)))
            pages.append({"url": url, "final_url": None, "status": None, "content_type": None,
                          "title": None, "description": None, "h1_count": 0, "canonical": None,
                          "canonical_count": 0, "canonical_valid": False, "robots": None, "links": []})
    findings.extend(_duplicate_findings(pages))
    return {"start_url": start_url, "pages": pages, "findings": findings}
