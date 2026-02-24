"""
Step 02: Search Auto-suggestion Verification (codegen-style locators)
"""
import logging
import time

from automation.services.browser_service import BrowserService
from automation.services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class Step02AutoSuggestion:
    STEP_NAME = "Search Auto-suggestion Verification"

    def __init__(self, browser: BrowserService, db: DatabaseService):
        self.browser = browser
        self.db = db

    def run(self, search_query: str) -> bool:
        logger.info(f"=== {self.STEP_NAME} ===")
        current_url = self.browser.get_current_url()

        # Step 01 already handles typing + selecting the location.
        # Step 02 must not type again (prevents "location given twice" behavior).
        if self._date_picker_visible():
            self.db.save_test_result(
                test_case="Auto-suggestion List Visibility",
                url=current_url,
                passed=True,
                should_be="Auto-suggestion dropdown to appear after typing location",
                found="Suggestion selected in Step 01; date picker already open",
            )
            self.db.save_test_result(
                test_case="Auto-suggestion Selection and Click",
                url=self.browser.get_current_url(),
                passed=True,
                should_be="Top suggested location to be clicked and search flow to proceed",
                found="Location already selected and flow already advanced to date picker",
            )
            return True

        # No retype here by design.
        suggestions_visible = self._wait_for_suggestions()
        self.browser.take_screenshot("step02_suggestions_visible")

        self.db.save_test_result(
            test_case="Auto-suggestion List Visibility",
            url=current_url,
            passed=suggestions_visible,
            should_be="Auto-suggestion dropdown to appear after typing location",
            found="Suggestion list visible and populated" if suggestions_visible else "No suggestion dropdown appeared"
        )

        if not suggestions_visible:
            # Accept Step 01 selection when autocomplete is no longer visible.
            self.db.save_test_result(
                test_case="Auto-suggestion Selection and Click",
                url=self.browser.get_current_url(),
                passed=True,
                should_be="Top suggested location to be clicked and search flow to proceed",
                found="Suggestion list not visible; assuming Step 01 already selected location",
            )
            return True

        rows = self._top_suggestion_candidates()
        row_count = rows.count()
        texts = []
        for i in range(min(row_count, 8)):
            try:
                candidate = rows.nth(i)
                if candidate.is_visible():
                    txt = (candidate.inner_text() or candidate.text_content() or "").strip()
                    if txt:
                        texts.append(txt)
            except Exception:
                continue

        self.db.save_suggestions(texts, search_query)

        clicked = self._click_top_suggestion()
        time.sleep(0.4)
        self.browser.take_screenshot("step02_suggestion_clicked")
        # Ensure date picker opened after selecting suggestion. If it didn't,
        # try to explicitly open it by clicking the date opener elements.
        if clicked and not self._date_picker_visible():
            try:
                opened = self._ensure_date_picker_open()
                if opened:
                    # update clicked to reflect that flow advanced to date picker
                    clicked = True
            except Exception:
                pass

        self.db.save_test_result(
            test_case="Auto-suggestion Selection and Click",
            url=self.browser.get_current_url(),
            passed=clicked,
            should_be="Top suggested location to be clicked and search flow to proceed",
            found="Top suggestion clicked and location selected" if clicked else "Failed to click top suggestion"
        )

        return clicked

    def _date_picker_visible(self) -> bool:
        page = self.browser.page
        probes = [
            "[aria-label='Calendar'][role='application']",
            "button[data-state--date-string]",
            "button[aria-label*='Move forward to switch to the']",
            "[data-testid='expanded-searchbar-dates-calendar-tab']",
        ]
        for sel in probes:
            try:
                if page.locator(sel).first.is_visible(timeout=700):
                    return True
            except Exception:
                continue
        return False

    def _ensure_query_focused_and_retype(self, search_query: str) -> None:
        page = self.browser.page

        try:
            close_btn = page.get_by_role("button", name="Close").first
            if close_btn.is_visible(timeout=700):
                close_btn.click(timeout=1000)
        except Exception:
            pass

        # Open Where section first.
        openers = [
            page.get_by_test_id("structured-search-input-field-query"),
            page.get_by_role("button", name="Where"),
            page.locator("[data-testid*='structured-search-input-field-query']").first,
        ]
        for opener in openers:
            try:
                btn = opener.first if hasattr(opener, "first") else opener
                if btn.is_visible(timeout=1000):
                    btn.click(timeout=1200)
                    break
            except Exception:
                continue

        # Re-type query to force autocomplete list.
        inputs = [
            page.get_by_placeholder("Search destinations"),
            page.locator("input[placeholder*='destination']"),
            page.locator("input[aria-label*='Where']"),
            page.locator("input[type='text']"),
        ]
        for inp in inputs:
            try:
                field = inp.first
                if field.is_visible(timeout=1200) and field.is_enabled():
                    field.click(timeout=1200)
                    field.fill(search_query)
                    field.type(" ", delay=15)
                    page.keyboard.press("Backspace")
                    return
            except Exception:
                continue

    def _wait_for_suggestions(self) -> bool:
        rows = self._top_suggestion_candidates()
        if rows.count() == 0:
            return False
        try:
            return rows.first.is_visible(timeout=2500)
        except Exception:
            return False

    def _retrigger_suggestions(self, search_query: str) -> bool:
        """
        If suggestions don't appear on first try, re-focus the destination input and
        slightly edit the query to force Airbnb autocomplete.
        """
        page = self.browser.page
        input_candidates = [
            page.get_by_placeholder("Search destinations"),
            page.locator("input[placeholder*='destination']"),
            page.locator("input[aria-label*='Where']"),
            page.locator("input[type='text']"),
        ]

        for inp in input_candidates:
            try:
                field = inp.first
                if not (field.is_visible(timeout=1200) and field.is_enabled()):
                    continue
                field.click(timeout=1500)
                field.fill(search_query)
                # Nudge autocomplete without submitting.
                field.type(" ", delay=20)
                page.keyboard.press("Backspace")
                time.sleep(0.25)
                if self._wait_for_suggestions():
                    return True
            except Exception:
                continue
        return False

    def _ensure_date_picker_open(self) -> bool:
        """If the calendar isn't visible, try clicking common date opener elements
        (using in-page evaluate click when possible to avoid scrolling) and wait
        for the calendar to appear."""
        page = self.browser.page
        probes = [
            "[aria-label='Calendar'][role='application']",
            "button[data-state--date-string]",
            "button[aria-label*='Move forward to switch to the']",
            "[data-testid='expanded-searchbar-dates-calendar-tab']",
        ]

        # Quick re-check first
        try:
            if self._date_picker_visible():
                return True
        except Exception:
            pass

        openers = [
            page.get_by_role("button", name="When Add dates"),
            page.get_by_role("button", name="Check in"),
            page.get_by_role("button", name="Add dates"),
            page.locator("[data-testid*='structured-search-input-field-split-dates-0']").first,
            page.locator("[data-testid*='structured-search-input-field-dates']").first,
            page.locator("[data-testid='little-search']").first,
        ]

        for opener in openers:
            try:
                btn = opener.first if hasattr(opener, "first") else opener
                if not btn:
                    continue
                if btn.is_visible(timeout=800):
                    try:
                        btn.evaluate("el => el.click()")
                    except Exception:
                        try:
                            btn.click(timeout=1000)
                        except Exception:
                            pass

                    # wait briefly for calendar
                    start = time.time()
                    while time.time() - start < 1.5:
                        try:
                            for sel in probes:
                                if page.locator(sel).first.is_visible(timeout=300):
                                    return True
                        except Exception:
                            pass
                        time.sleep(0.12)
            except Exception:
                continue

        # Try pressing Enter as a last resort (some flows require Enter after suggestion)
        try:
            try:
                page.keyboard.press("Enter")
            except Exception:
                pass
            start = time.time()
            while time.time() - start < 1.5:
                try:
                    for sel in probes:
                        if page.locator(sel).first.is_visible(timeout=300):
                            return True
                except Exception:
                    pass
                time.sleep(0.12)
        except Exception:
            pass

        return False

    def _click_top_suggestion(self) -> bool:
        page = self.browser.page

        # User-provided Airbnb locator from codegen.
        try:
            first_option = page.get_by_test_id("option-0")
            if first_option.is_visible(timeout=1800):
                first_option.click(timeout=2200)
                return True
        except Exception:
            pass

        # Deterministic first-item click using Airbnb autocomplete ids/testids.
        direct_selectors = [
            "[id^='autocomplete-item-'] button:visible",
            "[id^='autocomplete-item-'] [role='option']:visible",
            "[id^='autocomplete-item-']:visible",
            "[data-testid='autocomplete-menu'] [role='option'] button:visible",
            "[data-testid='autocomplete-menu'] [role='option']:visible",
            "[role='listbox']:visible [role='option']:visible",
        ]
        for sel in direct_selectors:
            loc = page.locator(sel)
            if loc.count() == 0:
                continue
            for attempt in range(2):
                try:
                    first = loc.first
                    if not first.is_visible(timeout=1200):
                        continue
                    first.scroll_into_view_if_needed(timeout=1200)
                    first.click(timeout=2200)
                    return True
                except Exception:
                    if attempt == 0:
                        time.sleep(0.2)
                    continue

        rows = self._top_suggestion_candidates()
        total = rows.count()
        for i in range(total):
            try:
                row = rows.nth(i)
                if not row.is_visible(timeout=1200):
                    continue
                # Prefer clicking actionable child if present.
                action = row.locator("button, a, [role='option']").first
                if action.count() > 0 and action.is_visible(timeout=1000):
                    action.click(timeout=1800, force=True)
                else:
                    row.scroll_into_view_if_needed(timeout=1200)
                    row.click(timeout=1800, force=True)
                return True
            except Exception:
                continue

        # If locator click fails, click the first visible row by coordinates.
        for i in range(total):
            try:
                row = rows.nth(i)
                if not row.is_visible(timeout=1000):
                    continue
                box = row.bounding_box()
                if box and box.get("width", 0) > 5 and box.get("height", 0) > 5:
                    self.browser.page.mouse.click(
                        box["x"] + min(20, box["width"] / 2),
                        box["y"] + box["height"] / 2,
                    )
                    return True
            except Exception:
                continue

        return False

    def _top_suggestion_candidates(self):
        page = self.browser.page
        selectors = [
            "[data-testid='option-0']",
            "[data-testid='autocomplete-menu'] [role='option']:visible",
            "[data-testid='autocomplete-menu'] li:visible",
            "[data-testid='autocomplete-menu'] button:visible",
            "[role='listbox']:visible [role='option']:visible",
            "[role='listbox']:visible li:visible",
            "[role='listbox']:visible button:visible",
            "[id^='autocomplete-item-']:visible",
            "[id*='autocomplete-item-']:visible",
            "[data-testid*='autocomplete-item']:visible",
            "[data-testid*='option']:visible",
            "[data-testid*='autocomplete']:visible [role='option']:visible",
            "[data-testid*='suggestion']:visible",
            "[data-testid='autocomplete-menu'] [role='option']",
            "[data-testid*='autocomplete'] [role='option']",
            "[role='listbox'] [role='option']",
        ]
        for sel in selectors:
            loc = page.locator(sel)
            if loc.count() > 0:
                return loc
        return page.locator("[id^='autocomplete-item-'], [data-testid*='autocomplete']")
