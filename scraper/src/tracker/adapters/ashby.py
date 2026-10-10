from ..models import Company, Posting
from .base import Context, get_json, parse_date


async def fetch(company: Company, ctx: Context) -> list[Posting]:
    slug = company.ats["slug"]
    data = await get_json(ctx.client, f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    out = []
    for j in data.get("jobs", []):
        if j.get("isListed") is False:
            continue
        locs = [j.get("location", "")]
        locs += [s.get("location", "") for s in j.get("secondaryLocations") or []]
        country = ((j.get("address") or {}).get("postalAddress") or {}).get("addressCountry")
        locs.append(country or "")
        out.append(
            Posting(
                company_id=company.id,
                source_id=j["id"],
                title=j["title"],
                url=j["jobUrl"],
                location="; ".join(dict.fromkeys(filter(None, locs))),
                posted_at=parse_date(j.get("publishedAt")),
            )
        )
    return out
