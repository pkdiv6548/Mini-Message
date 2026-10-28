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
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
python -m src.main https://example.com --max-pages 10 --check-links
```

Optional broken-link checks test up to 100 discovered URLs using HTTP HEAD requests (with GET fallback when unsupported). Use only on sites you own or are authorized to audit.\n\nOptional Lighthouse (requires Chrome/Chromium and Lighthouse CLI):
```bash
npm install -g lighthouse
python -m src.main https://example.com --max-pages 10 --lighthouse
```

Generated reports are saved under `reports/`; SQLite history is saved at `data/audits.db`.\n\nGenerate an HTML dashboard from previous local audit runs:\n```bash\npython -m src.main --dashboard-only\n```\nThe dashboard is written to `reports/dashboard.html` and includes recent runs, page and issue counts, severity breakdowns, and broken-link counts. It reads your local SQLite database; the static Cloudflare Pages overview does not automatically access local audit history.

## Safety
Only audit sites you own or have permission to test. Keep crawl limits reasonable. Do not put secrets in source control. This project makes no paid-service assumptions.
