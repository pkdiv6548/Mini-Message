# Website Audit Automation

A zero-budget website auditing toolkit for SEO, broken links, page metadata, and optional Google Lighthouse scores.

## Stack
- Python 3.11+
- SQLite for audit history
- Requests + BeautifulSoup for crawling and SEO checks
- Optional Node.js 22+ and Lighthouse CLI for browser-based audits
- GitHub Actions for tests
- Cloudflare Pages can host static HTML reports/dashboard, but it cannot run the Python crawler itself. The crawler runs locally or in GitHub Actions.

## Setup
```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
python -m src.main https://example.com --max-pages 10 --check-links
```

The crawler checks page titles and meta descriptions (missing, short, and long), duplicate titles/descriptions across crawled pages, H1 heading counts, canonical links, and robots meta directives such as `noindex`. Suggested character ranges are heuristics, not guaranteed ranking rules; snippets and search-engine behavior can vary. A `noindex` directive may be intentional and should be reviewed rather than automatically removed.

The HTML audit report includes page-level title, description, canonical, robots and H1 information, findings grouped by severity and category, and Lighthouse scores when available. HTML values are escaped before being written to the report. Reports are saved under `reports/`; the machine-readable full result is saved as `reports/latest.json`.

Optional broken-link checks test up to 100 discovered URLs using HTTP HEAD requests (with GET fallback when unsupported). Use only on sites you own or are authorized to audit.

Optional Lighthouse (requires Chrome/Chromium and Lighthouse CLI):
```bash
npm install -g lighthouse
python -m src.main https://example.com --max-pages 10 --lighthouse
```

SQLite history is saved at `data/audits.db`. Generate an HTML dashboard from previous local audit runs:
```bash
python -m src.main --dashboard-only
```
The dashboard is written to `reports/dashboard.html` and includes recent runs, page and issue counts, severity breakdowns, and broken-link counts. It reads your local SQLite database; the static Cloudflare Pages overview does not automatically access local audit history.

## Safety
Only audit sites you own or have permission to test. Keep crawl limits reasonable. Do not put secrets in source control. This project makes no paid-service assumptions.
