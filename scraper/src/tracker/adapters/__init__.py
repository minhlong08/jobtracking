"""Adapters fetch raw postings for one company from one kind of source."""
from collections.abc import Awaitable, Callable

from ..models import Company, Posting
from .base import Context
from . import amazon, ashby, atlassian, greenhouse, lever, llm_page, oracle_hcm, smartrecruiters, workday

Adapter = Callable[[Company, Context], Awaitable[list[Posting]]]

ADAPTERS: dict[str, Adapter] = {
    "greenhouse": greenhouse.fetch,
    "lever": lever.fetch,
    "ashby": ashby.fetch,
    "smartrecruiters": smartrecruiters.fetch,
    "workday": workday.fetch,
    "oracle_hcm": oracle_hcm.fetch,
    "amazon": amazon.fetch,
    "atlassian": atlassian.fetch,
    "llm": llm_page.fetch,
}


def adapter_for(company: Company) -> Adapter:
    kind = (company.ats or {}).get("type", "llm")
    # ATS types we detect but have no API adapter for are scraped from the rendered page.
    return ADAPTERS.get(kind, llm_page.fetch)


def needs_llm(company: Company) -> bool:
    """True if this company can only be read by the Claude page fallback."""
    return adapter_for(company) is llm_page.fetch
