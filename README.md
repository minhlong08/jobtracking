# Intern Tracker

Every morning this checks the careers sites of 200 Australian tech employers (from
`AU_Tech_Intern_Companies_top200.xlsx`) for **intern, graduate and early-career tech roles in
Australia**. It emails you the roles that are new since yesterday and publishes a job board
listing everything found in the last 30 days.

```
GitHub Actions (daily, 6–7am Sydney)
  └─ scraper/  → fetch postings per company → filter (Australia + early career + tech)
               → data/jobs.json (diffed against yesterday) → email of new roles
  └─ site/     → static job board built from data/jobs.json → GitHub Pages
```

## How companies are scraped

`data/companies.yaml` says how to read each company's jobs (`ats.type`):

| Type | Source |
|---|---|
| `greenhouse`, `lever`, `ashby`, `smartrecruiters`, `workday`, `oracle_hcm` | The ATS's public JSON API. These are fast and reliable. |
| `amazon`, `atlassian` | Company-specific JSON endpoints |
| `llm` (and anything else) | Renders `search_url` (or `careers_url`) in headless Chromium. Claude (`claude-haiku-5-5`) then picks out the postings. Results are cached per page, so unchanged pages cost nothing. |
| `enabled: false` | Blocks scrapers or has moved. Listed under **Check manually** on the job board. |

`data/health.json` records each company's last run: postings found, matches, errors. It also
records `ats_hint` when a rendered page links to a known ATS. That is the cue to switch the
company to the API adapter for that ATS.

Filters live in `scraper/src/tracker/filters.py` and have table tests in
`scraper/tests/test_filters.py`. Add a test case first when tuning them.

## One-time setup

1. **Create a GitHub repo** and push this folder. GitHub Pages on a free account needs a public
   repo, so the job data will be public. It's all public postings anyway. Your Saved/Applied marks
   stay private in your browser.
2. **Enable Pages:** go to Settings → Pages → Source and choose **GitHub Actions**.
3. **Create a Resend API key.** Sign up at <https://resend.com> with the email address you want
   the daily digest sent to. Under API Keys, create one with **Sending access** only. The free tier
   is 100 emails a day. A Resend key can only send email and can't read any inbox. Without a
   verified domain, Resend only delivers to the address you signed up with, which is all this needs.
4. **Get an Anthropic API key** at <https://console.anthropic.com>. About 100 companies have no
   public API and are read by Claude. Expect a few cents a day.
5. **Add repo secrets** under Settings → Secrets and variables → Actions:

   | Secret | Value |
   |---|---|
   | `RESEND_API_KEY` | your Resend API key (`re_...`) |
   | `EMAIL_TO` | the address you signed up to Resend with |
   | `ANTHROPIC_API_KEY` | your Anthropic key |

6. **Run it once by hand:** go to Actions → *Daily intern scrape* → **Run workflow**. The board is
   then live at `https://<you>.github.io/<repo>/`.

The first run after adding the Anthropic key picks up the roles already open at the
Claude-scraped companies. Those go onto the board without being announced as "new", so the email
isn't flooded. The same happens whenever you start tracking a new company.

## Running locally

```bash
uv venv -p 3.12 .venv && VIRTUAL_ENV=.venv uv pip install -e 'scraper[dev]'
.venv/bin/playwright install chromium

.venv/bin/pytest scraper                                        # tests
.venv/bin/python -m tracker.run --dry-run --only canva,seek     # print matches, change nothing
.venv/bin/python -m tracker.run --no-email                      # update data/ without emailing

cd site && npm install && npm run dev                           # job board at localhost:5173
```

Set `ANTHROPIC_API_KEY` to include the Claude-scraped companies, and `RESEND_API_KEY` /
`EMAIL_TO` to send email locally. `TRACKER_DEBUG=1` prints full tracebacks.

## Adding or fixing a company

- Edit `data/companies.yaml`, or add a row to the spreadsheet and run
  `python scraper/scripts/import_xlsx.py`. Your manual edits are kept.
- `python scraper/scripts/discover_ats.py --only <id> [--browser]` tries to detect the ATS
  automatically.
- If a site only has a landing page, set `ats: {type: llm, search_url: <job search URL>}`. Use a
  search pre-filtered to Australia or graduates where the site allows it.
