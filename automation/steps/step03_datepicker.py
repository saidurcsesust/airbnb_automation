"""
Step 03: Date Picker Interaction (codegen-style locators)
"""
import logging
import random
import re
import time

from automation.services.browser_service import BrowserService
from automation.services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class Step03DatePicker:
    STEP_NAME = "Date Picker Interaction"

    def __init__(self, browser: BrowserService, db: DatabaseService):
        self.browser = browser
        self.db = db
        self.checkin_date = None
        self.checkout_date = None

    def run(self) -> dict:
        logger.info(f"=== {self.STEP_NAME} ===")

        picker_open = self._open_date_picker()
        self.browser.take_screenshot("step03_date_picker_open")

        self.db.save_test_result(
            test_case="Date Picker Modal Open and Visibility Test",
            url=self.browser.get_current_url(),
            passed=picker_open,
            should_be="Date picker modal to open after location selection",
            found="Date picker opened" if picker_open else "Date picker did not open"
        )

        if not picker_open:
            return {'checkin': None, 'checkout': None}

        checkin_ok, checkout_ok = self._select_random_two_dates()

        self.browser.take_screenshot("step03_dates_selected")
        self.db.save_test_result(
            test_case="Date Selection Validation",
            url=self.browser.get_current_url(),
            passed=checkin_ok and checkout_ok,
            should_be="Check-in and check-out dates to be selected",
            found=f"Check-in: {self.checkin_date}, Check-out: {self.checkout_date}"
        )

        return {'checkin': self.checkin_date, 'checkout': self.checkout_date}

    def _open_date_picker(self) -> bool:
        if self._calendar_is_visible():
            return True

        # Force-open calendar if auto-open did not happen.
        for _ in range(3):
            expanders = [
                self.browser.page.locator("[data-testid='little-search']").first,
            ]
            for exp in expanders:
                try:
                    if exp.is_visible(timeout=500):
                        exp.click(timeout=1000)
                        time.sleep(0.2)
                        if self._calendar_is_visible():
                            return True
                except Exception:
                    continue

            openers = [
                self.browser.page.get_by_role("button", name=re.compile(r"Check in|check-in|Add dates", re.IGNORECASE)).first,
                self.browser.page.get_by_role("button", name=re.compile(r"Check out|check-out|Add dates", re.IGNORECASE)).first,
                self.browser.page.locator("[data-testid*='structured-search-input-field-split-dates-0']").first,
                self.browser.page.locator("[data-testid*='structured-search-input-field-split-dates-1']").first,
                self.browser.page.locator("[data-testid*='structured-search-input-field-dates']").first,
            ]
            for opener in openers:
                try:
                    if opener.is_visible(timeout=700):
                        opener.click(timeout=1500)
                        time.sleep(0.25)
                        if self._calendar_is_visible():
                            return True
                except Exception:
                    continue

        start = time.time()
        while time.time() - start < 4.0:
            if self._calendar_is_visible():
                return True
            time.sleep(0.2)

        return False

    def _calendar_is_visible(self) -> bool:
        page = self.browser.page
        probes = [
            "[aria-label='Calendar'][role='application']",
            "button[data-state--date-string]",
            "button[aria-label='Move forward to switch to the next month.']",
            "button[aria-label*='Move forward']",
            "[data-testid='expanded-searchbar-dates-calendar-tab']",
        ]
        for sel in probes:
            try:
                if page.locator(sel).first.is_visible(timeout=1500):
                    return True
            except Exception:
                continue
        return False

    def _get_available_day_buttons(self):
        page = self.browser.page
        loc = page.locator(
            "button[data-state--date-string]:not([disabled]):not([aria-disabled='true']):visible"
        )
        dates = []
        for i in range(loc.count()):
            btn = loc.nth(i)
            try:
                date_str = btn.get_attribute("data-state--date-string")
                if date_str:
                    dates.append(date_str)
            except Exception:
                continue

        # Keep order + dedupe
        return list(dict.fromkeys(dates))

    def _select_random_two_dates(self) -> tuple[bool, bool]:
        for _ in range(3):
            ok1, ok2 = self._select_two_available_days()
            if ok1 and ok2:
                return True, True

        ok1, ok2 = self._select_two_days_via_js()
        if ok1 and ok2:
            return True, True

        # First try flow aligned with provided locators:
        # advance calendar then click by accessible date labels.
        if self._select_by_role_date_buttons():
            return True, True

        date_values = self._get_available_day_buttons()
        if len(date_values) < 2 and self._open_date_picker():
            date_values = self._get_available_day_buttons()
        if len(date_values) < 2:
            return False, False

        try:
            # Pick two chronological visible dates.
            start_max = max(0, len(date_values) - 2)
            idx1 = random.randint(0, min(start_max, 10))
            max_gap = min(7, len(date_values) - idx1 - 1)
            gap = random.randint(1, max_gap if max_gap > 0 else 1)
            idx2 = min(idx1 + gap, len(date_values) - 1)

            self.checkin_date = date_values[idx1]
            self.checkout_date = date_values[idx2]

            checkin_btn = self.browser.page.locator(
                f"button[data-state--date-string='{self.checkin_date}']:not([disabled]):not([aria-disabled='true'])"
            ).first
            checkin_btn.click(timeout=2000)
            time.sleep(0.15)

            checkout_btn = self.browser.page.locator(
                f"button[data-state--date-string='{self.checkout_date}']:not([disabled]):not([aria-disabled='true'])"
            ).first
            checkout_btn.click(timeout=2000)
            return True, True
        except Exception as e:
            logger.warning(f"Date selection failed: {e}")
            return False, False

    def _select_two_available_days(self) -> tuple[bool, bool]:
        page = self.browser.page
        selectors = [
            "[role='application'][aria-label='Calendar'] button[aria-label*=','][aria-label*='20']:not([disabled]):not([aria-disabled='true']):visible",
            "button[data-state--date-string]:not([disabled]):not([aria-disabled='true']):visible",
            "button[aria-label*='Available']:not([disabled]):not([aria-disabled='true']):visible",
            "button[aria-label*=','][aria-label*='20']:not([disabled]):not([aria-disabled='true']):visible",
            "button[data-testid*='calendar-day']:not([disabled]):visible",
        ]

        for _ in range(3):
            day_buttons = None
            for sel in selectors:
                loc = page.locator(sel)
                if loc.count() >= 2:
                    day_buttons = loc
                    break

            if day_buttons is None or day_buttons.count() < 2:
                self._click_next_month_once()
                continue

            total = day_buttons.count()
            start_idx = min(2, total - 2) if total > 2 else 0
            end_idx = min(start_idx + 2, total - 1)

            try:
                checkin_btn = day_buttons.nth(start_idx)
                checkout_btn = day_buttons.nth(end_idx)

                checkin_label = (
                    checkin_btn.get_attribute("data-state--date-string")
                    or checkin_btn.get_attribute("aria-label")
                    or checkin_btn.text_content()
                    or ""
                ).strip()
                checkout_label = (
                    checkout_btn.get_attribute("data-state--date-string")
                    or checkout_btn.get_attribute("aria-label")
                    or checkout_btn.text_content()
                    or ""
                ).strip()

                if not checkin_label or not checkout_label or checkin_label == checkout_label:
                    self._click_next_month_once()
                    continue

                checkin_btn.click(timeout=1800)
                time.sleep(0.15)
                checkout_btn.click(timeout=1800)

                self.checkin_date = checkin_label
                self.checkout_date = checkout_label
                return True, True
            except Exception:
                self._click_next_month_once()
                continue

        return False, False

    def _select_two_days_via_js(self) -> tuple[bool, bool]:
        page = self.browser.page
        try:
            result = page.evaluate(
                """
                () => {
                  const visible = (el) => {
                    const s = window.getComputedStyle(el);
                    const r = el.getBoundingClientRect();
                    return s && s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
                  };
                  const candidates = Array.from(document.querySelectorAll("button"))
                    .filter((b) => {
                      if (!visible(b)) return false;
                      if (b.disabled) return false;
                      if ((b.getAttribute("aria-disabled") || "").toLowerCase() === "true") return false;
                      const label = (b.getAttribute("aria-label") || "").trim();
                      if (!label) return false;
                      if (!/\\d{1,2},/.test(label)) return false;
                      if (/unavailable|past date|not available/i.test(label)) return false;
                      return true;
                    });
                  if (candidates.length < 2) return {ok:false, labels:[]};
                  const first = candidates[Math.min(2, candidates.length - 2)];
                  const second = candidates[Math.min(4, candidates.length - 1)];
                  const l1 = (first.getAttribute("aria-label") || first.textContent || "").trim();
                  const l2 = (second.getAttribute("aria-label") || second.textContent || "").trim();
                  first.click();
                  second.click();
                  return {ok:true, labels:[l1, l2]};
                }
                """
            )
            if result and result.get("ok") and len(result.get("labels", [])) == 2:
                self.checkin_date = result["labels"][0]
                self.checkout_date = result["labels"][1]
                return True, True
        except Exception:
            pass
        return False, False

    def _click_next_month_once(self) -> None:
        page = self.browser.page
        next_selectors = [
            "button[aria-label='Move forward to switch to the next month.']",
            "button[aria-label*='Move forward to switch to the']",
            "button[aria-label*='Next month']",
        ]
        for sel in next_selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=800) and btn.is_enabled():
                    btn.click(timeout=1200)
                    time.sleep(0.1)
                    return
            except Exception:
                continue

    def _select_by_role_date_buttons(self) -> bool:
        page = self.browser.page

        # Provided locator: "Move forward to switch to the..."
        for _ in range(4):
            try:
                next_btn = page.get_by_role(
                    "button",
                    name=re.compile(r"Move forward to switch to the", re.IGNORECASE),
                ).first
                if next_btn.is_visible(timeout=1200):
                    next_btn.click(timeout=1500)
                    time.sleep(0.1)
            except Exception:
                break

        # Prefer exact labels from shared script, then generic visible date buttons.
        exact_labels = [
            "15, Monday, June 2026.",
            "18, Thursday, June 2026.",
        ]
        chosen_labels = []
        for label in exact_labels:
            try:
                btn = page.get_by_role("button", name=label).first
                if btn.is_visible(timeout=1200) and btn.is_enabled():
                    btn.click(timeout=1800)
                    chosen_labels.append(label)
            except Exception:
                continue

        if len(chosen_labels) == 2:
            self.checkin_date = chosen_labels[0]
            self.checkout_date = chosen_labels[1]
            return True

        day_buttons = page.get_by_role("button", name=re.compile(r"^\d{1,2},\s", re.IGNORECASE))
        total = day_buttons.count()
        selected = []
        for i in range(total):
            try:
                btn = day_buttons.nth(i)
                if not (btn.is_visible(timeout=600) and btn.is_enabled()):
                    continue
                label = btn.get_attribute("aria-label") or ""
                if not label:
                    continue
                btn.click(timeout=1600)
                selected.append(label)
                if len(selected) == 2:
                    break
            except Exception:
                continue

        if len(selected) == 2:
            self.checkin_date = selected[0]
            self.checkout_date = selected[1]
            return True

        return False
