from ..models import Company, Posting
from .base import Context, get_json, parse_date


async def fetch(company: Company, ctx: Context) -> list[Posting]:
    slug = company.ats["slug"]
    out, offset = [], 0
    while True:
        data = await get_json(
            ctx.client,
            f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
            params={"country": "au", "limit": 100, "offset": offset},
        )
        for j in data.get("content", []):
            loc = j.get("location", {})
            location = ", ".join(filter(None, [loc.get("city"), loc.get("region"), loc.get("country", "").upper()]))
            if loc.get("country", "").lower() == "au":
                location += ", Australia"
            if loc.get("remote"):
                location += " (Remote)"
            out.append(
                Posting(
                    company_id=company.id,
                    source_id=j["id"],
                    title=j["name"],
                    url=f"https://jobs.smartrecruiters.com/{slug}/{j['id']}",
                    location=location,
                    posted_at=parse_date(j.get("releasedDate")),
                )
            )
        offset += 100
        if offset >= data.get("totalFound", 0) or offset >= 2000:
            return out
