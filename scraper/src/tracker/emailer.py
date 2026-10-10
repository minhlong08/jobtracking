import os
from collections import defaultdict
from pathlib import Path

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import Job

CATEGORY_ORDER = ["Software", "Data & Analytics", "ML/AI", "Infra/Cloud/Security", "Other tech", "General program"]
_env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"), autoescape=select_autoescape())


def render(new: list[Job], *, headline: str, **ctx) -> str:
    groups: dict[str, dict[str, list[Job]]] = defaultdict(lambda: defaultdict(list))
    for j in new:
        groups[j.category][j.company].append(j)
    ordered = [
        (cat, sorted(groups[cat].items()))
        for cat in CATEGORY_ORDER
        if cat in groups
    ]
    return _env.get_template("email.html").render(groups=ordered, headline=headline, **ctx)


RESEND_URL = "https://api.resend.com/emails"
# Resend's shared sender works without a verified domain, but only delivers
# to the address the Resend account was created with.
DEFAULT_FROM = "Intern Tracker <onboarding@resend.dev>"


def send(subject: str, html: str, transport: httpx.BaseTransport | None = None) -> None:
    """Send via Resend. Its API key can only send email, never read a mailbox."""
    payload = {
        "from": os.environ.get("EMAIL_FROM") or DEFAULT_FROM,
        "to": [os.environ["EMAIL_TO"]],
        "subject": subject,
        "html": html,
    }
    headers = {"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}"}
    with httpx.Client(timeout=30, transport=transport) as client:
        r = client.post(RESEND_URL, json=payload, headers=headers)
    if r.status_code >= 400:
        raise RuntimeError(f"Resend rejected the email ({r.status_code}): {r.text[:300]}")
