"""Homepage health + tech audit for lead lists (one GET per site).
Built and operated by ProfitMaker (an AI agent) for Avatar 8 LLC."""
from __future__ import annotations
import re, datetime

TECH = {  # name: (category, regexes over html/headers)
 "WordPress": ("cms", [r"/wp-content/", r"/wp-includes/", r'generator" content="WordPress']),
 "Wix": ("cms", [r"static\.wixstatic\.com", r"x-wix-request-id"]),
 "Squarespace": ("cms", [r"static1\.squarespace\.com", r"squarespace-cdn"]),
 "Shopify": ("ecommerce", [r"cdn\.shopify\.com", r"x-shopid"]),
 "Webflow": ("cms", [r"assets\.website-files\.com", r"data-wf-page", r"webflow\.com"]),
 "GoDaddy Website Builder": ("cms", [r"img1\.wsimg\.com", r"godaddy-?website-?builder"]),
 "Weebly": ("cms", [r"editmysite\.com", r"weebly\.com"]),
 "Duda": ("cms", [r"dudamobile\.com", r"multiscreensite\.com"]),
 "Joomla": ("cms", [r'generator" content="Joomla']),
 "Drupal": ("cms", [r"Drupal\.settings", r"/sites/default/files/", r"x-drupal-cache"]),
 "WooCommerce": ("ecommerce", [r"woocommerce"]),
 "Next.js": ("framework", [r"/_next/static/", r"x-powered-by: next\.js"]),
 "React": ("framework", [r"data-reactroot", r"react-dom"]),
 "jQuery": ("library", [r"jquery[.-][0-9]", r"jquery\.min\.js"]),
 "Bootstrap": ("library", [r"bootstrap(\.min)?\.(css|js)"]),
 "Google Analytics 4": ("analytics", [r"gtag/js\?id=G-", r"googletagmanager\.com/gtag"]),
 "Google Tag Manager": ("analytics", [r"googletagmanager\.com/gtm\.js", r"GTM-[A-Z0-9]{4,}"]),
 "Meta Pixel": ("ads", [r"connect\.facebook\.net/.+/fbevents\.js", r"fbq\('init'"]),
 "Hotjar": ("analytics", [r"static\.hotjar\.com"]),
 "Plausible": ("analytics", [r"plausible\.io/js"]),
 "HubSpot": ("marketing", [r"js\.hs-scripts\.com", r"js\.hsforms\.net"]),
 "Mailchimp": ("marketing", [r"chimpstatic\.com", r"list-manage\.com"]),
 "Intercom": ("chat", [r"widget\.intercom\.io"]),
 "Tawk.to": ("chat", [r"embed\.tawk\.to"]),
 "Calendly": ("booking", [r"calendly\.com/"]),
 "Square Appointments": ("booking", [r"squareup\.com/appointments", r"square\.site"]),
 "OpenTable": ("booking", [r"opentable\.com/widget", r"opentable\.com/restref"]),
 "Cloudflare": ("cdn", [r"server: cloudflare", r"cf-ray:"]),
 "reCAPTCHA": ("security", [r"google\.com/recaptcha"]),
 "Stripe": ("payments", [r"js\.stripe\.com"]),
}

def detect_tech(html: str, headers: dict[str, str]) -> list[dict]:
    hay = html[:1_500_000] + "\n" + "\n".join(f"{k.lower()}: {v}" for k, v in headers.items())
    out = []
    for name, (cat, pats) in TECH.items():
        if any(re.search(p, hay, re.I) for p in pats):
            out.append({"name": name, "category": cat})
    return out

def copyright_year(text: str) -> int | None:
    years = [int(y) for y in re.findall(r"(?:©|&copy;|&#169;|copyright)\s*(?:\d{4}\s*[-–]\s*)?((?:19|20)\d{2})", text, re.I)]
    yr = datetime.date.today().year
    years = [y for y in years if 1995 <= y <= yr + 1]
    return max(years) if years else None

def audit(final_url: str, status: int, html: str, headers: dict[str, str], elapsed_ms: int, http_ok_on_http: bool | None = None) -> dict:
    h = {k.lower(): v for k, v in headers.items()}
    low = html.lower()
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    desc = re.search(r'<meta[^>]+name=["\']description["\'][^>]*content=["\']([^"\']*)', html, re.I)
    tech = detect_tech(html, h)
    cy = copyright_year(html)
    yr = datetime.date.today().year
    checks = {
        "https": final_url.startswith("https://"),
        "mobileViewport": bool(re.search(r'<meta[^>]+name=["\']viewport', html, re.I)),
        "hasTitle": bool(title and title.group(1).strip()),
        "hasMetaDescription": bool(desc and desc.group(1).strip()),
        "hasAnalytics": any(t["category"] == "analytics" for t in tech),
        "hasFavicon": "rel=\"icon\"" in low or "rel='icon'" in low or "shortcut icon" in low or 'rel="apple-touch-icon"' in low,
        "hasOpenGraph": 'property="og:' in low or "property='og:" in low,
        "hasStructuredData": "application/ld+json" in low,
        "fastResponse": elapsed_ms < 2000,
    }
    if cy is not None:  # unknown year stays neutral; many modern sites omit it
        checks["copyrightNotStale"] = cy >= yr - 2
    issues = [k for k, v in checks.items() if not v]
    score = round(100 * sum(checks.values()) / len(checks))
    return {
        "finalUrl": final_url, "httpStatus": status, "responseMs": elapsed_ms,
        "title": (re.sub(r"\s+", " ", title.group(1)).strip()[:200] if title else None),
        "copyrightYear": cy, "tech": tech,
        "cms": next((t["name"] for t in tech if t["category"] in ("cms", "ecommerce")), None),
        "checks": checks, "issues": issues, "healthScore": score,
        "needsWebsiteHelp": score < 60 or not checks["https"] or not checks["mobileViewport"],
    }
