# Airbnb End-to-End Automation

An automated end-to-end user journey testing project built with **Python**, **Django**, and **Playwright**. This project simulates a real user browsing Airbnb — from landing on the homepage to viewing a listing's detail page — and stores every test result, scraped data, network log, and console log into a database (default: **SQLite**).


## Project Overview

**Target Site:** https://www.airbnb.com/

This project automates the following real user journey on Airbnb:

1. Open Airbnb homepage and clear browser data
2. Search for a randomly selected country from the top 20 countries
3. Verify auto-suggestions appear and select one
4. Interact with the date picker (navigate months, select check-in & check-out)
5. Select random number of guests
6. Verify search results page and scrape all listing data
7. Open a random listing's detail page and capture title, subtitle, and gallery images

Every step is treated as a **test case** and stored in the database with pass/fail status and detailed comments.

---

## 🛠 Tech Stack

| Technology | Purpose |
|---|---|
| Python 3.10+ | Core programming language |
| Django 4.2 | Web framework & ORM |
| Playwright | Browser automation |
| SQLite | Default local database |
| PostgreSQL | Optional external database |
| psycopg2 | PostgreSQL adapter (optional) |
| python-dotenv | Environment variable management |
| Django Admin | Built-in dashboard to view results |

---

## Project Structure

```
airbnb_automation/
│
├── airbnb_automation/              # Django project configuration
│   ├── __init__.py
│   ├── settings.py                 # All settings (DB, installed apps, etc.)
│   ├── urls.py                     # URL routing (admin panel)
│   └── wsgi.py
│
├── automation/                     # Main Django app
│   ├── admin.py                    # Django Admin registration for all models
│   ├── apps.py
│   ├── models.py                   # All database models
│   │
│   ├── services/                   # Core reusable services
│   │   ├── browser_service.py      # Playwright browser/page management
│   │   └── database_service.py     # All database write operations
│   │
│   ├── steps/                      # Each automation step as a separate class
│   │   ├── step01_landing.py       # Homepage load + search input
│   │   ├── step02_suggestion.py    # Auto-suggestion verification
│   │   ├── step03_datepicker.py    # Date picker interaction
│   │   ├── step04_guestpicker.py   # Guest selection
│   │   ├── step05_results.py       # Search results scraping
│   │   └── step06_details.py       # Listing details page
│   │
│   ├── management/
│   │   └── commands/
│   │       └── run_airbnb_automation.py   # Django management command (entry point)
│   │
│   └── migrations/                 # Database migrations
│       └── 0001_initial.py
│
├── screenshots/                    # Auto-created; stores step-by-step screenshots
├── .env                            # Environment variables (DO NOT commit to git)
├── requirements.txt                # Python dependencies
├── manage.py                       # Django CLI entry point
└── README.md                       # This file
```

---

## Prerequisites

Before running this project, make sure you have the following installed:

| Requirement | Version | Check Command |
|---|---|---|
| Python | 3.10 or higher | `python3 --version` |
| Chromium (installed via Playwright) | Latest | `playwright install chromium` |
| Docker | Any recent version | `docker --version` |
| Git | Any version | `git --version` |

> **Note:** Playwright needs a one-time browser install: `playwright install chromium`.

---

## Installation & Setup

### Step 1 — Clone the Repository

```bash
git clone <your-repository-url>
cd airbnb_automation
```

> If you received this as a ZIP file, extract it and navigate into the inner `airbnb_automation` folder (the one that contains `manage.py`):
> ```bash
> cd airbnb_automation
> ls   # You should see: manage.py, requirements.txt, .env, automation/, airbnb_automation/
> ```

---

### Step 2 — Create a Virtual Environment

```bash
python3 -m venv venv
```

---

### Step 3 — Activate the Virtual Environment

**On Linux / macOS:**
```bash
source venv/bin/activate
```

**On Windows:**
```bash
venv\Scripts\activate
```

> After activation, your terminal prompt will show `(venv)` at the beginning.

