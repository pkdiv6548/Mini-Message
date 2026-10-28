# Website Audit Automation

A zero-budget website auditing toolkit for SEO, broken links, page metadata, and optional Google Lighthouse scores.

## Stack
- Python 3.11+
- SQLite for local audit and Lighthouse score history
- Requests + BeautifulSoup for crawling and SEO checks
- Optional Node.js and Lighthouse CLI for browser-based audits
- GitHub Actions for automated tests
- Cloudflare Pages for the static project overview only; it does not run the Python crawler or automatically access a local SQLite database

## Setup
~~~bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
~~~

## Run a website audit
~~~bash
python -m src.main https://example.com --max-pages 10 --check-links --max-links 100
~~~

The crawler checks internal pages and can check up to 100 unique discovered HTTP(S) link targets by default. Use --max-links to set a different limit from 1 to 500. The link report identifies the source page, target URL, internal/external scope, final destination, redirect count, and HTTP status. Successful redirect chains are listed as low-severity recommendations so you can update links to their final destinations. HTTP HEAD checks fall back to GET for servers that reject or do not support HEAD. Network failures are recorded without exposing response bodies. Use only on sites you own or are authorized to audit.

## Lighthouse scores and history
Install Chrome/Chromium and the Lighthouse CLI if you want browser-based scores:
~~~bash
npm install -g lighthouse
python -m src.main https://example.com --max-pages 10 --lighthouse
~~~

When Lighthouse is available, the run saves Performance, Accessibility, Best Practices, and SEO scores to the local SQLite database. Repeated audits of the same website are compared in the dashboard; each score shows its change from the previous recorded score for that website/category. A score marked “first” has no earlier recorded value. Lighthouse is optional and no paid service is required.

## Dashboard and reports
Generated reports are saved under reports/; SQLite history is saved at data/audits.db.

Generate an HTML dashboard from previous local audit runs:
~~~bash
python -m src.main --dashboard-only
~~~

The dashboard is written to reports/dashboard.html. It includes recent runs, page and issue counts, severity breakdowns, broken-link counts, Lighthouse category scores, and score changes. Re-run the dashboard command after audits to refresh the report. The static Cloudflare Pages overview does not automatically access local audit history.

## Safety
Only audit sites you own or have permission to test. Keep crawl limits reasonable. Do not put secrets in source control. This project makes no paid-service assumptions.
