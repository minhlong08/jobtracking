"""Atlassian's careers listing JSON (backed by iCIMS)."""
from ..models import Company, Posting
from .base import Context, get_json, parse_date


async def fetch(company: Company, ctx: Context) -> list[Posting]:
    data = await get_json(ctx.client, "https://www.atlassian.com/endpoint/careers/listings")
    out = []
    for j in data:
        portal = j.get("portalJobPost") or {}
        out.append(
            Posting(
                company_id=company.id,
                source_id=str(j["id"]),
                title=j["title"],
                url=portal.get("portalUrl") or f"https://www.atlassian.com/company/careers/details/{j['id']}",
                location="; ".join(j.get("locations") or []),
                posted_at=parse_date((portal.get("updatedDate") or "")[:10]),
            )
        )
    return out
