# Upwork Bot — Project Documentation

## What This Bot Does

This bot automates Upwork job discovery and proposal writing for a freelance presentation designer. It:

1. Opens Chrome 3 times a day and browses Upwork like a human
2. Searches for jobs matching configured keywords (Google Slides, PowerPoint, pitch decks)
3. Reads 4–5 job postings per session
4. Sends each job to DeepSeek AI to generate a personalized proposal
5. Writes the job details + proposal to a Google Sheet

**The bot never submits proposals. The freelancer reads the sheet and applies manually.**

---

## Freelancer Profile

- **Name**: Komal Khalid
- **Specialty**: PowerPoint, Keynote, Google Slides, pitch decks, business presentations
- **Experience**: 7+ years, 1500+ projects, Top Rated Plus on Upwork
- **Notable clients**: Sneak, Veeam, TraveliGo, Simpo, Vloggle

---

## Machine Setup

| Machine | Role |
|---|---|
| Mac 1 (development) | Code is written here, pushed to GitHub |
| Mac 2 (scraper) | Runs the bot — connected to phone hotspot |

**Mac 2 must use phone hotspot** (not home WiFi) to keep its IP separate from Mac 1 which has the real Upwork freelancer account. This protects the main account if the scraper account ever gets flagged.

Mac 2 uses a **new separate Upwork account** created specifically for scraping. If it gets banned, the main account is unaffected.

---

## Architecture Flow

```
[3x per day — randomized timing ±20 min]
        ↓
[Chrome opens — headed, real profile, not headless]
        ↓
[Navigates to Upwork homepage first — never directly to search URL]
        ↓
[Types search keyword slowly, character by character]
        ↓
[Scrolls through results naturally]
[Sometimes does idle scroll 30–90 sec (40% chance) to simulate reading]
        ↓
[Opens 4–5 job detail pages — 8–20 sec delay between each]
        ↓
[Extracts: title, URL, budget, duration, skills, client info, description]
        ↓
[Deduplicator checks SQLite DB — skips already-seen jobs]
        ↓
[DeepSeek API generates personalized proposal]
        ↓
[Google Sheets writer appends one row per new job]
        ↓
[Freelancer opens sheet on any device, reads proposals, applies manually]
```

---

## Project Structure

```
Upwork-bot/
├── config/
│   └── config.yaml              # All non-secret configuration
├── credentials/
│   └── credentials.json         # Google service account key (never on GitHub)
├── data/
│   └── seen_jobs.db             # SQLite dedup database (never on GitHub)
├── src/
│   ├── main.py                  # Entry point — runs pipeline and starts scheduler
│   ├── scheduler.py             # APScheduler — 3x daily with random offset
│   ├── config_loader.py         # Pydantic settings — loads config.yaml + .env
│   ├── deduplicator.py          # Tracks seen job IDs in SQLite
│   ├── proposal_generator.py    # DeepSeek API — generates proposals
│   ├── sheet_writer.py          # Google Sheets — appends rows
│   ├── fetcher/
│   │   ├── playwright_fetcher.py  # Core scraper — search + job detail pages
│   │   └── session_manager.py    # Chrome session, login, stealth setup
│   ├── models/
│   │   ├── job.py               # Job Pydantic model
│   │   └── proposal.py          # Proposal Pydantic model
│   └── utils/
│       ├── human_behavior.py    # Random delays, scrolling, typing helpers
│       └── logger.py            # structlog setup
├── .env                         # Secret keys — never on GitHub (create manually)
├── .env.example                 # Empty template — safe to push to GitHub
├── .gitignore                   # Excludes .env, credentials/, data/
└── requirements.txt             # All Python dependencies
```

---

## Configuration (`config/config.yaml`)

