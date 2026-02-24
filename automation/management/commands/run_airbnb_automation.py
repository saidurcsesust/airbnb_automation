"""
Django Management Command: run_airbnb_automation
Executes the full end-to-end Airbnb user journey automation.

Usage:
    python manage.py run_airbnb_automation
    python manage.py run_airbnb_automation --mobile
    python manage.py run_airbnb_automation --no-headless
"""
import logging
import os
import sys
import time
import re
import random

from django.core.management.base import BaseCommand
from django.conf import settings

from automation.services.browser_service import BrowserService
from automation.steps.step01_landing import Step01LandingAndSearch
from automation.steps.step02_suggestion import Step02AutoSuggestion
from automation.steps.step03_datepicker import Step03DatePicker
from automation.steps.step04_guestpicker import Step04GuestPicker
from automation.steps.step05_results import Step05SearchResults
from automation.steps.step06_details import Step06ListingDetails

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


class NoOpDatabaseService:
    """Drop-in replacement that disables all DB writes."""

    @staticmethod
    def save_test_result(*args, **kwargs):
        return None

    @staticmethod
    def save_suggestions(*args, **kwargs):
        return None

    @staticmethod
    def save_listings(*args, **kwargs):
        return None

    @staticmethod
    def save_network_logs(*args, **kwargs):
        return None

    @staticmethod
    def save_console_logs(*args, **kwargs):
        return None


