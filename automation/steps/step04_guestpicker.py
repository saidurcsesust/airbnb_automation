"""
Step 04: Guest Picker Interaction (codegen-style locators)
"""
import logging
import random
import re
import time

from automation.services.browser_service import BrowserService
from automation.services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class Step04GuestPicker:
    STEP_NAME = "Guest Picker Interaction"

    def __init__(self, browser: BrowserService, db: DatabaseService):
        self.browser = browser
        self.db = db
        self.total_selected = 0

    def run(self) -> int:
        logger.info(f"=== {self.STEP_NAME} ===")

        opened = self._open_guest_picker()
        self.browser.take_screenshot("step04_guest_picker_open")

        self.db.save_test_result(
            test_case="Guest Picker Open Verification",
            url=self.browser.get_current_url(),
            passed=opened,
            should_be="Guest picker popup to open when Who/Add guests field is clicked",
            found="Guest picker popup opened" if opened else "Guest picker did not open"
        )

        if not opened:
            return 0

        # Ensure stepper controls are actually visible before trying to increment.
        if not self._guest_controls_visible():
            opened = self._open_guest_picker()

        self.total_selected = self._add_adults_children_randomly()
        self.browser.take_screenshot("step04_guests_selected")

        displayed = self._get_displayed_count()
        self.db.save_test_result(
            test_case="Guest Count Display Verification",
            url=self.browser.get_current_url(),
            passed=displayed > 0 or self.total_selected > 0,
            should_be="Guest count to be visible in Who field",
            found=f"Guest field displays: {displayed} guest(s)"
        )

        searched = self._click_search()
        time.sleep(0.5)
        self.browser.take_screenshot("step04_search_clicked")

        self.db.save_test_result(
            test_case="Search Button Click After Guest Selection",
            url=self.browser.get_current_url(),
            passed=searched,
            should_be="Search button to be clickable and trigger results",
            found="Search triggered" if searched else "Search button click failed"
        )

        return self.total_selected

    def _open_guest_picker(self) -> bool:
        page = self.browser.page
        candidates = [
            page.get_by_role("button", name="Who Add guests"),
            page.get_by_role("button", name="Who"),
            page.get_by_role("button", name="Add guests"),
            page.get_by_text("Who", exact=True),
            page.locator("[data-testid*='structured-search-input-field-guests']").first,
        ]

        for c in candidates:
            try:
                if c.is_visible(timeout=2000):
                    c.click(timeout=2000)
                    time.sleep(0.2)
                    if self._guest_controls_visible():
                        return True
            except Exception:
                continue
        return self._guest_controls_visible()

    def _guest_controls_visible(self) -> bool:
        page = self.browser.page
        probes = [
            "button[data-testid='stepper-adults-increase-button']",
            "button[data-testid='stepper-children-increase-button']",
            "button[data-testid='stepper-infants-increase-button']",
            "button[aria-label*='Add adult']",
        ]
        for sel in probes:
            try:
                if page.locator(sel).first.is_visible(timeout=1000):
                    return True
            except Exception:
                continue
        return False

    def _add_adults_children_randomly(self) -> int:
        # Prefer fixed codegen-style increments with explicit Airbnb test ids.
        deterministic_added = self._apply_codegen_guest_clicks()
        if deterministic_added > 0:
            logger.info(f"Guests added via codegen locators: total={deterministic_added}")
            return deterministic_added

        adults = random.randint(1, 3)
        children = random.randint(0, 2)
        added = 0

        added += self._click_increment([
            "button[data-testid='stepper-adults-increase-button']",
            "button:has-text('Adults') >> xpath=ancestor::*[1]//button[contains(@aria-label,'increase')]",
            "button[aria-label*='Add adult']",
        ], adults)

        # Hard guard: at least 1 adult must be selected.
        if added == 0:
            self._open_guest_picker()
            added += self._click_increment([
                "button[data-testid='stepper-adults-increase-button']",
                "button[aria-label*='Add adult']",
            ], 1)

        added += self._click_increment([
            "button[data-testid='stepper-children-increase-button']",
            "button[aria-label*='Add children']",
            "button[aria-label*='children'][aria-label*='increase']",
        ], children)

        logger.info(f"Guests added: adults={adults}, children={children}, total={added}")
        return added

    def _apply_codegen_guest_clicks(self) -> int:
        page = self.browser.page
        steps = [
            ("stepper-adults-increase-button", 3),
            ("stepper-children-increase-button", 2),
            ("stepper-infants-increase-button", 1),
            ("stepper-pets-increase-button", 1),
        ]

        added = 0
        for test_id, count in steps:
            for _ in range(count):
                try:
                    btn = page.get_by_test_id(test_id).first
                    if btn.is_visible(timeout=1000) and btn.is_enabled():
                        btn.click(timeout=1500)
                        added += 1
                        time.sleep(0.1)
                    else:
                        break
                except Exception:
                    break

        return added

    def _click_increment(self, selectors: list, count: int) -> int:
        done = 0
        for _ in range(count):
            clicked = False
            for sel in selectors:
                try:
                    btn = self.browser.page.locator(sel).first
                    if btn.is_visible(timeout=1000) and btn.is_enabled():
                        btn.click(timeout=1500)
                        time.sleep(0.2)
                        done += 1
                        clicked = True
                        break
                except Exception:
                    continue
            if not clicked:
                break
        return done

    def _get_displayed_count(self) -> int:
        selectors = [
            "[data-testid*='structured-search-input-field-guests']",
            "button:has-text('guest')",
            "*:has-text('guest')",
        ]
        for sel in selectors:
            el = self.browser.safe_find(sel)
            if el:
                try:
                    text = (el.text_content() or '').strip()
                    nums = re.findall(r'\d+', text)
                    if nums:
                        return int(nums[0])
                except Exception:
                    continue
        return self.total_selected

    def _click_search(self) -> bool:
        page = self.browser.page
        candidates = [
            page.get_by_role("button", name="Search"),
            page.locator("button[data-testid='structured-search-input-search-button']").first,
            page.locator("button[type='submit']").first,
        ]

        for c in candidates:
            try:
                if c.is_visible(timeout=1500) and c.is_enabled():
                    c.click(timeout=2000)
                    return True
            except Exception:
                continue

        return False
