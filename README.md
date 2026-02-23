# Airbnb End-to-End Automation — Django + Playwright

A full end-to-end browser automation project that walks through a real Airbnb user journey, persisting every step, screenshot, network request, and console log to a Django database, and exposing the results through a live dashboard.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration (.env)](#configuration-env)
6. [Database Setup](#database-setup)
7. [Running the Automation](#running-the-automation)
8. [Dashboard](#dashboard)
9. [Mobile Mode (Bonus)](#mobile-mode-bonus)
10. [Project Structure](#project-structure)
11. [Design Decisions](#design-decisions)

---

## Project Overview

The automation covers 6 journey steps on <https://www.airbnb.com/>:

| Step | Description |
|------|-------------|
| 01 | Landing page load, cache clear, random country selection & typing |
| 02 | Auto-suggestion verification, map icon check, DB storage, random click |
| 03 | Date-picker interaction: next-month navigation (3–8×), check-in/out selection |
| 04 | Guest picker: random 2–5 guests, verification, Search button click |
| 05 | Results page: URL validation, listing scraping (title / price / image) |
| 06 | Detail page: title, subtitle, gallery image collection |

Every step is stored as a `TestCase` in the database with status, message, screenshot path, and duration.  Network requests and console messages are also captured and stored per run.

---

## Architecture

```
airbnb_automation/
├── airbnb_automation/      # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── automation/             # Main Django app
│   ├── models.py           # TestRun, TestCase, AutoSuggestion, …
│   ├── admin.py            # Django admin registrations
│   ├── views.py            # Dashboard + Run Detail views
│   ├── urls.py
│   ├── management/
│   │   └── commands/
│   │       └── run_airbnb_journey.py   # Entry-point management command
│   └── utils/
│       ├── browser.py      # BrowserManager (Playwright wrapper)
│       ├── constants.py    # Countries list, viewports, etc.
│       ├── logger.py       # StepLogger with DB persistence
│       ├── screenshot.py   # Screenshot helper
│       └── steps.py        # AirbnbJourney (all 6 steps as methods)
├── templates/
│   ├── base.html
│   └── automation/
│       ├── dashboard.html
│       └── run_detail.html
├── screenshots/            # Auto-created; stores PNG screenshots
├── .env                    # ← You create this (see below)
├── .env.example
├── manage.py
└── requirements.txt
```

### Key classes

| Class | Location | Responsibility |
|-------|----------|----------------|
| `BrowserManager` | `utils/browser.py` | Playwright lifecycle, network/console listeners |
| `StepLogger` | `utils/logger.py` | Step context manager, stdout + DB logging |
| `AirbnbJourney` | `utils/steps.py` | All 6 journey step methods |
| `run_airbnb_journey` | `management/commands/` | Django management command entry point |

---

## Prerequisites

- Python 3.11+
- pip
- Google Chrome / Chromium (installed by Playwright)

---

## Installation

```bash
# 1. Clone / extract the project
cd airbnb_automation

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium
```

---

## Configuration (.env)

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | _(required)_ | Django secret key |
| `DEBUG` | `True` | Django debug mode |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated hosts |
| `SCREENSHOT_DIR` | `screenshots` | Folder for PNG screenshots |
| `HEADLESS` | `True` | Run browser headlessly |
| `SLOW_MO` | `100` | Playwright slow-mo delay (ms) |
| `MOBILE_MODE` | `False` | Default device mode |

> **All secrets live in `.env` — never commit it to version control.**

---

## Database Setup

```bash
python manage.py migrate
python manage.py createsuperuser   # optional, for admin UI
```

---

## Running the Automation

### Desktop (default)

```bash
python manage.py run_airbnb_journey
```

### Mobile (Bonus)

```bash
python manage.py run_airbnb_journey --mobile
```

### Headed (visible browser window)

```bash
python manage.py run_airbnb_journey --headless false
```

The command will print step-by-step progress to the terminal and store all results in the SQLite database.

---

## Dashboard

Start the development server:

```bash
python manage.py runserver
```

Then open:

| URL | Description |
|-----|-------------|
| `http://127.0.0.1:8000/` | Test runs dashboard |
| `http://127.0.0.1:8000/run/<id>/` | Detailed run view |
| `http://127.0.0.1:8000/admin/` | Django admin |

The dashboard displays:
- All test runs with status, country, dates, guests, and step counts
- Per-run view: step results with messages, auto-suggestions, listings, listing detail, console logs, and network logs

---

## Mobile Mode (Bonus)

When `--mobile` is passed, the automation uses an iPhone 13 device profile:

- Viewport: 390 × 844 px
- Touch enabled
- Mobile Safari user-agent
- Device pixel ratio: 3

The `is_mobile` flag is stored on the `TestRun` record and shown in the dashboard.

---

## Project Structure

### OOP Design

- **Single Responsibility**: `BrowserManager` owns browser lifecycle; `StepLogger` owns logging; `AirbnbJourney` owns domain logic.
- **DRY**: All selectors with fallback lists are centralised inside step methods; screenshot, logger, and DB helpers are reusable across steps.
- **Open/Closed**: New journey steps can be added as new methods in `AirbnbJourney` without modifying the command or logger.

### Database Models

| Model | Purpose |
|-------|---------|
| `TestRun` | One per automation execution |
| `TestCase` | One per step (6 total) |
| `AutoSuggestion` | All suggestion items captured in Step 02 |
| `SelectedDates` | Date picker result from Step 03 |
| `GuestSelection` | Guest counts from Step 04 |
| `SearchListing` | Each scraped listing from Step 05 |
| `ListingDetail` | Title, subtitle, gallery images from Step 06 |
| `NetworkLog` | Every HTTP response captured by Playwright listener |
| `ConsoleLog` | Every browser console message captured |

---

## Acceptance Criteria Checklist

- [x] Django framework
- [x] All secrets in `.env` (no hard-coding)
- [x] `README.md` with clear instructions
- [x] Management command (`run_airbnb_journey`)
- [x] Modular design — no duplicate code
- [x] OOP best practices
- [x] Each step treated as a test case
- [x] Every test case stored in DB with detailed message
- [x] Full-page screenshot per step
- [x] Screenshots in dedicated `screenshots/` folder
- [x] Console and Network logs stored in DB
- [x] **Bonus**: Mobile device mode via `--mobile` flag
