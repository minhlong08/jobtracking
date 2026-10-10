"""Daily run: scrape every company, update data/jobs.json, email what's new.

python -m tracker.run [--dry-run] [--only id1,id2] [--no-email]
"""
import argparse
import asyncio
import json
import os
import sys
import time
import traceback
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from . import emailer, store
from .adapters import adapter_for
from .adapters.base import Context, make_client
from .filters import classify, clean_location
from .models import Company, Job

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"
COMPANY_TIMEOUT = 300
ZERO_DAYS_WARNING = 7


def log(*a):
    print(*a, file=sys.stderr, flush=True)


async def scrape_one(company: Company, ctx: Context) -> tuple[list, str | None, float]:
    start = time.monotonic()
    try:
        postings = await asyncio.wait_for(adapter_for(company)(company, ctx), COMPANY_TIMEOUT)
        return postings, None, time.monotonic() - start
    except Exception as e:  # noqa: BLE001 - one company must never break the run
        msg = f"{type(e).__name__}: {e}"[:300]
        if os.environ.get("TRACKER_DEBUG"):
            traceback.print_exc()
        return [], msg, time.monotonic() - start


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print matches; write nothing, send nothing")
    ap.add_argument("--only", help="comma-separated company ids")
    ap.add_argument("--no-email", action="store_true")
    ap.add_argument("--concurrency", type=int, default=8)
    args = ap.parse_args()

    today = datetime.now(ZoneInfo("Australia/Sydney")).date()
    companies = [Company(**c) for c in yaml.safe_load((DATA / "companies.yaml").read_text())]
    manual = [c for c in companies if not c.enabled]
    companies = [c for c in companies if c.enabled]
    if args.only:
        wanted = set(args.only.split(","))
        companies = [c for c in companies if c.id in wanted]

    health_path = DATA / "health.json"
    health = json.loads(health_path.read_text()) if health_path.exists() else {}
    cache_dir = DATA / "llm_cache"
    cache_dir.mkdir(exist_ok=True)

    found: list[Job] = []
    ok_companies: set[str] = set()
    sem = asyncio.Semaphore(args.concurrency)
    async with make_client() as client:
        ctx = Context(client=client, today=today, cache_dir=cache_dir)

        async def run(company: Company):
            async with sem:
                postings, err, secs = await scrape_one(company, ctx)
            matched = []
            for p in postings:
                hit = classify(p.title, p.location, company.sector)
                if hit:
                    level, category = hit
                    matched.append(
                        Job(
                            id=store.job_id(company.id, p.source_id), company_id=company.id,
                            company=company.name, sector=company.sector, title=p.title.strip(),
                            url=p.url, location=clean_location(p.location), level=level, category=category,
                            posted_at=p.posted_at, first_seen=today, last_seen=today,
                        )
                    )
            # The same role can appear under several search terms or locations.
            matched = list({j.id: j for j in matched}.values())
            h = health.setdefault(company.id, {})
            h.update(name=company.name, source=(company.ats or {}).get("type", "llm"), last_run=str(today), seconds=round(secs, 1))
            if err:
                h.update(status="error", error=err)
                log(f"  ✗ {company.id:<32} {err[:120]}")
            else:
                ok_companies.add(company.id)
                h.update(status="ok", error=None, raw=len(postings), matched=len(matched), last_ok=str(today))
                h.setdefault("first_ok", str(today))
                if postings:
                    h["last_nonzero"] = str(today)
                log(f"  ✓ {company.id:<32} {len(postings):>5} postings  {len(matched):>3} matched  ({secs:.0f}s)")
            if company.id in ctx.ats_hints:
                h["ats_hint"] = ctx.ats_hints[company.id]
            found.extend(matched)

        try:
            await asyncio.gather(*(run(c) for c in companies))
        finally:
            await ctx.close()

    if args.dry_run:
        for j in sorted(found, key=lambda j: (j.company, j.title)):
            print(f"{j.company:<25} {j.level:<13} {j.category:<20} {j.title[:60]:<60} {j.location[:40]}  {j.url}")
        log(f"\n{len(found)} matched jobs, {len(ok_companies)}/{len(companies)} companies OK")
        return

    jobs_path = DATA / "jobs.json"
    db = store.load(jobs_path)
    baseline = db.get("baseline_date") is None
    if baseline:
        db["baseline_date"] = str(today)
    new = store.merge(db, found, ok_companies, today)
    # Roles from a company scraped successfully for the first time today were
    # already open, so they go on the board without being announced as new.
    first_run = {cid for cid in ok_companies if health[cid].get("first_ok") == str(today)}
    initial = [j for j in new if baseline or j.company_id in first_run]
    announce = [j for j in new if j not in initial]
    initial_ids = {j.id for j in initial}
    for j in db["jobs"]:
        if j["id"] in initial_ids:
            j["initial"] = True
    db["manual"] = [
        {"id": c.id, "name": c.name, "sector": c.sector, "url": c.careers_url, "reason": c.manual_reason or ""}
        for c in manual
    ]
    db["updated_at"] = datetime.now(ZoneInfo("Australia/Sydney")).isoformat(timespec="minutes")
    store.save(jobs_path, db)
    health_path.write_text(json.dumps(dict(sorted(health.items())), indent=1) + "\n")

    total_open = sum(1 for j in db["jobs"] if not j.get("closed"))
    log(f"\n{len(found)} matched, {len(announce)} new, {len(initial)} initial, {total_open} open, {len(ok_companies)}/{len(companies)} companies OK")

    if args.no_email or not os.environ.get("RESEND_API_KEY"):
        log("email skipped")
        return
    by_id = {c.id: c for c in companies}
    problems = []
    for cid, h in sorted(health.items()):
        if cid not in by_id:
            continue
        if h.get("status") == "error":
            problems.append({"name": h["name"], "url": by_id[cid].careers_url, "reason": h["error"][:100]})
        elif (date.fromisoformat(h.get("last_nonzero", "2000-01-01")) - today).days <= -ZERO_DAYS_WARNING:
            problems.append({"name": h["name"], "url": by_id[cid].careers_url, "reason": f"no postings since {h.get('last_nonzero', 'ever')}"})

    if baseline:
        subject = f"Intern Tracker started: {total_open} open roles"
        headline = f"Tracking started: {total_open} early-career tech roles open right now"
        shown = sorted(initial, key=lambda j: (j.company, j.title))
        initial_count = 0
    else:
        subject = f"{len(announce)} new intern/grad tech role{'s' if len(announce) != 1 else ''}" if announce else "No new intern/grad roles today"
        headline = subject
        shown = announce
        initial_count = len(initial)
    html = emailer.render(
        shown, headline=headline, today=today, total_open=total_open, ok_count=len(ok_companies),
        site_url=os.environ.get("SITE_URL", ""), problems=problems, initial_count=initial_count,
    )
    emailer.send(subject, html)
    log(f"email sent: {subject}")


if __name__ == "__main__":
    asyncio.run(main())