> **Important:** Every time you open a new terminal session, you must activate the venv again before running any commands.

---

### Step 4 — Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- Django 4.2
- Playwright
- psycopg2-binary (PostgreSQL driver)
- python-dotenv
- Pillow
- requests

Then install browser binaries:
```bash
playwright install chromium
```

---

## Environment Configuration

The project can run with SQLite by default (no `.env` required).
If you want PostgreSQL, create a `.env` file and set DB variables.

PostgreSQL `.env` example:

```env
# Database Configuration (optional)
DB_ENGINE=postgres
DB_NAME=mydb
DB_USER=ali
DB_PASSWORD=1234
DB_HOST=localhost
DB_PORT=5432

# Airbnb Target URL
AIRBNB_URL=https://www.airbnb.com/

# Screenshots folder name
SCREENSHOT_DIR=screenshots
```

> Never hardcode credentials directly in the code. Always use `.env`.

---

## Database Setup

Default: SQLite (`db.sqlite3`)  
No extra setup needed, just run:

```bash
python manage.py migrate
```

Optional: PostgreSQL (Docker)  
Set `DB_ENGINE=postgres` and DB credentials in `.env`, then follow the PostgreSQL steps below.

### Step 1 — Start Your Docker PostgreSQL Container

```bash
docker start <your-container-name>
```

To check if your container is running:
```bash
docker ps
```

You should see your PostgreSQL container listed. The connection used by this project:
```
postgres://ali:1234@localhost:5432/mydb
```

### Step 2 — Run Django Migrations

This will automatically create all required tables in your database:

```bash
python manage.py migrate
```

Expected output:
```
Operations to perform:
  Apply all migrations: admin, auth, automation, contenttypes, sessions
Running migrations:
  Applying automation.0001_initial... OK
  ...
```

### Step 3 — (Optional) Create Django Admin Superuser

To access the Django Admin dashboard:

```bash
python manage.py createsuperuser
```

Enter your preferred username, email, and password when prompted.

---

## Running the Automation

### Normal Run (Visible Browser — Default)

```bash
python manage.py run_airbnb_automation
```

The browser will open visibly and you can watch the automation run in real time.

---

### Run in Headless Mode (No Browser Window)

```bash
python manage.py run_airbnb_automation --headless
```

Useful for running on a server or in the background.

---

### Run in Mobile Device Mode (Bonus Feature)

```bash
python manage.py run_airbnb_automation --mobile
```

Emulates an **iPhone 14 Pro** (390×844 resolution, pixel ratio 3.0) with a mobile user agent.

---

### Example Full Output

```
============================================================
  Airbnb End-to-End Automation Starting
  Mode: Desktop | Browser: Visible
============================================================

[Step 01] Website Landing and Initial Search Setup
  ✓ Country selected: United Kingdom

[Step 02] Search Auto-suggestion Verification
  ✓ Suggestion selected

[Step 03] Date Picker Interaction
  ✓ Dates: check-in=2026-06-15 | check-out=2026-06-22

[Step 04] Guest Picker Interaction
  ✓ Guests added: 3

[Step 05] Refine Search and Item List Verification
  ✓ Listings scraped: 18

[Step 06] Item Details Page Verification
  ✓ Details captured: Queen Room in Victorian Home and Garden

============================================================
  AUTOMATION COMPLETE
  Total Test Cases : 22
  Passed           : 20
  Failed           : 2
============================================================
```

---

## Django Admin Panel

After running migrations and creating a superuser, start the Django development server:

```bash
python manage.py runserver
```

Then open your browser and go to:
```
http://127.0.0.1:8000/admin/
```

Log in with your superuser credentials. You will see all data collected during the automation run:

| Section | What You Can See |
|---|---|
| **Test Results** | All test cases with pass/fail status and comments |
| **Listings** | Scraped listing titles, prices, and image URLs |
| **Suggestions** | Auto-suggestion items captured per search query |
| **Network Logs** | HTTP network requests captured during automation |
| **Console Logs** | Browser console messages (errors, warnings, info) |

