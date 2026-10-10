"""Detect which applicant-tracking system each company uses.

Fetches each careers URL (and a few "search jobs" links it points to), looks for
known ATS URL signatures, and writes the result into data/companies.yaml under `ats`.
Entries that already have an `ats` value are skipped unless --force is passed.

Usage: python scraper/scripts/discover_ats.py [--force] [--only id1,id2]
"""
import argparse
import asyncio
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin

import httpx
import yaml

from tracker.ats_detect import detect

ROOT = Path(__file__).resolve().parents[2]
COMPANIES = ROOT / "data" / "companies.yaml"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

LINK_HINT = re.compile(r"(search|view|browse|find|open|current|all)[\s-]*(jobs|roles|positions|opportunities|vacancies)|job search|graduate|early career|student", re.I)


async def probe(client: httpx.AsyncClient, company: dict) -> tuple[dict | None, str]:
    url = company["careers_url"]
    try:
        r = await client.get(url)
    except Exception as e:  # noqa: BLE001
        return None, f"fetch error: {type(e).__name__}"
    status = f"http {r.status_code}"
    final = str(r.url)
    ats = detect(final) or detect(r.text)
    if ats:
        return ats, status
    # Follow up to 6 job-search-looking links one level deep.
    links = re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', r.text, re.S | re.I)
    candidates = []
    for href, label in links:
        label_text = re.sub(r"<[^>]+>", " ", label)
        if LINK_HINT.search(label_text) or LINK_HINT.search(href):
            candidates.append(urljoin(final, href))
    for link in list(dict.fromkeys(candidates))[:6]:
        ats = detect(link)
        if ats:
            return ats, status
        try:
            r2 = await client.get(link)
        except Exception:  # noqa: BLE001
            continue
        ats = detect(str(r2.url)) or detect(r2.text)
        if ats:
            return ats, status
    return None, status


async def probe_browser(browser, company: dict) -> tuple[dict | None, list[str]]:
    """Render the careers page (and its best job-search link) and watch network traffic."""
    seen: list[str] = []
    page = await browser.new_page(user_agent=UA)
    page.on("request", lambda req: seen.append(req.url))
    try:
        await page.goto(company["careers_url"], wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)
        hrefs = await page.eval_on_selector_all(
            "a[href]", "els => els.map(e => [e.href, (e.innerText || '').trim()])"
        )
        seen.extend(h for h, _ in hrefs)
        ats = detect(page.url) or next((a for a in map(detect, seen) if a), None)
        if not ats:
            links = [h for h, t in hrefs if LINK_HINT.search(t) or LINK_HINT.search(h)]
            for link in list(dict.fromkeys(links))[:3]:
                try:
                    await page.goto(link, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)
                except Exception:  # noqa: BLE001
                    continue
                more = await page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
                seen.extend(more)
                ats = detect(page.url) or next((a for a in map(detect, seen) if a), None)
                if ats:
                    break
    except Exception:  # noqa: BLE001
        ats = None
    finally:
        await page.close()
    return ats, seen


async def main_browser(companies: list[dict], todo: list[dict]) -> None:
    from playwright.async_api import async_playwright

    sem = asyncio.Semaphore(4)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()

        async def run(c):
            async with sem:
                ats, _ = await probe_browser(browser, c)
                print(f"{c['id']:<35} browser {ats}", file=sys.stderr)
                if ats:
                    c["ats"] = ats

        await asyncio.gather(*(run(c) for c in todo))
        await browser.close()


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--browser", action="store_true", help="render pages with Playwright (slower, finds JS-loaded ATS)")
    args = ap.parse_args()
    only = set(args.only.split(",")) if args.only else None

    companies = yaml.safe_load(COMPANIES.read_text())
    todo = [c for c in companies if (args.force or not c.get("ats")) and (not only or c["id"] in only)]
    if args.browser:
        await main_browser(companies, todo)
        COMPANIES.write_text(yaml.safe_dump(companies, sort_keys=False, allow_unicode=True, width=200))
        counts = Counter((c.get("ats") or {}).get("type", "unknown") for c in companies)
        print("\ncoverage:", dict(counts.most_common()), file=sys.stderr)
        return
    sem = asyncio.Semaphore(10)
    async with httpx.AsyncClient(headers={"User-Agent": UA}, follow_redirects=True, timeout=20) as client:

        async def run(c):
            async with sem:
                ats, status = await probe(client, c)
                print(f"{c['id']:<35} {status:<22} {ats}", file=sys.stderr)
                if ats:
                    c["ats"] = ats
                c["_probe"] = status

        await asyncio.gather(*(run(c) for c in todo))

    for c in companies:
        c.pop("_probe", None)
    COMPANIES.write_text(yaml.safe_dump(companies, sort_keys=False, allow_unicode=True, width=200))
    counts = Counter((c.get("ats") or {}).get("type", "unknown") for c in companies)
    print("\ncoverage:", dict(counts.most_common()), file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
