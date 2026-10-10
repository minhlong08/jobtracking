"""Fallback for career sites without a usable API.

Renders the page with Playwright, then asks Claude to pick out job postings.
Claude answers with indices into the page's own link list, so every URL we
store really exists on the page. Results are cached by a hash of the page
content, so unchanged pages cost nothing on later runs.
"""
import hashlib
import json
import os

import anthropic
from pydantic import BaseModel

from ..ats_detect import detect
from ..models import Company, Posting
from .base import Context, parse_date

MODEL = os.environ.get("LLM_MODEL", "claude-haiku-5-5")
MAX_TEXT = 40_000
MAX_LINKS = 400
MAX_HOPS = 2

SYSTEM = """You read the rendered text and link list of a company careers web page and extract job postings.

Return every individual job posting visible on the page (any seniority; filtering happens later).
For each, give its title exactly as shown, the index of the link that opens that specific posting,
its location if shown, and its posted date (YYYY-MM-DD) if shown.

Only use link indices from the provided list. Skip generic links (e.g. "Search jobs", "Graduates", "Life at X")
that are not one specific posting.

If the page lists no individual postings but has a link that leads to a job search/listing page
(ideally filtered to students, graduates, interns or early careers, or to Australia), set next_link_index to it."""


class ExtractedJob(BaseModel):
    title: str
    link_index: int
    location: str | None = None
    posted_date: str | None = None


class Extraction(BaseModel):
    jobs: list[ExtractedJob]
    next_link_index: int | None = None


async def _render(ctx: Context, url: str) -> tuple[str, str, list[tuple[str, str]]]:
    page = await ctx.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:  # noqa: BLE001 - some pages never go idle
            pass
        for _ in range(4):  # trigger lazy-loaded lists
            await page.mouse.wheel(0, 4000)
            await page.wait_for_timeout(700)
        text = await page.evaluate("() => document.body ? document.body.innerText : ''")
        links = await page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => [(e.innerText || e.getAttribute('aria-label') || '').trim().replace(/\\s+/g,' ').slice(0,150), e.href])",
        )
        final_url = page.url
    finally:
        await page.context.close()
    seen, uniq = set(), []
    for label, href in links:
        if href.startswith("http") and href not in seen and label:
            seen.add(href)
            uniq.append((label, href))
    return final_url, text[:MAX_TEXT], uniq[:MAX_LINKS]


async def _extract(client: anthropic.AsyncAnthropic, url: str, text: str, links: list[tuple[str, str]]) -> Extraction:
    link_list = "\n".join(f"[{i}] {label} -> {href}" for i, (label, href) in enumerate(links))
    response = await client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Page URL: {url}\n\n<page_text>\n{text}\n</page_text>\n\n<links>\n{link_list}\n</links>",
            }
        ],
        output_format=Extraction,
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise RuntimeError(f"LLM extraction failed: stop_reason={response.stop_reason}")
    return response.parsed_output


async def fetch(company: Company, ctx: Context) -> list[Posting]:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set; cannot scrape non-ATS page")
    url = (company.ats or {}).get("search_url") or company.careers_url
    client = anthropic.AsyncAnthropic()
    cache_file = ctx.cache_dir / f"{company.id}.json"
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}

    postings: list[Posting] = []
    async with ctx.browser_lock:
        for _ in range(MAX_HOPS):
            final_url, text, links = await _render(ctx, url)
            hint = detect(final_url) or next((a for a in (detect(h) for _, h in links) if a), None)
            if hint:
                ctx.ats_hints[company.id] = hint
            key = hashlib.sha256((final_url + text + json.dumps(links)).encode()).hexdigest()
            if cache.get("key") == key:
                result = Extraction.model_validate(cache["result"])
            else:
                result = await _extract(client, final_url, text, links)
                cache = {"key": key, "url": final_url, "result": result.model_dump()}
                cache_file.write_text(json.dumps(cache, indent=1))
            for j in result.jobs:
                if 0 <= j.link_index < len(links):
                    href = links[j.link_index][1]
                    postings.append(
                        Posting(
                            company_id=company.id,
                            source_id=href,
                            title=j.title,
                            url=href,
                            location=j.location or "",
                            posted_at=parse_date(j.posted_date),
                        )
                    )
            nxt = result.next_link_index
            if postings or nxt is None or not (0 <= nxt < len(links)):
                break
            url = links[nxt][1]
    return postings