---

## Database Tables

The following tables are created automatically by Django migrations:

---

### 1. `testing` — Main Test Results Table

This is the primary table required by the assignment.

| Column | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment primary key |
| `test_case` | VARCHAR(255) | Name/label of the test step |
| `url` | VARCHAR(2048) | Page URL at time of test |
| `passed` | Boolean | `true` = passed, `false` = failed |
| `comment` | Text | Format: `"should be <expected>, found <actual>"` |

**Example Data:**

| id | test_case | url | passed | comment |
|---|---|---|---|---|
| 1 | Homepage Load Verification | https://www.airbnb.com/ | true | should be airbnb.com homepage to load, found URL is https://www.airbnb.com/ |
| 2 | Auto-suggestion List Visibility | https://www.airbnb.com/ | true | should be dropdown to appear after typing, found Suggestion list visible |
| 3 | Date Picker Modal Open and Visibility Test | https://www.airbnb.com/ | true | should be date picker visible with Feb and Mar months, found Date picker modal is visible |
| 4 | Search Results Page Load Verification | https://www.airbnb.com/s/... | true | should be results page to load with listings, found Results page loaded with listings |

---

### 2. `listing_data` — Scraped Listings

| Column | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment primary key |
| `title` | VARCHAR(512) | Listing title |
| `price` | VARCHAR(100) | Price per night or total |
| `image_url` | VARCHAR(2048) | Thumbnail image URL |
| `listing_url` | VARCHAR(2048) | Full URL to the listing |
| `scraped_at` | DateTime | Timestamp of when data was scraped |

---

### 3. `suggestion_data` — Auto-Suggestions

| Column | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment primary key |
| `text` | VARCHAR(512) | Suggestion text shown in dropdown |
| `search_query` | VARCHAR(255) | The search term that triggered it |
| `captured_at` | DateTime | Timestamp |

---

### 4. `network_logs` — Network Request Logs

| Column | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment primary key |
| `url` | VARCHAR(2048) | Request URL |
| `method` | VARCHAR(10) | HTTP method (GET, POST, etc.) |
| `status_code` | Integer | HTTP response status code |
| `resource_type` | VARCHAR(50) | Type (XHR, Document, Image, etc.) |
| `captured_at` | DateTime | Timestamp |

---

### 5. `console_logs` — Browser Console Logs

| Column | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment primary key |
| `level` | VARCHAR(20) | INFO / WARNING / ERROR / DEBUG |
| `message` | Text | Console message content |
| `source` | VARCHAR(512) | Source file/URL of the message |
| `captured_at` | DateTime | Timestamp |

---

## Automation Steps

| Step | Class | File | What It Does |
|---|---|---|---|
| 01 | `Step01LandingAndSearch` | `step01_landing.py` | Opens Airbnb, clears cache, dismisses popups, types a random country |
| 02 | `Step02AutoSuggestion` | `step02_suggestion.py` | Verifies dropdown, checks relevance & icons, stores suggestions, clicks one |
| 03 | `Step03DatePicker` | `step03_datepicker.py` | Opens date picker, navigates 3–8 months forward, selects check-in & check-out |
| 04 | `Step04GuestPicker` | `step04_guestpicker.py` | Opens guest popup, adds 2–5 guests randomly, clicks Search |
| 05 | `Step05SearchResults` | `step05_results.py` | Verifies URL params, scrapes listing title/price/image, stores in DB |
| 06 | `Step06ListingDetails` | `step06_details.py` | Opens a random listing, captures h1 title, h2 subtitle, all gallery images |

---

## Screenshots

Screenshots are automatically saved in the `screenshots/` folder after each important step.

```
screenshots/
├── step01_homepage_20260223_093900.png
├── step01_search_typed_20260223_093912.png

```



## Author

**Project:** Airbnb End-to-End Automation Assignment  
**Framework:** Django + Playwright  
**Database:** PostgreSQL (Docker)  
**Target Site:** https://www.airbnb.com/
