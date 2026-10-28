"""Command-line entry point for Website Audit Automation."""
import argparse
import json
from pathlib import Path
from src.crawler import crawl_website
from src.dashboard_generator import generate_dashboard
from src.database import create_audit_run, save_findings
from src.link_checker import check_links
from src.lighthouse_analyzer import analyze_with_lighthouse
from src.lighthouse_history import save_lighthouse_scores
from src.report_generator import write_report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit a website for basic SEO and HTTP issues.")
    parser.add_argument("url", nargs="?", help="Website URL to audit")
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--lighthouse", action="store_true")
    parser.add_argument("--check-links", action="store_true", help="Check up to 100 discovered HTTP(S) links")
    parser.add_argument("--dashboard-only", action="store_true")
    args = parser.parse_args(argv)
    if args.dashboard_only:
        dashboard_path = generate_dashboard()
        print(f"Dashboard: {dashboard_path}")
        return 0
    if not args.url:
        parser.error("url is required unless --dashboard-only is used")
    if not 1 <= args.max_pages <= 200:
        parser.error("--max-pages must be between 1 and 200")
    result = crawl_website(args.url, max_pages=args.max_pages, timeout=args.timeout)
    link_findings = check_links((link for page in result["pages"] for link in page.get("links", [])), timeout=args.timeout) if args.check_links else []
    result["findings"].extend(link_findings)
    lighthouse = analyze_with_lighthouse(args.url) if args.lighthouse else None
    summary = {"pages": len(result["pages"]), "findings": len(result["findings"]), "broken_links": len(link_findings),
               "lighthouse_available": bool(lighthouse and lighthouse.get("available"))}
    run_id = create_audit_run(args.url, len(result["pages"]), len(result["findings"]), summary)
    save_findings(run_id, result["findings"])
    if lighthouse and lighthouse.get("available"):
        save_lighthouse_scores(run_id, lighthouse)
    result["audit_run_id"] = run_id
    result["summary"] = summary
    result["lighthouse"] = lighthouse
    report_path = write_report(result)
    print(f"Audit run: {run_id}")
    print(f"Pages scanned: {len(result['pages'])}")
    print(f"Findings: {len(result['findings'])}")
    if args.check_links:
        print(f"Broken links: {len(link_findings)}")
    print(f"Report: {report_path}")
    if lighthouse and not lighthouse.get("available"):
        print(f"Lighthouse warning: {lighthouse.get('error')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
