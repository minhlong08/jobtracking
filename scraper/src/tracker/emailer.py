import os
import smtplib
from collections import defaultdict
from email.message import EmailMessage
from pathlib import Path

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


def send(subject: str, html: str) -> None:
    user, password = os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"]
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"Intern Tracker <{user}>"
    msg["To"] = os.environ.get("EMAIL_TO", user)
    msg.set_content("This email is HTML; please view it in an HTML-capable client.")
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, password)
        s.send_message(msg)