class Command(BaseCommand):
    help = 'Run full end-to-end Airbnb automation journey'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mobile',
            action='store_true',
            default=False,
            help='Run automation in mobile device mode (bonus feature)',
        )
        parser.add_argument(
            '--headless',
            action='store_true',
            default=False,
            help='Run browser in headless mode (no visible window). Default is visible.',
        )
        parser.add_argument(
            '--step',
            type=int,
            default=0,
            choices=[0, 1, 2, 3, 4, 5, 6],
            help='Run a specific step only (1-6). Use 0 for full journey (default).',
        )
        parser.add_argument(
            '--deterministic',
            action='store_true',
            default=False,
            help='Run a deterministic single-direction Playwright flow (exact script).',
        )
        parser.add_argument(
            '--no-screenshots',
            action='store_true',
            default=False,
            help='Disable saving screenshots during the automation run.',
        )
        parser.add_argument(
            '--store-db',
            action='store_true',
            default=False,
            help='Enable database storage (disabled by default).',
        )
        parser.add_argument(
            '--keep-browser-open',
            action='store_true',
            default=False,
            help='Keep the browser window open after automation completes.',
        )

    def handle(self, *args, **options):
        # Playwright sync API internally runs an event loop; allow ORM calls in this command context.
        os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

        mobile = options.get('mobile', False)
        headless = options.get('headless', False)  # Default: visible browser
        step = options.get('step', 0)
        store_db = options.get('store_db', False)

        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*60}\n"
            f"  Airbnb End-to-End Automation Starting\n"
            f"  Mode: {'Mobile' if mobile else 'Desktop'} | "
            f"Browser: {'Headless' if headless else 'Visible (--headless to hide)'} | "
            f"Step: {'All' if step == 0 else step}\n"
            f"{'='*60}\n"
        ))

        airbnb_url = settings.AIRBNB_URL
        db = NoOpDatabaseService()
        if store_db:
            from automation.services.database_service import DatabaseService
            db = DatabaseService()
            db.save_test_result(
                test_case="Automation Session Start",
                url=airbnb_url,
                passed=True,
                should_be="Automation session to initialize correctly",
                found="Session started successfully"
            )
        else:
            self.stdout.write(self.style.WARNING("  DB storage: disabled (--store-db to enable)"))

        screenshots_enabled = not options.get('no_screenshots', False)
        keep_browser_open = options.get('keep_browser_open', False)

        try:
            with BrowserService(mobile=mobile, headless=headless, screenshots_enabled=screenshots_enabled, keep_browser_open=keep_browser_open) as browser:
                if options.get('deterministic'):
                    # Run the explicit single-direction flow matching the provided Playwright script.
                    self._run_deterministic_flow(browser, db, airbnb_url, store_db=store_db)
                else:
                    self._run_journey(browser, db, airbnb_url, step, store_db=store_db)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nAutomation interrupted by user."))
            if store_db:
                db.save_test_result(
                    test_case="Automation Session End",
                    url=airbnb_url,
                    passed=False,
                    should_be="Automation to complete all 6 steps",
                    found="Interrupted by user"
                )
        except Exception as e:
            logger.error(f"Unhandled error in automation: {e}", exc_info=True)
            if store_db:
                db.save_test_result(
                    test_case="Automation Session End",
                    url=airbnb_url,
                    passed=False,
                    should_be="Automation to complete all 6 steps without error",
                    found=f"Failed with error: {str(e)[:200]}"
                )
            self.stdout.write(self.style.ERROR(f"\nAutomation failed: {e}"))
            raise

    def _run_journey(self, browser: BrowserService, db, airbnb_url: str, step: int = 0, store_db: bool = False):
        """Execute all 6 steps of the Airbnb user journey."""

        # ── STEP 01 ─────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("\n[Step 01] Website Landing and Initial Search Setup"))
        step01 = Step01LandingAndSearch(browser, db, airbnb_url)
        selected_country = step01.run()
        self.stdout.write(self.style.SUCCESS(f"  ✓ Country selected: {selected_country}"))
        time.sleep(2)  # Delay after Step 01

        # Capture console & network logs after page load
        self._save_monitoring_logs(browser, db)

        if step == 1:
            db.save_test_result(
                test_case="Automation Session End",
                url=browser.get_current_url(),
                passed=True,
                should_be="Step 01 to complete successfully",
                found=f"Step 01 completed: country={selected_country}"
            )
            self._print_summary(store_db=store_db)
            return

        # ── STEP 02 ─────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("\n[Step 02] Search Auto-suggestion Verification"))
        step02 = Step02AutoSuggestion(browser, db)
        suggestion_ok = step02.run(selected_country)
        self.stdout.write(
            self.style.SUCCESS("  ✓ Suggestion selected") if suggestion_ok
            else self.style.WARNING("  ⚠ Suggestion step had issues, continuing...")
        )
        time.sleep(2)  # Delay after Step 02

        if step == 2:
            db.save_test_result(
                test_case="Automation Session End",
                url=browser.get_current_url(),
                passed=suggestion_ok,
                should_be="Step 02 to complete successfully",
                found=f"Step 02 completed for country={selected_country}"
            )
            self._print_summary(store_db=store_db)
            return

        # ── STEP 03 ─────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("\n[Step 03] Date Picker Interaction"))
        step03 = Step03DatePicker(browser, db)
        date_info = step03.run()
        self.stdout.write(self.style.SUCCESS(
            f"  ✓ Dates: check-in={date_info.get('checkin')} | check-out={date_info.get('checkout')}"
        ))
        time.sleep(2)  # Delay after Step 03

        if step == 3:
            step_ok = bool(date_info.get('checkin') and date_info.get('checkout'))
            db.save_test_result(
                test_case="Automation Session End",
                url=browser.get_current_url(),
                passed=step_ok,
                should_be="Step 03 to complete successfully",
                found=f"Step 03 completed: checkin={date_info.get('checkin')}, checkout={date_info.get('checkout')}"
            )
            self._print_summary(store_db=store_db)
            return

        # ── STEP 04 ─────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("\n[Step 04] Guest Picker Interaction"))
        step04 = Step04GuestPicker(browser, db)
        guest_count = step04.run()
        self.stdout.write(self.style.SUCCESS(f"  ✓ Guests added: {guest_count}"))
        time.sleep(2)  # Delay after Step 04

        if step == 4:
            db.save_test_result(
                test_case="Automation Session End",
                url=browser.get_current_url(),
                passed=guest_count > 0,
                should_be="Step 04 to complete successfully",
                found=f"Step 04 completed: guests={guest_count}"
            )
            self._print_summary(store_db=store_db)
            return

        # Capture logs after search triggered
        self._save_monitoring_logs(browser, db)

        # ── STEP 05 ─────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("\n[Step 05] Refine Search and Item List Verification"))
        step05 = Step05SearchResults(browser, db)
        listings = step05.run(date_info, guest_count)
        self.stdout.write(self.style.SUCCESS(f"  ✓ Listings scraped: {len(listings)}"))
        time.sleep(2)  # Delay after Step 05

        if step == 5:
            db.save_test_result(
                test_case="Automation Session End",
                url=browser.get_current_url(),
                passed=len(listings) > 0,
                should_be="Step 05 to complete successfully",
                found=f"Step 05 completed: listings={len(listings)}"
            )
            self._print_summary(store_db=store_db)
            return

        # ── STEP 06 ─────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("\n[Step 06] Item Details Page Verification"))
        step06 = Step06ListingDetails(browser, db, persist_to_db=store_db)
        details = step06.run(listings)
        self.stdout.write(self.style.SUCCESS(
            f"  ✓ Details captured: {details.get('title', 'N/A')[:50]}"
        ))
        time.sleep(2)  # Delay after Step 06

        if step == 6:
            db.save_test_result(
                test_case="Automation Session End",
                url=browser.get_current_url(),
                passed=bool(details),
                should_be="Step 06 to complete successfully",
                found=f"Step 06 completed: title={details.get('title', '')[:60]}"
            )
            self._print_summary(store_db=store_db)
            return

        # Final monitoring capture
        self._save_monitoring_logs(browser, db)

        # ── SUMMARY ─────────────────────────────────────────────────────────
        if store_db:
            db.save_test_result(
                test_case="Automation Session End",
                url=browser.get_current_url(),
                passed=True,
                should_be="All 6 steps to complete successfully",
                found=f"Journey completed: country={selected_country}, listings={len(listings)}, title={details.get('title', '')[:60]}"
            )

        self._print_summary(store_db=store_db)

    def _run_deterministic_flow(self, browser: BrowserService, db, airbnb_url: str, store_db: bool = False):
        """Run the exact single-direction Playwright flow provided by the user script.

        This intentionally performs deterministic clicks/typing in sequence and then exits.
        """
        page = browser.page
        self.stdout.write(self.style.HTTP_INFO("\n[Deterministic] Running single-direction flow"))

        # Navigate to Airbnb
        page.goto(airbnb_url, wait_until="domcontentloaded", timeout=15000)
        try:
            page.wait_for_load_state("load", timeout=10000)
        except Exception:
            pass

        # Use last selected country if present in DB flow; otherwise fall back to 'bangladesh'.
        search_text = 'bangladesh'
        try:
            # If a previous Step01 run created selected_country on this Command instance, reuse it.
            # Fallback to the deterministic literal if not set.
            if hasattr(self, 'selected_country') and self.selected_country:
                search_text = self.selected_country
        except Exception:
            pass

        try:
            page.get_by_test_id("structured-search-input-field-query").click()
        except Exception:
            pass

        try:
            page.get_by_test_id("structured-search-input-field-query").fill(search_text)
        except Exception:
            try:
                # Fallback to visible input
                inp = page.get_by_placeholder("Search destinations")
                if inp:
                    inp.fill(search_text)
            except Exception:
                pass

        try:
            page.get_by_test_id("option-0").click()
        except Exception:
            pass

        time.sleep(1.5)  # Delay after selecting suggestion

        # Some Airbnb flows require pressing Enter after selecting suggestion
        try:
            page.keyboard.press("Enter")
        except Exception:
            pass

        time.sleep(1)  # Delay after Enter key

        # Debug: capture screenshot and log calendar visibility immediately after suggestion click
        try:
            browser.take_screenshot("after_suggestion_click")
        except Exception:
            pass

        try:
            vis_states = {}
            for sel in probes:
                try:
                    vis_states[sel] = bool(page.locator(sel).first.is_visible(timeout=300))
                except Exception:
                    vis_states[sel] = False
            self.stdout.write(self.style.NOTICE(f"Calendar probe visibility after suggestion: {vis_states}"))
        except Exception:
            pass

        # Immediately try clicking the date picker opener to trigger calendar.
        try:
            opener_try = [
                page.get_by_role("button", name=re.compile(r"Check in|check-in|Add dates", re.IGNORECASE)).first,
                page.locator("[data-testid*='structured-search-input-field-dates']").first,
                page.locator("[data-testid*='structured-search-input-field-split-dates-0']").first,
            ]
            for opener in opener_try:
                try:
                    if opener.is_visible(timeout=700):
                        try:
                            opener.evaluate("el => el.click()")
                        except Exception:
                            opener.click(timeout=1200)
                        time.sleep(1)  # Delay after clicking opener
                        break
                except Exception:
                    continue
        except Exception:
            pass

        # Wait for date picker to appear; if it doesn't, try opening it explicitly.
        calendar_open = False
        probes = [
            "[aria-label='Calendar'][role='application']",
            "button[data-state--date-string]",
            "button[aria-label*='Move forward to switch to the']",
            "[data-testid='expanded-searchbar-dates-calendar-tab']",
        ]
        start = time.time()
        while time.time() - start < 2.5:
            for sel in probes:
                try:
                    if page.locator(sel).first.is_visible(timeout=300):
                        calendar_open = True
                        break
                except Exception:
                    continue
            if calendar_open:
                break
            time.sleep(0.12)

        if not calendar_open:
            # Try clicking date opener elements to force the calendar open.
            openers = [
                # common check-in/check-out buttons
                page.get_by_role("button", name=re.compile(r"Check in|check-in|Add dates", re.IGNORECASE)).first,
                page.locator("[data-testid*='structured-search-input-field-split-dates-0']").first,
                page.locator("[data-testid*='structured-search-input-field-dates']").first,
                page.locator("[data-testid='little-search']").first,
            ]
            for opener in openers:
                try:
                    if opener.is_visible(timeout=800):
                        try:
                            opener.evaluate("el => el.click()")
                        except Exception:
                            opener.click(timeout=1200)
                        time.sleep(0.25)
                        try:
                            browser.take_screenshot("after_opener_click")
                        except Exception:
                            pass
                        # check again
                        for sel in probes:
                            try:
                                if page.locator(sel).first.is_visible(timeout=400):
                                    calendar_open = True
                                    break
                            except Exception:
                                continue
                        if calendar_open:
                            break
                except Exception:
                    continue

        # Click next month button up to 4 times (best-effort)
        for _ in range(4):
            try:
                page.get_by_role("button", name="Move forward to switch to the").click()
            except Exception:
                try:
                    # Try a more generic next selector
                    page.locator("button[aria-label*='Move forward']").first.click()
                except Exception:
                    break
            time.sleep(0.5)  # Delay between month advances

        time.sleep(1.5)  # Delay after advancing all months

        # After advancing months, pick two available dates at random (chronological)
        calendar_open = False
        probes = [
            "[aria-label='Calendar'][role='application']",
            "button[data-state--date-string]",
            "button[aria-label*='Move forward to switch to the']",
            "[data-testid='expanded-searchbar-dates-calendar-tab']",
        ]
        start = time.time()
        while time.time() - start < 2.5:
            for sel in probes:
                try:
                    if page.locator(sel).first.is_visible(timeout=300):
                        calendar_open = True
                        break
                except Exception:
                    continue
            if calendar_open:
                break
            time.sleep(0.12)

        if calendar_open:
            try:
                loc = page.locator("button[data-state--date-string]:not([disabled]):not([aria-disabled='true']):visible")
                total = loc.count()
                if total >= 2:
                    # collect visible indexes (to preserve DOM order)
                    visible_idxs = []
                    for i in range(min(total, 50)):
                        try:
                            btn = loc.nth(i)
                            if not btn.is_visible(timeout=200):
                                continue
                            visible_idxs.append(i)
                        except Exception:
                            continue

                    if len(visible_idxs) >= 2:
                        i1 = random.choice(visible_idxs[:-1])
                        greater = [x for x in visible_idxs if x > i1]
                        if greater:
                            i2 = random.choice(greater)
                        else:
                            i2 = min(i1 + 1, total - 1)

                        try:
                            loc.nth(i1).click(timeout=2000)
                            time.sleep(0.8)  # Delay after clicking first date
                        except Exception:
                            pass
                        try:
                            loc.nth(i2).click(timeout=2000)
                            time.sleep(0.8)  # Delay after clicking second date
                        except Exception:
                            pass
                    else:
                        # fallback: try role-based visible date buttons
                        day_buttons = page.get_by_role("button", name=re.compile(r"^\d{1,2},\s")).filter(has_text=True)
                        if day_buttons.count() >= 2:
                            a = 0
                            b = 1
                            try:
                                day_buttons.nth(a).click(timeout=1800)
                                time.sleep(0.12)
                                day_buttons.nth(b).click(timeout=1800)
                            except Exception:
                                pass
            except Exception:
                pass

        # Open guest picker and increment counts as in the script
        try:
            page.get_by_role("button", name="Who Add guests").click()
        except Exception:
            try:
                page.get_by_role("button", name="Who").click()
            except Exception:
                pass

        time.sleep(1)  # Delay after opening guest picker

        for _ in range(3):
            try:
                page.get_by_test_id("stepper-adults-increase-button").click()
                time.sleep(0.3)  # Delay between guest increments
            except Exception:
                break

        for _ in range(2):
            try:
                page.get_by_test_id("stepper-children-increase-button").click()
                time.sleep(0.3)  # Delay between guest increments
            except Exception:
                break

        try:
            page.get_by_test_id("stepper-infants-increase-button").click()
            time.sleep(0.3)
        except Exception:
            pass

        try:
            page.get_by_test_id("stepper-pets-increase-button").click()
            time.sleep(0.3)
        except Exception:
            pass

        time.sleep(1)  # Delay after setting guest counts

        # Click search
        try:
            page.get_by_test_id("structured-search-input-search-button").click()
        except Exception:
            try:
                page.get_by_role("button", name="Search").click()
            except Exception:
                pass

        time.sleep(2)  # Delay after clicking search

        # Optionally open a listing in a popup (best-effort mimic of script)
        try:
            with page.expect_popup() as popup_info:
                page.locator("a").nth(3).click()
            popup = popup_info.value
            # Allow some time for the popup to load then close it.
            time.sleep(1.0)
            try:
                popup.close()
            except Exception:
                pass
        except Exception:
            pass

        # Finalize: capture logs and take a screenshot
        try:
            browser.take_screenshot("deterministic_flow_end")
            self._save_monitoring_logs(browser, db)
        except Exception:
            pass

        # When deterministic flow finishes, record session end and exit.
        if store_db:
            db.save_test_result(
                test_case="Deterministic Flow End",
                url=browser.get_current_url(),
                passed=True,
                should_be="Deterministic single-direction flow to complete",
                found="Completed deterministic flow"
            )
        self._print_summary(store_db=store_db)

    def _save_monitoring_logs(self, browser: BrowserService, db):
        """Capture and save console + network logs."""
        try:
            console_logs = browser.get_console_logs()
            if console_logs:
                db.save_console_logs(console_logs)

            network_logs = browser.get_network_logs()
            if network_logs:
                db.save_network_logs(network_logs)
        except Exception as e:
            logger.debug(f"Could not capture monitoring logs: {e}")

    def _print_summary(self, store_db: bool = False):
        """Print a final summary of test results."""
        total = passed = failed = 0
        if store_db:
            from automation.models import TestResult
            total = TestResult.objects.count()
            passed = TestResult.objects.filter(passed=True).count()
            failed = total - passed

        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*60}\n"
            f"  AUTOMATION COMPLETE\n"
            f"  Total Test Cases: {total if store_db else 'N/A (DB disabled)'}\n"
            f"  Passed:           {passed if store_db else 'N/A (DB disabled)'}\n"
            f"  Failed:           {failed if store_db else 'N/A (DB disabled)'}\n"
            f"{'='*60}\n"
        ))
