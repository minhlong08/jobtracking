"""Oracle Recruiting Cloud (Candidate Experience) public REST API."""
from ..models import Company, Posting
from .base import Context, get_json, parse_date

SEARCH_TERMS = ["intern", "graduate", "early career", "entry level", "junior", "student", "vacation", "cadet"]


async def fetch(company: Company, ctx: Context) -> list[Posting]:
    host, site = company.ats["host"], company.ats["site"]
    api = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    seen: dict[str, Posting] = {}
    for term in SEARCH_TERMS:
        for offset in range(0, 200, 50):
            finder = (
                f'findReqs;siteNumber={site},keyword="{term}",limit=50,offset={offset},'
                f"sortBy=POSTING_DATES_DESC"
            )
            data = await get_json(
                ctx.client,
                api,
                params={"onlyData": "true", "expand": "requisitionList.secondaryLocations", "finder": finder},
            )
            items = (data.get("items") or [{}])[0].get("requisitionList", [])
            for j in items:
                locs = [j.get("PrimaryLocation", ""), j.get("PrimaryLocationCountry", "")]
                locs += [s.get("Name", "") for s in j.get("secondaryLocations") or []]
                seen[j["Id"]] = Posting(
                    company_id=company.id,
                    source_id=str(j["Id"]),
                    title=j["Title"],
                    url=f"https://{host}/hcmUI/CandidateExperience/en/sites/{site}/job/{j['Id']}",
                    location="; ".join(dict.fromkeys(filter(None, locs))),
                    posted_at=parse_date(j.get("PostedDate")),
                )
            if len(items) < 50:
                break
    return list(seen.values())