```yaml
search:
  queries: ["Google Slides", "Powerpoint Design", "pitch deck"]
  budget:
    min_fixed: 100      # Minimum fixed budget in USD
    min_hourly: 20      # Minimum hourly rate in USD
  experience_level: ["intermediate", "expert"]
  jobs_per_session: 5   # Max jobs to process per session (keep low — human-like)

freelancer:
  name: "Komal Khalid"
  bio: "..."            # Full bio sent to DeepSeek for proposal personalization
  skills: [...]         # List of skills
  portfolio_highlights: [...]
  tone: "professional"
  max_proposal_words: 300

google_sheets:
  spreadsheet_id: "1-dV0sI-51LA-Tr3ih7O8CizdUvt038qva-TR7k8BjcI"
  sheet_name: "Upwork Proposals"
  credentials_path: "credentials/credentials.json"

scheduler:
  sessions_per_day: 3
  run_times: ["09:00", "14:00", "20:00"]
  random_offset_minutes: 20   # Each session runs at time ± up to 20 min randomly

upwork:
  homepage: "https://www.upwork.com"
  min_delay_seconds: 5
  max_delay_seconds: 15
```

---

## Environment Variables (`.env` file — create manually on each machine)

```
DEEPSEEK_API_KEY=sk-...         # From platform.deepseek.com
UPWORK_EMAIL=newaccount@...     # The scraper Upwork account (NOT the main account)
UPWORK_PASSWORD=...
```

---

## Google Sheet Layout

| Col | Header | Content |
|---|---|---|
| A | Job ID | Upwork job UID (used for dedup) |
| B | Date Found | Timestamp when bot found the job |
| C | Title | Job title |
| D | URL | Direct link to job posting |
| E | Budget Type | Hourly / Fixed |
| F | Budget Amount | e.g. $50/hr or $500 |
| G | Duration | e.g. 1–3 months |
| H | Experience Level | Entry / Mid / Expert |
| I | Skills Required | Comma-separated |
| J | Client Location | Country |
| K | Client Rating | 0–5.0 |
| L | Client Hire Count | Number of past hires |
| M | Description Excerpt | First 500 chars of job description |
| N | Generated Proposal | DeepSeek-generated proposal text |
| O | Status | Freelancer fills this: New / Applied / Skipped |

---

## Tech Stack

| Concern | Tool |
|---|---|
| Browser automation | `playwright` (headed Chrome, not headless) |
| HTML parsing | `beautifulsoup4` + `lxml` |
| Proposal AI | `deepseek-chat` via `openai` SDK (DeepSeek is OpenAI-compatible) |
| Google Sheets | `google-api-python-client` |
| Scheduling | `APScheduler` |
| Config | `pydantic-settings` + PyYAML |
| Deduplication | `aiosqlite` (SQLite) |
| Retries | `tenacity` |
| Logging | `structlog` |

---

## Human Behavior Design

The bot is designed to avoid detection by mimicking human browsing patterns:

- **Never goes directly to a search URL** — always starts at the homepage
- **Types search keywords character by character** with random delays (50–150ms per char)
- **Random delays between actions**: 5–15 sec between page loads, 8–20 sec between jobs
- **Idle scrolling**: 40% chance of scrolling up/down for 30–90 seconds doing nothing
- **Random mouse movement** before interactions
- **Sessions run at randomized times** (scheduled time ± up to 20 min)
- **Only 4–5 jobs per session** — not greedy
- **3 sessions per day** — matches how a real freelancer checks Upwork

---

## Deduplication

Uses SQLite (`data/seen_jobs.db`) to track processed job IDs. On each run:
- Checks if `job_id` exists in DB before processing
- Marks job as seen after successfully writing to Google Sheet
- Stores the Google Sheet row number alongside the job ID

---

## Running the Bot

```bash
# Install dependencies (Mac 2 only)
pip install -r requirements.txt
playwright install chrome

# Create .env file with real keys
cp .env.example .env
nano .env

# Run
python src/main.py
```

The bot runs immediately on start, then again at each scheduled time.

---

## Important Notes

- **Upwork ToS**: Web scraping violates Upwork's Terms of Service. This bot uses a separate throwaway account on a separate machine with a separate IP to protect the main freelancer account.
- **No auto-apply**: The bot never submits proposals. It only reads and writes to Google Sheets.
- **Selectors may break**: Upwork's frontend (React) changes periodically. If scraping stops working, check `playwright_fetcher.py` — the CSS selectors in `_fetch_job_detail()` may need updating.
- **First run**: On first run, the bot will open Chrome and log into Upwork. It saves the session to `data/browser_state.json` so subsequent runs don't need to log in again.
- **Warm up the account**: Before running the bot on Mac 2, manually browse Upwork on that machine for a few days using the scraper account. This builds a legitimate-looking session history.
