"""Import the company spreadsheet into data/companies.yaml.

Re-runnable: existing entries keep any manual edits (ats, search_url, enabled...);
only name/sector/careers_url are refreshed from the spreadsheet.
"""
import re
import sys
from pathlib import Path

import openpyxl
import yaml

ROOT = Path(__file__).resolve().parents[2]
XLSX = ROOT / "AU_Tech_Intern_Companies_top200.xlsx"
OUT = ROOT / "data" / "companies.yaml"


def slugify(name: str) -> str:
    name = re.sub(r"\(.*?\)", "", name)
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def main() -> None:
    wb = openpyxl.load_workbook(XLSX, read_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    header = [str(h).strip() if h else "" for h in rows[0]]
    idx = {h: i for i, h in enumerate(header)}

    existing = {}
    if OUT.exists():
        for c in yaml.safe_load(OUT.read_text()) or []:
            existing[c["id"]] = c

    companies = []
    for r in rows[1:]:
        if len(r) <= idx["Careers page (click)"]:
            continue
        name = r[idx["Company"]]
        if not name:
            continue
        cid = slugify(str(name))
        entry = existing.get(cid, {})
        entry.update(
            id=cid,
            name=str(name).strip(),
            sector=str(r[idx["Sector"]]).strip(),
            careers_url=str(r[idx["Careers page (click)"]]).strip(),
        )
        entry.setdefault("ats", None)
        companies.append(entry)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(yaml.safe_dump(companies, sort_keys=False, allow_unicode=True, width=200))
    print(f"wrote {len(companies)} companies to {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
