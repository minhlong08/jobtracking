"""Workday career sites (the cxs JSON API behind *.myworkdayjobs.com)."""
import re

from ..filters import classify_title
from ..models import Company, Posting
from .base import Context, parse_date

SEARCH_TERMS = ["intern", "graduate", "early career", "entry level", "junior", "student", "vacation", "cadet"]
PAGE = 20  # Workday rejects larger page sizes


def _find_au_facet(facets: list) -> tuple[str, str] | None:
    """Find (facetParameter, id) for Australia among Workday location facets (possibly nested)."""
    for f in facets or []:
        param = f.get("facetParameter", "")
        for v in f.get("values", []):
            if "values" in v:  # nested group
                hit = _find_au_facet([{"facetParameter": v.get("facetParameter", param), "values": v["values"]}])
                if hit:
                    return hit
            elif v.get("descriptor", "").strip().lower() == "australia" and "country" in param.lower():
                return param, v["id"]
    return None


async def fetch(company: Company, ctx: Context) -> list[Posting]:
    a = company.ats
    host = f"https://{a['tenant']}.{a['wd']}.myworkdayjobs.com"
    api = f"{host}/wday/cxs/{a['tenant']}/{a['site']}/jobs"

    async def page(body: dict) -> dict:
        r = await ctx.client.post(api, json={"appliedFacets": {}, "limit": PAGE, "offset": 0, "searchText": "", **body})
        r.raise_for_status()
        return r.json()

    first = await page({"limit": 1})
    au = _find_au_facet(first.get("facets", []))

    raw: dict[str, dict] = {}
    if au:
        # Every Australian posting; usually a few hundred at most.
        offset, total = 0, None
        while total is None or offset < min(total, 1500):
            data = await page({"appliedFacets": {au[0]: [au[1]]}, "offset": offset})
            total = data.get("total", 0) if total is None else total
            for j in data.get("jobPostings", []):
                raw[j["externalPath"]] = j
            if not data.get("jobPostings"):
                break
            offset += PAGE
        location_known = True
    else:
        for term in SEARCH_TERMS:
            for offset in range(0, 100, PAGE):
                data = await page({"searchText": term, "offset": offset})
                for j in data.get("jobPostings", []):
                    raw[j["externalPath"]] = j
                if len(data.get("jobPostings", [])) < PAGE:
                    break
        location_known = False

    out = []
    for path, j in raw.items():
        title = j.get("title", "")
        location = j.get("locationsText", "")
        if location_known:
            location = f"{location}, Australia" if location else "Australia"
        elif re.match(r"\d+ Locations", location) and classify_title(title, company.sector):
            # Only resolve multi-location postings for titles we would keep.
            try:
                r = await ctx.client.get(f"{host}/wday/cxs/{a['tenant']}/{a['site']}{path}")
                info = r.json().get("jobPostingInfo", {})
                location = "; ".join(
                    filter(None, [info.get("location", "")] + list(info.get("additionalLocations") or []) + [info.get("country", {}).get("descriptor", "")])
                )
            except Exception:  # noqa: BLE001
                pass
        req_id = (j.get("bulletFields") or [path])[0]
        out.append(
            Posting(
                company_id=company.id,
                source_id=req_id,
                title=title,
                url=f"{host}/en-US/{a['site']}{path}",
                location=location,
                posted_at=parse_date(j.get("postedOn")),
            )
        )
    return out
