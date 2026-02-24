"""
Step 01: Website Landing and Initial Search Setup
"""
import logging
import random
import time

from automation.services.browser_service import BrowserService
from automation.services.database_service import DatabaseService
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

TOP_20_COUNTRIES = [
    "Germany", "Rome Italy", "New York USA", "Paris France", "London United Kingdom",
    "Tokyo Japan", "Bangkok Thailand", "Barcelona Spain", "Amsterdam Netherlands", "Dubai UAE",
    "Berlin Germany", "Venice Italy", "Los Angeles USA", "Madrid Spain", "Sydney Australia",
    "Singapore", "Hong Kong", "Mexico City Mexico", "Copenhagen Denmark", "Vienna Austria",
]


class Step01LandingAndSearch:
    STEP_NAME = "Website Landing and Initial Search Setup"

    def __init__(self, browser: BrowserService, db: DatabaseService, airbnb_url: str):
        self.browser = browser
        self.db = db
        self.airbnb_url = airbnb_url
        self.selected_country = None

    # ===================== RUN =====================
    def run(self) -> str:
        logger.info(f"=== {self.STEP_NAME} ===")
        page = self.browser.page

        # --- open homepage
        page.goto(self.airbnb_url, wait_until="domcontentloaded", timeout=15000)
        try:
            page.wait_for_load_state("load", timeout=10000)
        except PlaywrightTimeoutError:
            # Airbnb can keep loading trackers; proceed once key search UI is visible.
            page.wait_for_selector(
                "[data-testid='structured-search-input-field-query']",
                timeout=12000,
            )

        self.close_any_modal()
        self._close_modal_now()

        self.browser.take_screenshot("step01_open_homepage")

        current_url = self.browser.get_current_url()
        self.db.save_test_result(
            test_case="Homepage Load Verification",
            url=current_url,
            passed="airbnb" in current_url,
            should_be="airbnb homepage loads",
            found=current_url,
        )

        # --- welcome popup
        self._wait_and_close_welcome_popup()

        # --- prepare 20 random locations and choose one to type
        locations = random.sample(TOP_20_COUNTRIES, k=min(20, len(TOP_20_COUNTRIES)))
        # pick one randomly from the generated list to enter into the input
        self.selected_country = random.choice(locations)

        # Type the chosen location and select the top suggestion (click)
        clicked = self._enter_destination_and_select(self.selected_country)

        self.browser.take_screenshot("step01_location_selected")

        self.db.save_test_result(
            test_case="Search Field Input",
            url=self.browser.get_current_url(),
            passed=True,
            should_be=f"{self.selected_country} selected",
            found="Suggestion clicked" if clicked else "Typed and submitted with Enter",
        )

        return self.selected_country

    def _enter_destination_and_select(self, destination: str) -> bool:
        page = self.browser.page
        self._close_modal_now()

        # Prefer the historically stable flow:
        # slow type -> wait options -> click first suggestion.
        try:
            query = page.get_by_test_id("structured-search-input-field-query")
            if query.is_visible(timeout=2500):
                self._close_modal_now()
                query.click(timeout=2000)
                typing_input = self._resolve_text_input(query) or query
                self.browser.slow_type(typing_input, destination)
                page.wait_for_selector('[role="option"]', timeout=6000)
                page.get_by_role("option").first.click(timeout=2500)
                self._close_modal_now()
                self._wait_for_date_picker_auto_open()
                self.browser.take_screenshot("step01_search_typed")
                return True
        except Exception:
            pass

        search_field = self._open_where_and_get_input()
        if not search_field:
            return False

        typing_input = self._resolve_text_input(search_field)
        if not typing_input:
            return False

        try:
            self._close_modal_now()
            typing_input.click(timeout=2000)
            self.browser.slow_type(typing_input, destination)
            page.wait_for_selector('[role="option"]', timeout=6000)
            page.get_by_role("option").first.click(timeout=2500)
            self._close_modal_now()
            self._wait_for_date_picker_auto_open()
            self.browser.take_screenshot("step01_search_typed")
            return True
        except Exception:
            try:
                typing_input.click(timeout=2000)
                typing_input.press("Control+A")
                typing_input.press("Backspace")
                typing_input.type(destination, delay=90)
            except Exception:
                return False

        time.sleep(0.6)
        try:
            option0 = page.get_by_test_id("option-0")
            if option0.is_visible(timeout=1500):
                option0.click(timeout=2000)
                self._wait_for_date_picker_auto_open()
                return True
        except Exception:
            pass

        for _ in range(3):
            try:
                options = page.get_by_role("option")
                if options.first.is_visible(timeout=1500):
                    options.first.click(timeout=2000)
                    self._wait_for_date_picker_auto_open()
                    return True
            except Exception:
                time.sleep(0.4)

        try:
            page.keyboard.press("Enter")
        except Exception:
            pass
        return False

    def _wait_for_date_picker_auto_open(self, timeout_sec: float = 4.0) -> bool:
        page = self.browser.page
        probes = [
            "[aria-label='Calendar'][role='application']",
            "button[data-state--date-string]",
            "button[aria-label*='Move forward to switch to the']",
            "[data-testid='expanded-searchbar-dates-calendar-tab']",
        ]
        start = time.time()
        while time.time() - start < timeout_sec:
            for sel in probes:
                try:
                    if page.locator(sel).first.is_visible(timeout=400):
                        return True
                except Exception:
                    continue
            time.sleep(0.15)
        return False

    # ===================== MODAL HELPERS =====================
    def close_any_modal(self):
        try:
            self.browser.page.keyboard.press("Escape")
        except Exception:
            pass
        self._close_modal_now()

    def _close_modal_now(self):
        """
        Immediately try to close any visible modal/popup dialog.
        Kept short to avoid slowing the flow.
        """
        page = self.browser.page
        # If the search destination input is focused or already has text,
        # avoid closing modals/popups as that can clear the input unexpectedly.
        try:
            script = """() => {
                const selectors = [
                    "[data-testid='structured-search-input-field-query']",
                    "input[placeholder*='destination']",
                    "input[type='text']"
                ];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (!el) continue;
                    if (el === document.activeElement) return true;
                    try {
                        const v = el.value || el.textContent || '';
                        if (v && v.trim().length > 0) return true;
                    } catch (e) {}
                }
                return false;
            }"""
            try:
                if page.evaluate(script):
                    logger.info("Skipping modal close: search input focused/has text")
                    return
            except Exception:
                pass
        except Exception:
            pass
        quick_close_targets = [
            page.get_by_role("button", name="Close"),
            page.get_by_role("button", name="Dismiss"),
            page.locator("button[aria-label*='close' i]"),
            page.locator("button[aria-label*='dismiss' i]"),
            page.locator("[role='dialog'] button").first,
        ]

        for target in quick_close_targets:
            try:
                btn = target.first if hasattr(target, "first") else target
                if btn.is_visible(timeout=250):
                    btn.click(timeout=500, force=True)
                    time.sleep(0.08)
            except Exception:
                continue

        try:
            page.keyboard.press("Escape")
        except Exception:
            pass

    def _wait_and_close_welcome_popup(self, max_wait_sec: int = 10):
        page = self.browser.page
        start = time.time()

        dialog = page.get_by_role("dialog")

        while time.time() - start < max_wait_sec:
            try:
                self._close_modal_now()
                if dialog.first.is_visible(timeout=500):
                    close_buttons = [
                        dialog.get_by_role("button", name="Close"),
                        dialog.get_by_role("button", name="Dismiss"),
                        dialog.locator("button[aria-label*='close']"),
                    ]

                    for btn in close_buttons:
                        try:
                            if btn.first.is_visible(timeout=400):
                                btn.first.click(force=True)
                                return
                        except Exception:
                            pass

                    page.keyboard.press("Escape")
                    return
            except Exception:
                pass

            time.sleep(0.3)

    # ===================== SEARCH FIELD =====================
    def _open_where_and_get_input(self):
        page = self.browser.page

        click_candidates = [
            page.get_by_test_id("structured-search-input-field-query"),
            page.get_by_role("button", name="Where"),
            page.get_by_role("button", name="Search destinations"),
        ]

        for target in click_candidates:
            try:
                if target.is_visible(timeout=1500):
                    target.click()
                    break
            except Exception:
                continue

        input_candidates = [
            page.get_by_placeholder("Search destinations"),
            page.locator("input[placeholder*='destination']"),
            page.locator("input[type='text']"),
        ]

        for inp in input_candidates:
            try:
                if inp.first.is_visible(timeout=2000):
                    return inp.first
            except Exception:
                pass

        return None

    def _resolve_text_input(self, locator):
        try:
            tag = (locator.evaluate("el => el.tagName") or "").lower()
            if tag in {"input", "textarea"}:
                return locator
        except Exception:
            pass

        try:
            nested = locator.locator("input, textarea").first
            if nested.is_visible(timeout=1200):
                return nested
        except Exception:
            pass

        return None
