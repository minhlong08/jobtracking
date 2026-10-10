from ..models import Company, Posting
from .base import Context, get_json, parse_date


async def fetch(company: Company, ctx: Context) -> list[Posting]:
    slug = company.ats["slug"]
    data = await get_json(ctx.client, f"https://api.lever.co/v0/postings/{slug}?mode=json")
    out = []
    for j in data:
        cats = j.get("categories", {})
        locs = [cats.get("location", "")] + list(cats.get("allLocations") or []) + [j.get("country", "")]
        out.append(
            Posting(
                company_id=company.id,
                source_id=j["id"],
                title=j["text"],
                url=j["hostedUrl"],
                location="; ".join(dict.fromkeys(filter(None, locs))),
                posted_at=parse_date(j.get("createdAt")),
            )
        )
    return out
