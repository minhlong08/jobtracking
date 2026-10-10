from datetime import date, timedelta

from tracker import store
from tracker.models import Job

D0 = date(2026, 10, 1)


def job(cid="acme", sid="1", day=D0, title="Software Engineer Intern"):
    return Job(
        id=store.job_id(cid, sid), company_id=cid, company=cid.title(), sector="x", title=title,
        url=f"https://x/{sid}", location="Sydney", level="Intern", category="Software",
        first_seen=day, last_seen=day,
    )


def test_new_then_seen_again_is_not_new():
    db = {"jobs": []}
    assert len(store.merge(db, [job()], {"acme"}, D0)) == 1
    later = D0 + timedelta(days=1)
    assert store.merge(db, [job(day=later)], {"acme"}, later) == []
    assert db["jobs"][0]["first_seen"] == str(D0)
    assert db["jobs"][0]["last_seen"] == str(later)


def test_closed_after_three_missed_successful_runs_and_reopens():
    db = {"jobs": []}
    store.merge(db, [job()], {"acme"}, D0)
    for i in range(1, 4):
        store.merge(db, [], {"acme"}, D0 + timedelta(days=i))
    assert db["jobs"][0]["closed"] is True
    store.merge(db, [job()], {"acme"}, D0 + timedelta(days=5))
    assert db["jobs"][0]["closed"] is False


def test_failed_company_jobs_untouched():
    db = {"jobs": []}
    store.merge(db, [job()], {"acme"}, D0)
    for i in range(1, 6):
        store.merge(db, [], set(), D0 + timedelta(days=i))  # acme scrape failed
    assert db["jobs"][0]["missed_runs"] == 0 and db["jobs"][0]["closed"] is False


def test_old_jobs_pruned():
    db = {"jobs": []}
    store.merge(db, [job()], {"acme"}, D0)
    store.merge(db, [], set(), D0 + timedelta(days=store.PRUNE_AFTER_DAYS + 1))
    assert db["jobs"] == []
