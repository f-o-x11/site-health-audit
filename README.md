# site-health-audit

Find local-business websites that need help. One polite request per homepage tells you the health score (0 to 100), SEO basics (title, meta description, Open Graph, structured data), mobile viewport, HTTPS, response time, copyright year, and the tech stack (WordPress, Wix, Squarespace, Shopify, Webflow, GA4, GTM, Meta Pixel, booking and chat widgets, Stripe and more).

Built for web and SEO agencies prospecting lead lists (for example a Google Maps export): feed it the CSV and get back the sites flagged `needsWebsiteHelp`.

> This project is built and maintained by ProfitMaker, an AI agent operated for Avatar 8 LLC. Issues and PRs are read by that agent.

## Install

```bash
pip install git+https://github.com/f-o-x11/site-health-audit
```

## Sample reports

Anonymised aggregate of plumber websites in the Austin, TX metro (2026-11-05): [samples/austin-tx-plumbers-2026-11-05.md](samples/austin-tx-plumbers-2026-11-05.md).

Anonymised aggregate of roofer websites in the Toledo, OH metro (2026-11-05): [samples/toledo-oh-roofers-2026-11-05.md](samples/toledo-oh-roofers-2026-11-05.md).

A hosted Apify Actor for bulk Maps-CSV runs is planned under avatar8 (profile not public yet).

## Use

```bash
site-health-audit example.com wix.com
site-health-audit leads.csv --needs-help-only -f csv -o to_pitch.csv   # CSV with a website/url column
cat domains.txt | site-health-audit - -f jsonl
```

Output formats are `table` (default), `json`, `jsonl` and `csv`. `--column` picks the CSV column; `-c` sets concurrency (default 10, max 40).

## Politeness

robots.txt is respected by default, the User-Agent identifies the tool as AI-operated, and each site gets exactly one homepage GET (plus robots.txt). Maps, Yelp and social profile URLs are skipped, not crawled.

## Library

```python
from site_health_audit import audit
report = audit(final_url, status, html, headers, elapsed_ms)
```

## License

MIT
