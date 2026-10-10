"""amazon.jobs search JSON."""
from ..models import Company, Posting
from .base import Context, get_json, parse_date

SEARCH_TERMS = ["intern", "graduate", "early career", "entry level", "student", "university"]


async def fetch(company: Company, ctx: Context) -> list[Posting]:
    seen: dict[str, Posting] = {}
    for term in SEARCH_TERMS:
        for offset in range(0, 300, 100):
            data = await get_json(
                ctx.client,
                "https://www.amazon.jobs/en/search.json",
                params={"base_query": term, "country": "AUS", "result_limit": 100, "offset": offset, "sort": "recent"},
            )
            jobs = data.get("jobs", [])
            for j in jobs:
                seen[j["id_icims"]] = Posting(
                    company_id=company.id,
                    source_id=str(j["id_icims"]),
                    title=j["title"],
                    url=f"https://www.amazon.jobs{j['job_path']}",
                    location=f"{j.get('normalized_location') or j.get('location', '')}, Australia",
                    posted_at=parse_date(j.get("posted_date")),
                )
            if len(jobs) < 100:
                break
    return list(seen.values())
