from datetime import date

from pydantic import BaseModel


class Company(BaseModel):
    id: str
    name: str
    sector: str
    careers_url: str
    ats: dict | None = None
    enabled: bool = True
    manual_reason: str | None = None


class Posting(BaseModel):
    """A raw job posting as returned by an adapter, before filtering."""

    company_id: str
    source_id: str  # stable id from the ATS, or the posting URL
    title: str
    url: str
    location: str = ""
    posted_at: date | None = None


class Job(BaseModel):
    """A posting that passed the filters, as stored in data/jobs.json."""

    id: str
    company_id: str
    company: str
    sector: str
    title: str
    url: str
    location: str
    level: str  # Intern | Graduate | Early career
    category: str  # Software | Data & Analytics | ML/AI | Infra/Cloud/Security | Other tech | General program
    posted_at: date | None = None
    first_seen: date
    last_seen: date
    missed_runs: int = 0
    closed: bool = False
