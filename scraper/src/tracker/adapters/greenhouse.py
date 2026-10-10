from ..models import Company, Posting
from .base import Context, get_json, parse_date


async def fetch(company: Company, ctx: Context) -> list[Posting]:
    slug = company.ats["slug"]
    data = await get_json(ctx.client, f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
    out = []
    for j in data.get("jobs", []):
        locs = [j.get("location", {}).get("name", "")] + [o.get("name", "") for o in j.get("offices", [])]
        out.append(
            Posting(
                company_id=company.id,
                source_id=str(j["id"]),
                title=j["title"],
                url=j["absolute_url"],
                location="; ".join(dict.fromkeys(filter(None, locs))),
                posted_at=parse_date(j.get("first_published") or j.get("updated_at")),
            )
        )
    return out
