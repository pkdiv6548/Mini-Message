"""Optional Google Lighthouse CLI integration."""
import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

CATEGORIES = ("performance", "accessibility", "best-practices", "seo")
METRICS = ("first-contentful-paint", "largest-contentful-paint",
           "cumulative-layout-shift", "total-blocking-time", "speed-index")


def analyze_with_lighthouse(url, output_dir="reports/lighthouse", timeout=180):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return {"available": False, "error": "A valid http(s) URL is required."}
    executable = shutil.which("lighthouse")
    if not executable:
        return {"available": False, "error": "Lighthouse CLI not found. Install with npm install -g lighthouse."}
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = out / (parsed.hostname.replace(":", "_") + ".report.json")
    command = [executable, url, "--output=json", f"--output-path={report}",
               "--only-categories=" + ",".join(CATEGORIES), "--chrome-flags=--headless", "--quiet"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"available": False, "error": f"Lighthouse timed out after {timeout}s."}
    except OSError as exc:
        return {"available": False, "error": str(exc)}
    if result.returncode != 0 or not report.is_file():
        return {"available": False, "error": (result.stderr or "Lighthouse failed")[-1500:]}
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"available": False, "error": f"Invalid Lighthouse JSON: {exc}"}
    categories = {}
    for name in CATEGORIES:
        category = data.get("categories", {}).get(name)
        if category:
            score = category.get("score")
            categories[name] = {"title": category.get("title", name),
                                "score": round(score * 100, 1) if isinstance(score, (int, float)) else None}
    metrics = {}
    for name in METRICS:
        audit = data.get("audits", {}).get(name)
        if audit:
            metrics[name] = {"title": audit.get("title", name),
                             "display_value": audit.get("displayValue"),
                             "numeric_value": audit.get("numericValue"),
                             "score": audit.get("score")}
    return {"available": True, "url": url, "final_url": data.get("finalDisplayedUrl"),
            "report_json_path": str(report), "categories": categories, "metrics": metrics}
