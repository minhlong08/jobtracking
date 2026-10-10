"""Recognise applicant-tracking systems from URLs."""
import re

# (type, regex). Named groups become ats fields.
SIGNATURES = [
    ("workday", r"https?://(?P<tenant>[\w-]+)\.(?P<wd>wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?(?P<site>[\w-]+)"),
    ("greenhouse", r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?(?P<slug>[\w-]+)"),
    ("greenhouse", r"boards-api\.greenhouse\.io/v1/boards/(?P<slug>[\w-]+)"),
    ("lever", r"jobs\.(?:eu\.)?lever\.co/(?P<slug>[\w-]+)"),
    ("ashby", r"jobs\.ashbyhq\.com/(?P<slug>[\w.-]+)"),
    ("smartrecruiters", r"(?:jobs|careers)\.smartrecruiters\.com/(?P<slug>[\w-]+)"),
    ("workable", r"apply\.workable\.com/(?P<slug>[\w-]+)"),
    ("pageup", r"https?://(?P<host>(?:careers|jobs)\.pageuppeople\.com)/(?P<instance>\d+)/(?P<portal>[\w-]+)"),
    ("eightfold", r"https?://(?P<host>[\w.-]+\.eightfold\.ai)"),
    ("oracle_hcm", r"https?://(?P<host>[\w-]+\.fa\.[\w.-]*oraclecloud\.com)/hcmUI/CandidateExperience/[\w-]+/sites/(?P<site>[\w-]+)"),
    ("successfactors", r"https?://(?P<host>career\d*\.successfactors\.(?:com|eu))/career\?company=(?P<company>[\w-]+)"),
    ("apsjobs", r"apsjobs\.gov\.au"),
]

def detect(text: str) -> dict | None:
    for kind, pattern in SIGNATURES:
        m = re.search(pattern, text)
        if m:
            ats = {"type": kind, **{k: v for k, v in m.groupdict().items() if v}}
            # ignore generic path segments that are not tenants
            if kind in ("greenhouse", "lever", "ashby", "smartrecruiters", "workable") and ats.get("slug") in ("embed", "js", "api", "v1"):
                continue
            return ats
    return None
