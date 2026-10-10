"""Persist matched jobs in data/jobs.json and work out what is new."""
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

from .models import Job

CLOSE_AFTER_MISSES = 3
PRUNE_AFTER_DAYS = 90


def job_id(company_id: str, source_id: str) -> str:
    return hashlib.sha1(f"{company_id}|{source_id}".encode()).hexdigest()[:16]


def load(path: Path) -> dict:
    if not path.exists():
        return {"baseline_date": None, "jobs": []}
    return json.loads(path.read_text())


def save(path: Path, db: dict) -> None:
    db["jobs"].sort(key=lambda j: (j["first_seen"], j["company"], j["title"]), reverse=True)
    path.write_text(json.dumps(db, indent=1, default=str) + "\n")


def merge(db: dict, found: list[Job], ok_companies: set[str], today: date) -> list[Job]:
    """Merge this run's matches into db; return jobs first seen today.

    Jobs from companies whose scrape failed this run are left untouched, so a
    flaky site never makes its jobs look closed (or re-new when it recovers).
    """
    existing = {j["id"]: j for j in db["jobs"]}
    found_ids = set()
    new: list[Job] = []
    for job in found:
        found_ids.add(job.id)
        old = existing.get(job.id)
        if old is None:
            existing[job.id] = json.loads(job.model_dump_json())
            new.append(job)
        else:
            old.update(
                title=job.title, url=job.url, location=job.location, level=job.level,
                category=job.category, last_seen=str(today), missed_runs=0, closed=False,
            )
            if job.posted_at and not old.get("posted_at"):
                old["posted_at"] = str(job.posted_at)

    for jid, j in existing.items():
        if jid not in found_ids and j["company_id"] in ok_companies and not j.get("closed"):
            j["missed_runs"] = j.get("missed_runs", 0) + 1
            if j["missed_runs"] >= CLOSE_AFTER_MISSES:
                j["closed"] = True

    cutoff = str(today - timedelta(days=PRUNE_AFTER_DAYS))
    db["jobs"] = [j for j in existing.values() if j["first_seen"] >= cutoff]
    return new
