import random
from playwright.sync_api import sync_playwright
from .models import Log, Listing

COUNTRIES = [
    "USA","France","Italy","Spain","Japan","Thailand",
    "Canada","Australia","Germany","UK",
    "Brazil","Mexico","Indonesia","Turkey","India",
    "China","Portugal","Greece","Netherlands","UAE"
]

def log(step, action, result):
    Log.objects.create(step=step, action=action, result=result)

def run_scraper():

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # STEP 1
        page.goto("https://www.airbnb.com/")
        log("Step01","Open homepage","Success")

        country = random.choice(COUNTRIES)

        page.locator('input[placeholder*="Where"]').click()
        page.keyboard.type(country, delay=100)

        log("Step01","Typed country",country)

        page.keyboard.press("Enter")

        # STEP 3 Dates
        page.wait_for_timeout(2000)

        for _ in range(random.randint(3,8)):
            try:
                page.locator('[aria-label="Next month"]').click()
            except:
                pass

        days = page.locator('[data-testid="calendar-day"]').all()

        if len(days) > 10:
            days[5].click()
            days[8].click()

        log("Step03","Dates selected","OK")

        # Guests
        try:
            page.locator('button:has-text("Guests")').click()

            for _ in range(random.randint(2,5)):
                page.locator('[aria-label="increase value"]').first.click()

        except:
            pass

        page.keyboard.press("Enter")

        # Results
        page.wait_for_load_state("networkidle")

        items = page.locator('[itemprop="itemListElement"]').all()

        for item in items[:10]:
            title = item.text_content()
            Listing.objects.create(title=title or "")

        log("Step05","Listings saved","Done")

        browser.close()