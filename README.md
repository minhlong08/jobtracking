# Intern Tracker

[![Daily intern scrape](https://github.com/minhlong08/jobtracking/actions/workflows/daily.yml/badge.svg)](https://github.com/minhlong08/jobtracking/actions/workflows/daily.yml)

**Live job board:** <https://minhlong08.github.io/jobtracking/>

Intern Tracker finds **internship, graduate and early-career tech roles in Australia**. It checks
the careers sites of 200 major Australian tech employers every morning. It emails a digest of
roles posted since the previous day, and it publishes a searchable job board of everything found
in the last 30 days.

It runs entirely on GitHub's free tier, with GitHub Actions for the daily job and GitHub Pages for
the website. There are no servers or databases to maintain.

---

## Contents

- [Features](#features)
- [How it works](#how-it-works)
- [Repository structure](#repository-structure)
- [Setup guide](#setup-guide)
- [Using it day to day](#using-it-day-to-day)
- [Configuration](#configuration)
- [Local development](#local-development)
- [Maintaining company coverage](#maintaining-company-coverage)
- [Data model](#data-model)
- [Costs, limits and security](#costs-limits-and-security)
- [Troubleshooting](#troubleshooting)

---

## Features

- **Daily automated scan** of 200 employers across big tech, Australian scale-ups, banking,
  trading, consulting, defence, telco, government and more. The list comes from
  `AU_Tech_Intern_Companies_top200.xlsx`.
- **Targeted filtering.** It keeps only roles that are:
  - **in Australia**, and
  - **intern, graduate or early-career level**, and
  - **in tech**: software, data and analytics, ML/AI, infrastructure, cloud and security, or a
    general graduate program.
- **Daily email digest** of new roles, grouped by role type, each with a direct apply link.
- **Job board website** in the style of Seek or LinkedIn:
  - keyword and city search, with filters by role type, level and company;
  - **Apply** buttons that open the company's own posting;
  - **Saved** and **Applied** tracking, stored privately in your browser.
- **Reliable data sources.** It reads companies' applicant tracking systems (Workday,
  Greenhouse, Lever and others) through their public APIs instead of scraping fragile HTML.
- **Optional AI fallback.** For career sites with no API, it renders the page in a headless
  browser and uses Claude to extract the postings.
- **Self-reporting health.** Failing or blocked sites are flagged in the email and on the job
  board, so nothing silently drops out.

## How it works

```
                    ┌──────────── GitHub Actions, every day at ~6–7am Sydney ────────────┐
                    │                                                                     │
 data/companies.yaml│  1. Fetch postings     ATS JSON APIs ─┐                            │
 (200 employers)  ──┼─▶  for each company    Claude page    ├─▶ raw postings               │
                    │                         fallback ──────┘        │                     │
                    │  2. Filter             Australia + early career + tech               │
                    │                                                 │                     │
                    │  3. Compare            with data/jobs.json ──▶ new / still open /     │
                    │                                                 closed               │
                    │  4. Email              digest of today's new roles (Resend)          │
                    │  5. Commit             updated data/ back to the repo                │
                    │  6. Publish            build site/ ──▶ GitHub Pages                  │
                    └─────────────────────────────────────────────────────────────────────┘
```

**Company coverage** (each company's source is set in `data/companies.yaml`):

| Source | Companies | How it works |
|---|---|---|
| Public ATS APIs | 80 | Workday, Greenhouse, SmartRecruiters, Ashby, Oracle Recruiting, Lever, plus Amazon and Atlassian endpoints. Fast, structured, reliable. |
| Claude page fallback | 105 | Headless Chromium renders the careers page, then Claude (`claude-haiku-5-5`) extracts the postings. **Only active when an Anthropic API key is set.** Without one, these companies are listed on the board for manual checking. |
| Manual check | 15 | The site blocks automated access or has moved. Listed on the board with a link. |

**What counts as new.** A role is announced as new on the day it is first seen. Roles already
open when tracking starts, or when a company is first tracked, are added to the board quietly
instead of being announced, so the email is never flooded. A role is marked **closed** after it
has been missing for 3 successful checks in a row. Roles first seen more than 90 days ago are
removed from the data.

## Repository structure

```
├── .github/workflows/daily.yml   # Daily schedule: scrape → commit data → build → deploy
├── AU_Tech_Intern_Companies_top200.xlsx   # Source list of employers
├── data/
│   ├── companies.yaml            # One entry per employer and how to read its jobs (editable)
│   ├── jobs.json                 # Every matching role, with first/last seen dates (generated)
│   ├── health.json               # Per-company result of the latest run (generated)
│   └── llm_cache/                # Cached Claude extractions, keyed by page content (generated)
├── scraper/                      # Python package `tracker`
│   ├── src/tracker/
│   │   ├── run.py                # Entry point for the daily run
│   │   ├── adapters/             # One module per job source (workday.py, greenhouse.py, llm_page.py, …)
│   │   ├── filters.py            # Location, level and category rules
│   │   ├── store.py              # Merges results into jobs.json; new/closed logic
│   │   ├── emailer.py            # Renders and sends the digest via Resend
│   │   └── templates/email.html  # Email layout
│   ├── scripts/
│   │   ├── import_xlsx.py        # Spreadsheet → data/companies.yaml
│   │   └── discover_ats.py       # Detects which ATS each company uses
│   └── tests/                    # pytest suite (filters, store, emailer)
└── site/                         # Job board (Vite + React + TypeScript)
    └── src/App.tsx               # List/detail UI, filters, saved/applied tracking
```

---

## Setup guide

These steps set up your own copy from scratch. Allow about 15 minutes.

### Prerequisites

- A GitHub account.
- An email address to receive the daily digest.
- *Optional:* an Anthropic account, to cover the 105 career sites that need the AI fallback.

### Step 1: Get the code into your GitHub account

Fork this repository, or create a new **public** repository and push this code to it.

> GitHub Pages on a free account requires a public repository. The job data is made up of public
> job postings, so nothing sensitive is exposed. Your Saved/Applied marks never leave your browser.

### Step 2: Turn on GitHub Pages

1. In your repository, open **Settings → Pages**.
2. Under **Build and deployment → Source**, choose **GitHub Actions**.

### Step 3: Create a Resend account for email

The digest is sent through [Resend](https://resend.com), an email-sending service. A Resend API
key can only send email; it cannot read any inbox. That makes it much safer than storing a Gmail
password.

1. Sign up at <https://resend.com> **using the email address you want the digest sent to**.
2. Go to **API Keys → Create API Key**.
3. Name it `jobtracking` and set **Permission** to **Sending access**.
4. Copy the key, which starts with `re_`. It is only shown once.

> Without a verified domain, Resend only delivers to the address you signed up with. That is all
> this project needs. The free tier allows 100 emails a day.

### Step 4 (optional): Create an Anthropic API key

Skip this step to start with the 80 API-based companies. You can add the key at any time.

1. Sign up at <https://console.anthropic.com>. This is separate from a Claude.ai chat
   subscription.
2. Add prepaid credit under **Settings → Billing**. The minimum is $5.
3. Optionally, set a monthly spend limit under **Settings → Limits**.
4. Create a key under **Settings → API Keys** and copy it. It starts with `sk-ant-`.

### Step 5: Add the secrets to GitHub

Secrets are stored encrypted by GitHub and are never visible in the code or the logs.

1. Open **Settings → Secrets and variables → Actions → New repository secret**.
2. Add each of these:

   | Name | Value | Required |
   |---|---|---|
   | `RESEND_API_KEY` | Your Resend key (`re_…`) | Yes |
   | `EMAIL_TO` | The **same** address you signed up to Resend with | Yes |
   | `ANTHROPIC_API_KEY` | Your Anthropic key (`sk-ant-…`) | Optional |

If you use the GitHub CLI, you can set them from a terminal instead. Each command prompts for the
value:

```bash
gh secret set RESEND_API_KEY -R <your-user>/<your-repo>
gh secret set EMAIL_TO -R <your-user>/<your-repo>
gh secret set ANTHROPIC_API_KEY -R <your-user>/<your-repo>   # optional
```

### Step 6: Run it for the first time

1. Open the **Actions** tab and select **Daily intern scrape**.
2. Click **Run workflow → Run workflow**.
3. Wait for both jobs, **scrape** and **deploy**, to show a green tick. This takes 2–3 minutes.

### Step 7: Check that it worked

- **Website:** open `https://<your-user>.github.io/<your-repo>/`.
- **Email:** look for a message from `onboarding@resend.dev`. Check spam the first time and mark
  it *Not spam*.
- **Health:** open `data/health.json` in the repo to see each company's result.

That's it. From now on the workflow runs automatically every morning.

---

## Using it day to day

### The daily email

- Lists only roles **first found since the previous run**, grouped by role type.
- Each role has an **Apply** button linking to the company's posting.
- On quiet days you receive a short "No new intern/grad roles today" message, which confirms the
  check ran.
- The footer lists companies whose check failed, so you can visit those sites yourself.

### The job board

| Feature | How to use it |
|---|---|
| **Search** | Type a keyword (title, company or location) and optionally choose a city. |
| **Filters** | Toggle role types and levels. Pick a company, choose how recently roles were found, and sort by newest or by company. On mobile, tap **Filters**. |
| **Role details** | Click a role to see its location, level, industry and posting dates. |
| **Apply** | **Apply on company site** opens the official posting in a new tab. Afterwards, the board asks whether you finished applying. |
| **Save** | Bookmark a role. It appears under the **Saved** tab. |
| **Mark as applied** | Records the date you applied. It appears under the **Applied** tab. Use **Hide applied** to declutter the main list. |
| **Check manually** | Companies that can't be checked automatically, each with a link to its careers page. |
| **New badge** | Roles first found in the last day are tagged **New**. The header shows today's count. |

> Saved and Applied are stored in your browser's local storage. They are private to that browser
> and device. Clearing site data removes them.

---

## Configuration

### Change the schedule

Edit the cron line in `.github/workflows/daily.yml`. Times are in UTC:

```yaml
schedule:
  - cron: "0 20 * * *"   # 20:00 UTC = 6am AEST / 7am AEDT
```

### Environment variables

| Variable | Used for | Default |
|---|---|---|
| `RESEND_API_KEY` | Sending the email. If unset, the email is skipped. | none |
| `EMAIL_TO` | Digest recipient. | none |
| `EMAIL_FROM` | Sender address. Only change this after verifying a domain in Resend. | `Intern Tracker <onboarding@resend.dev>` |
| `ANTHROPIC_API_KEY` | Enables the Claude page fallback. If unset, those companies are skipped. | none |
| `LLM_MODEL` | Model used by the fallback. | `claude-haiku-5-5` |
| `SITE_URL` | Job board link in the email. The workflow sets this automatically. | none |
| `TRACKER_DEBUG` | Set to `1` to print full error tracebacks. | off |

### Tune what counts as a match

The rules live in `scraper/src/tracker/filters.py`, as regular expressions for Australian
locations, seniority levels, tech categories and non-tech exclusions.
`scraper/tests/test_filters.py` holds a table of real job titles and their expected results. When
changing a rule, add the title that prompted the change to that table first. Then run the tests
to confirm nothing else broke.

---

## Local development

Requirements: Python 3.12+, Node 20+, and optionally [uv](https://github.com/astral-sh/uv).

```bash
# 1. Install the scraper and the headless browser
uv venv -p 3.12 .venv
VIRTUAL_ENV=.venv uv pip install -e 'scraper[dev]'
.venv/bin/playwright install chromium

# 2. Run the tests
.venv/bin/pytest scraper

# 3. Try the scraper without changing anything
.venv/bin/python -m tracker.run --dry-run --only canva,seek,amazon-aws

# 4. Run the website
cd site
npm install
npm run dev        # http://localhost:5173
```

`tracker.run` options:

| Flag | Effect |
|---|---|
| `--dry-run` | Print matching roles. Writes no files and sends no email. |
| `--only id1,id2` | Check only these company ids (from `data/companies.yaml`). |
| `--no-email` | Update `data/` but don't send the email. |
| `--concurrency N` | Number of companies checked in parallel. Default 8. |

To send a test email locally, export `RESEND_API_KEY` and `EMAIL_TO` before running without
`--dry-run` or `--no-email`.

---

## Maintaining company coverage

### Check how each company is doing

`data/health.json` is updated on every run. For each company it shows:

- `status`: `ok`, `error` or `skipped`;
- `raw` and `matched`: postings found, and how many passed the filters;
- `error`: what went wrong, if anything;
- `ats_hint`: an applicant tracking system spotted on a rendered page. This is a cue that the
  company can be switched to a faster, more reliable API adapter.

### Add a company

1. Add a row to `AU_Tech_Intern_Companies_top200.xlsx`.
2. Run `python scraper/scripts/import_xlsx.py`. Existing manual edits in `companies.yaml` are
   preserved.
3. Run `python scraper/scripts/discover_ats.py --only <company-id>` to detect its ATS. Add
   `--browser` for JavaScript-heavy sites.
4. Check it with `python -m tracker.run --dry-run --only <company-id>`.

### Fix or redirect a company

Edit its entry in `data/companies.yaml`:

```yaml
- id: example-co
  name: Example Co
  sector: Australian Software / Scale-ups
  careers_url: https://example.com/careers
  ats: {type: workday, tenant: example, wd: wd3, site: External}   # API adapter
  # ats: {type: greenhouse, slug: exampleco}
  # ats: {type: llm, search_url: https://example.com/jobs?location=Australia}   # page fallback
  # enabled: false                                                  # list for manual checking
  # manual_reason: Blocks automated checks
```

Supported `ats.type` values are `workday`, `greenhouse`, `lever`, `ashby`, `smartrecruiters`,
`oracle_hcm`, `amazon`, `atlassian` and `llm`. Any other type uses the page fallback. For `llm`,
point `search_url` at a job search page, ideally pre-filtered to Australia or graduates.

---

## Data model

Each role in `data/jobs.json`:

| Field | Meaning |
|---|---|
| `id` | Stable hash of company and posting id |
| `company`, `sector` | Employer and industry |
| `title`, `url`, `location` | The posting, with a direct link to apply |
| `level` | `Intern`, `Graduate` or `Early career` |
| `category` | `Software`, `Data & Analytics`, `ML/AI`, `Infra/Cloud/Security`, `Other tech` or `General program` |
| `posted_at` | Date posted, when the source provides it |
| `first_seen`, `last_seen` | When the tracker first and most recently found it |
| `closed` | `true` once missing for 3 consecutive successful checks |
| `initial` | `true` if it was already open when tracking began, so it was not announced as new |

---

## Costs, limits and security

- **GitHub Actions and Pages:** free for public repositories. A daily run takes 2–3 minutes.
- **Resend:** free tier of 100 emails a day. This project sends one.
- **Anthropic (optional):** the fallback uses Claude Haiku 5.5. Unchanged pages are served from
  `data/llm_cache/` and cost nothing, so typical use is a few cents a day, at most about
  US$0.15 a day.
- **Secrets** live only in GitHub's encrypted secret store and are masked in logs. The Resend key
  can send but not read email. Error messages are scrubbed of email addresses before they reach
  the public workflow logs.
- **Scraping etiquette:** each company is fetched once a day, a limited number of companies are
  fetched at a time, and sites that block automated access are respected rather than worked
  around.

---

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Workflow fails with `Resend rejected the email (403)` | `EMAIL_TO` doesn't match your Resend sign-up address. Update the secret, or verify a domain in Resend and set `EMAIL_FROM`. |
| No email, but the workflow succeeded | Check your spam folder, and look for `email sent` in the workflow log. If the log says `email skipped`, `RESEND_API_KEY` is not set. |
| Website shows 404 | Make sure Pages' source is **GitHub Actions** (Step 2) and that the **deploy** job succeeded. |
| Website says "Couldn't load roles" | The site was deployed without data. Re-run the workflow. |
| A company shows `error` in `health.json` | The site may have changed or started blocking bots. Re-run discovery for it, point it at a different URL, or set `enabled: false`. |
| A role is missing or misclassified | Add the title to `scraper/tests/test_filters.py`, adjust `filters.py`, and run the tests. |
| 105 companies listed as "Not tracked yet" | Expected without `ANTHROPIC_API_KEY`. Add the key (Steps 4–5) to enable them. |

---

## Tech stack

**Scraper:** Python 3.12, httpx, Playwright (Chromium), Pydantic, Jinja2, Anthropic Python SDK,
pytest.
**Website:** React 18, TypeScript, Vite.
**Infrastructure:** GitHub Actions, GitHub Pages, Resend.
