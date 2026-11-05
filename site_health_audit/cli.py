"""Command-line interface. One polite GET per homepage, robots.txt respected by default."""
from __future__ import annotations
import argparse, asyncio, csv, json, sys, time, urllib.robotparser
from urllib.parse import urlparse
import httpx
from . import __version__
from .audit import audit

UA = f"site-health-audit/{__version__} (AI-operated open-source auditor; +https://github.com/f-o-x11/site-health-audit)"
MAX_PAGE_BYTES = 3 * 1024 * 1024
SKIP_HOSTS = ("google.", "yelp.", "facebook.", "instagram.", "maps.app.goo.gl")


def normalize(u: str) -> str | None:
    u = (u or "").strip()
    if not u or u.startswith("#"):
        return None
    if "://" not in u:
        u = "https://" + u
    p = urlparse(u)
    if not p.netloc or any(h in p.netloc for h in SKIP_HOSTS):
        return None
    return f"{p.scheme}://{p.netloc}/"


def read_inputs(paths: list[str], column: str | None) -> list[str]:
    raw: list[str] = []
    for path in paths:
        if path.startswith(("http://", "https://")) or ("." in path and "/" not in path and not path.endswith((".csv", ".txt"))):
            raw.append(path); continue
        fh = sys.stdin if path == "-" else open(path, newline="", encoding="utf-8")
        with fh:
            if path.endswith(".csv"):
                rows = list(csv.DictReader(fh))
                col = column or next((c for c in (rows[0].keys() if rows else []) if c.lower() in ("website", "url", "site", "domain")), None)
                if not col:
                    raise SystemExit(f"{path}: no website/url column; pass --column")
                raw += [r.get(col, "") for r in rows]
            else:
                raw += fh.read().split()
    seen, out = set(), []
    for u in raw:
        n = normalize(u)
        if n and n not in seen:
            seen.add(n); out.append(n)
    return out


async def robots_ok(c: httpx.AsyncClient, url: str) -> bool:
    p = urlparse(url); rp = urllib.robotparser.RobotFileParser()
    try:
        r = await c.get(f"{p.scheme}://{p.netloc}/robots.txt", timeout=8)
        rp.parse(r.text.splitlines() if r.status_code < 400 else [])
    except Exception:
        rp.parse([])
    return rp.can_fetch(UA, url)


async def audit_one(c: httpx.AsyncClient, url: str, robots: bool) -> dict:
    out = {"url": url, "domain": urlparse(url).netloc}
    if robots and not await robots_ok(c, url):
        return {**out, "status": "blocked_by_robots_txt"}
    t0 = time.monotonic()
    try:
        r = await c.get(url)
    except Exception as e:
        return {**out, "status": "unreachable", "error": type(e).__name__}
    ms = int((time.monotonic() - t0) * 1000)
    if r.status_code >= 400:
        return {**out, "status": "http_error", "httpStatus": r.status_code, "responseMs": ms}
    if "html" not in r.headers.get("content-type", "html"):
        return {**out, "status": "not_html", "httpStatus": r.status_code}
    return {**out, "status": "ok", **audit(str(r.url), r.status_code, r.text[:MAX_PAGE_BYTES], dict(r.headers), ms)}


async def run(urls: list[str], concurrency: int, robots: bool) -> list[dict]:
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(follow_redirects=True, timeout=15, headers={"User-Agent": UA}) as c:
        async def one(u):
            async with sem:
                try:
                    return await asyncio.wait_for(audit_one(c, u, robots), 40)
                except asyncio.TimeoutError:
                    return {"url": u, "domain": urlparse(u).netloc, "status": "timeout"}
        return await asyncio.gather(*(one(u) for u in urls))


def flat(row: dict) -> dict:
    return {k: (";".join(t["name"] if isinstance(t, dict) else str(t) for t in v) if isinstance(v, list)
                else json.dumps(v) if isinstance(v, dict) else v) for k, v in row.items()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="site-health-audit", description="Audit homepages for health, SEO basics and tech stack (one GET each).")
    ap.add_argument("inputs", nargs="+", help="URLs/domains, .txt (one per line), .csv (website/url column), or - for stdin")
    ap.add_argument("--column", help="CSV column holding the website")
    ap.add_argument("-f", "--format", choices=["table", "json", "jsonl", "csv"], default="table")
    ap.add_argument("-o", "--output", help="write to file instead of stdout")
    ap.add_argument("-c", "--concurrency", type=int, default=10)
    ap.add_argument("--needs-help-only", action="store_true", help="only output sites flagged needsWebsiteHelp")
    ap.add_argument("--ignore-robots", action="store_true", help="skip robots.txt check (not recommended)")
    ap.add_argument("-V", "--version", action="version", version=__version__)
    a = ap.parse_args(argv)
    urls = read_inputs(a.inputs, a.column)
    if not urls:
        print("no valid websites found", file=sys.stderr); return 2
    rows = asyncio.run(run(urls, max(1, min(a.concurrency, 40)), not a.ignore_robots))
    if a.needs_help_only:
        rows = [r for r in rows if r.get("needsWebsiteHelp")]
    out = open(a.output, "w", newline="", encoding="utf-8") if a.output else sys.stdout
    if a.format == "json":
        json.dump(rows, out, indent=2); out.write("\n")
    elif a.format == "jsonl":
        for r in rows: out.write(json.dumps(r) + "\n")
    elif a.format == "csv":
        fr = [flat(r) for r in rows]; keys: list[str] = []
        for r in fr: keys += [k for k in r if k not in keys]
        w = csv.DictWriter(out, fieldnames=keys); w.writeheader(); w.writerows(fr)
    else:
        out.write(f"{'score':>5}  {'help':4}  {'status':12}  domain / tech\n")
        for r in sorted(rows, key=lambda r: r.get("healthScore", -1)):
            tech = ", ".join(t["name"] if isinstance(t, dict) else str(t) for t in r.get("tech", []) or [])
            out.write(f"{r.get('healthScore', '-'):>5}  {'yes' if r.get('needsWebsiteHelp') else '':4}  {r['status']:12}  {r['domain']}  {tech}\n")
    if a.output: out.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
