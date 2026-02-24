# Airbnb Automation (Django + Playwright)

End-to-end Airbnb journey automation built with Python, Django, and Playwright.

The project runs a 6-step browser flow and can optionally persist test results, suggestions, listings, network logs, and console logs to the database.

## What it automates

1. Open Airbnb homepage and select a destination
2. Verify/select auto-suggestion
3. Open date picker and choose check-in/check-out
4. Open guest picker and add guests
5. Open results page and scrape listing cards
6. Open a listing details page and collect title/subtitle/images

## Tech stack

- Python 3.10+
- Django 4.2
- Playwright (Chromium)
- SQLite (default)

## Project structure

```text
.
├── airbnb_automation/                  # Django project settings/urls
├── automation/
│   ├── management/commands/
│   │   └── run_airbnb_automation.py   # Main entry command
│   ├── services/                       # Browser + DB services
│   ├── steps/                          # Step01 ... Step06 implementations
│   ├── models.py                       # Test/log/listing DB models
│   └── admin.py                        # Django admin registrations
├── screenshots/                        # Run screenshots (auto-created)
├── airbnb_recorded.py                  # Standalone Playwright recorded script
├── requirements.txt
└── manage.py
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python manage.py migrate
```

## Configuration

Settings are loaded from environment variables (`python-dotenv` supported).

Default behavior:
- Database: SQLite (`db.sqlite3`)
- Airbnb URL: `https://www.airbnb.com/`
- Screenshots directory: `screenshots`

Common environment variables:






## Run automation

Main command:

```bash
python manage.py run_airbnb_automation
```

Important default:
- DB writes are disabled unless you pass `--store-db`.

### Useful command examples

```bash
# Full flow (desktop, visible browser)
python manage.py run_airbnb_automation

# Full flow + persist to DB
python manage.py run_airbnb_automation --store-db

# Headless run
python manage.py run_airbnb_automation --headless

# Mobile emulation
python manage.py run_airbnb_automation --mobile

# Run only one step (1-6)
python manage.py run_airbnb_automation --step 3

# Deterministic one-direction flow
python manage.py run_airbnb_automation --deterministic

# Disable screenshots
python manage.py run_airbnb_automation --no-screenshots

# Keep browser open at end
python manage.py run_airbnb_automation --keep-browser-open
```

## Django admin

To inspect persisted results:

```bash
python manage.py createsuperuser
python manage.py runserver
```

Open: `http://127.0.0.1:8000/admin/`

Available admin models:
- `TestResult`
- `SuggestionData`
- `ListingData`
- `NetworkLog`
- `ConsoleLog`

## Notes

- Airbnb UI/locators can change; selectors are implemented with fallbacks but may need updates over time.
- If you do not use `--store-db`, automation still runs and takes screenshots, but DB counters in summary are `N/A`.
- `airbnb_recorded.py` is a minimal standalone Playwright script and is separate from the Django command flow.
