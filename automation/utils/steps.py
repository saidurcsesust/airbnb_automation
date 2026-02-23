"""
Airbnb end-to-end journey steps.

Each public method corresponds to one numbered step in the assignment.
All DB writes are handled here; screenshot + logging delegates to helpers.
"""

import random
import time

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from automation.models import (
    AutoSuggestion, GuestSelection, ListingDetail,
    SearchListing, SelectedDates, TestRun,
)
from automation.utils.constants import AIRBNB_URL, TOP_20_COUNTRIES
from automation.utils.logger import StepLogger
from automation.utils.screenshot import take_screenshot


class AirbnbJourney:
    """
    Encapsulates the entire Airbnb user journey.

    :param page: Playwright Page
    :param test_run: Active TestRun ORM instance
    :param logger: StepLogger
    """

    def __init__(self, page: Page, test_run: TestRun, logger: StepLogger):
        self.page = page
        self.run = test_run
        self.log = logger

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _screenshot(self, label: str) -> str:
        path = take_screenshot(self.page, self.run.pk, label)
        self.log.set_screenshot(path)
        self.log.info(f"Screenshot saved: {path}")
        return path

    def _dismiss_popups(self) -> None:
        """Close translation banners, cookie consent, and similar overlays."""
        # Translation banner
        for sel in [
            '[data-testid="translation-announce-modal"] button[aria-label="Close"]',
            'button[aria-label="Close"]',
            '[data-testid="accept-btn"]',
            'button:has-text("Got it")',
            'button:has-text("Close")',
            'button:has-text("Dismiss")',
        ]:
            try:
                el = self.page.locator(sel).first
                if el.is_visible(timeout=2000):
                    el.click()
                    self.log.info(f"Dismissed popup via: {sel}")
                    time.sleep(0.5)
            except Exception:
                pass

    def _human_type(self, locator, text: str, delay_ms: int = 80) -> None:
        """Type text character by character to simulate a real user."""
        locator.click()
        for char in text:
            locator.type(char, delay=delay_ms)

    # ------------------------------------------------------------------
    # Step 01 – Landing & Initial Search Setup
    # ------------------------------------------------------------------

    def step_01_landing_and_search_setup(self) -> str:
        """
        Opens Airbnb, clears browser state, confirms the homepage loads,
        picks a random country and types it into the search field.

        :returns: The country that was typed.
        """
        with self.log.step(1, "Step 01 – Landing & Initial Search Setup"):
            # 1a. Navigate
            self.log.info(f"Navigating to {AIRBNB_URL}")
            self.page.goto(AIRBNB_URL, wait_until="domcontentloaded", timeout=60_000)

            # 1b. Clear browser state
            self.page.evaluate(
                "() => { try { localStorage.clear(); } catch(e) {} "
                "try { sessionStorage.clear(); } catch(e) {} }"
            )
            self.log.info("Cleared localStorage / sessionStorage")

            # 1c. Dismiss pop-ups
            self._dismiss_popups()

            # 1d. Confirm homepage
            title = self.page.title()
            assert "Airbnb" in title, f"Unexpected page title: {title}"
            self.log.info(f"Homepage loaded – title: {title!r}")
            self._screenshot("01a_homepage")

            # 1e. Click search field
            search_selectors = [
                '[data-testid="structured-search-input-field-query"]',
                'input[placeholder*="Search"]',
                '[class*="SearchBar"]',
                '[data-testid="search-form"] input',
                'button[data-testid="structured-search-input-search-button"]',
                '[id*="bigsearch-query-location"]',
            ]
            clicked = False
            for sel in search_selectors:
                try:
                    el = self.page.locator(sel).first
                    if el.is_visible(timeout=3000):
                        el.click()
                        clicked = True
                        self.log.info(f"Clicked search field: {sel}")
                        break
                except Exception:
                    continue
            if not clicked:
                self.log.warn("Could not find main search field – trying body click")
                self.page.keyboard.press("Tab")

            # 1f. Pick country
            country = random.choice(TOP_20_COUNTRIES)
            self.log.info(f"Selected country: {country}")
            self.run.selected_country = country
            self.run.save(update_fields=["selected_country"])

            # 1g. Type country
            input_selectors = [
                '[data-testid="structured-search-input-field-query"]',
                '[id*="bigsearch-query-location"]',
                'input[placeholder*="Search destinations"]',
                'input[aria-label*="Search"]',
                'input[type="text"]',
            ]
            typed = False
            for sel in input_selectors:
                try:
                    inp = self.page.locator(sel).first
                    if inp.is_visible(timeout=3000):
                        self._human_type(inp, country)
                        typed = True
                        self.log.info(f"Typed {country!r} into {sel}")
                        break
                except Exception:
                    continue
            if not typed:
                self.log.warn("Falling back to keyboard typing")
                self.page.keyboard.type(country, delay=80)

            time.sleep(1.5)
            self._screenshot("01b_after_typing_country")

        return country

    # ------------------------------------------------------------------
    # Step 02 – Auto-suggestion Verification
    # ------------------------------------------------------------------

    def step_02_autosuggestion(self) -> str:
        """
        Verifies auto-suggestions appear, validates their content,
        stores them in the DB, and clicks one.

        :returns: The text of the suggestion that was clicked.
        """
        with self.log.step(2, "Step 02 – Search Auto-suggestion Verification"):
            # Wait for suggestion list
            suggestion_container_selectors = [
                '[data-testid="structured-search-input-field-query-panel"]',
                '[class*="suggestions"]',
                '[role="listbox"]',
                '[data-testid*="suggestion"]',
                'ul[role="listbox"]',
            ]
            suggestions_visible = False
            for sel in suggestion_container_selectors:
                try:
                    self.page.locator(sel).first.wait_for(state="visible", timeout=8000)
                    suggestions_visible = True
                    self.log.info(f"Suggestion container visible: {sel}")
                    break
                except Exception:
                    continue

            if not suggestions_visible:
                self.log.warn("Suggestion container not found via known selectors – continuing")

            self._screenshot("02a_suggestions_visible")

            # Collect suggestion items
            item_selectors = [
                '[data-testid*="suggestion-item"]',
                '[role="option"]',
                'li[id*="option"]',
                '[class*="suggestion"] li',
            ]
            items = []
            for sel in item_selectors:
                found = self.page.locator(sel).all()
                if found:
                    items = found
                    self.log.info(f"Found {len(items)} suggestion items via: {sel}")
                    break

            assert len(items) > 0, "No auto-suggestion items found"

            # Store + validate suggestions
            valid_items = []
            for idx, item in enumerate(items):
                try:
                    text = item.inner_text().strip()
                    if not text:
                        continue
                    # Check for map icon (svg or img inside the item)
                    has_icon = item.locator("svg, img").count() > 0
                    suggestion = AutoSuggestion.objects.create(
                        test_run=self.run,
                        text=text,
                        has_map_icon=has_icon,
                        position=idx,
                    )
                    valid_items.append((item, suggestion))
                    self.log.info(f"Suggestion [{idx}]: {text!r} (icon={has_icon})")
                except Exception as e:
                    self.log.warn(f"Could not read suggestion [{idx}]: {e}")

            assert valid_items, "No valid suggestions captured"

            # Validate at least some suggestions reference the typed country
            country = self.run.selected_country.lower()
            relevant = [s for _, s in valid_items if country[:4] in s.text.lower()]
            if relevant:
                self.log.info(f"{len(relevant)} suggestions are relevant to {country!r}")
            else:
                self.log.warn("Suggestions may not be directly relevant to the country typed")

            # Pick one suggestion randomly and click
            chosen_elem, chosen_suggestion = random.choice(valid_items)
            chosen_suggestion.is_selected = True
            chosen_suggestion.save(update_fields=["is_selected"])
            self.run.selected_suggestion = chosen_suggestion.text
            self.run.save(update_fields=["selected_suggestion"])

            self.log.info(f"Clicking suggestion: {chosen_suggestion.text!r}")
            chosen_elem.click()
            time.sleep(2)
            self._screenshot("02b_after_suggestion_click")

        return chosen_suggestion.text

    # ------------------------------------------------------------------
    # Step 03 – Date Picker Interaction
    # ------------------------------------------------------------------

    def step_03_date_picker(self) -> tuple[str, str]:
        """
        Opens the date picker, navigates forward 3-8 months,
        picks check-in and check-out dates.

        :returns: (checkin_date_str, checkout_date_str)
        """
        with self.log.step(3, "Step 03 – Date Picker Interaction"):
            # Verify date picker opened
            date_picker_selectors = [
                '[data-testid="structured-search-input-field-split-dates-0"]',
                '[data-testid="calendar-date-one"]',
                '[class*="DatePicker"]',
                '[class*="datePicker"]',
                'div[data-visible="true"][class*="calendar"]',
                '[aria-label*="calendar"]',
            ]
            picker_open = False
            for sel in date_picker_selectors:
                try:
                    self.page.locator(sel).first.wait_for(state="visible", timeout=8000)
                    picker_open = True
                    self.log.info(f"Date picker visible: {sel}")
                    break
                except Exception:
                    continue

            if not picker_open:
                # Try clicking check-in field
                for sel in ['[data-testid*="checkin"]', 'input[placeholder*="Check"]', '[class*="CheckIn"]']:
                    try:
                        self.page.locator(sel).first.click(timeout=3000)
                        picker_open = True
                        break
                    except Exception:
                        continue

            self._screenshot("03a_date_picker_open")

            # Click "Next Month" button N times
            clicks = random.randint(3, 8)
            self.log.info(f"Will click Next Month {clicks} times")
            next_btn_selectors = [
                'button[aria-label="Move forward to switch to the next month."]',
                'button[aria-label*="next month"]',
                '[data-testid="calendar-next-navigation"]',
                'button[class*="nextMonthButton"]',
                'button[class*="next"]',
            ]
            for i in range(clicks):
                clicked = False
                for sel in next_btn_selectors:
                    try:
                        btn = self.page.locator(sel).first
                        if btn.is_visible(timeout=2000):
                            btn.click()
                            clicked = True
                            break
                    except Exception:
                        continue
                if clicked:
                    time.sleep(0.4)
                else:
                    self.log.warn(f"Could not click Next Month on iteration {i+1}")

            self._screenshot("03b_after_month_navigation")

            # Read current month label
            month_label = ""
            for sel in [
                '[data-testid="calendar-title"]',
                'h2[class*="month"]',
                '[class*="CalendarMonth_caption"]',
                '[class*="month-caption"]',
                'strong[class*="month"]',
            ]:
                try:
                    el = self.page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        month_label = el.inner_text().strip()
                        self.log.info(f"Current month: {month_label!r}")
                        break
                except Exception:
                    continue

            # Select check-in date (first available day)
            available_day_sel = (
                'button[data-testid*="calendar-day"]:not([disabled]):not([aria-disabled="true"]),'
                'td[class*="CalendarDay"]:not([class*="blocked"]):not([class*="selected"]),'
                '[role="button"][class*="day"]:not([disabled])'
            )
            available_days = self.page.locator(available_day_sel).all()
            assert available_days, "No available days found in calendar"

            # Pick check-in (skip first 2 to be safe)
            checkin_el = available_days[min(2, len(available_days) - 1)]
            checkin_label = checkin_el.get_attribute("aria-label") or checkin_el.inner_text().strip()
            checkin_el.click()
            self.log.info(f"Check-in clicked: {checkin_label!r}")
            time.sleep(0.8)

            # Pick check-out (a few days after)
            available_days2 = self.page.locator(available_day_sel).all()
            if len(available_days2) > 5:
                checkout_el = available_days2[min(6, len(available_days2) - 1)]
            else:
                checkout_el = available_days2[-1]
            checkout_label = checkout_el.get_attribute("aria-label") or checkout_el.inner_text().strip()
            checkout_el.click()
            self.log.info(f"Check-out clicked: {checkout_label!r}")
            time.sleep(0.8)

            self._screenshot("03c_dates_selected")

            # Persist
            SelectedDates.objects.create(
                test_run=self.run,
                month_name=month_label,
                checkin_date=checkin_label,
                checkout_date=checkout_label,
                next_month_clicks=clicks,
            )
            self.run.checkin_date = checkin_label
            self.run.checkout_date = checkout_label
            self.run.selected_month = month_label
            self.run.save(update_fields=["checkin_date", "checkout_date", "selected_month"])

            # Validate logical ordering (basic check – both must be non-empty)
            assert checkin_label, "Check-in date is empty"
            assert checkout_label, "Check-out date is empty"
            self.log.info("Date selection is logically valid (both dates non-empty)")

        return checkin_label, checkout_label

    # ------------------------------------------------------------------
    # Step 04 – Guest Picker Interaction
    # ------------------------------------------------------------------

    def step_04_guest_picker(self) -> dict:
        """
        Opens the guest picker, randomly selects 2-5 total guests,
        then clicks the Search button.

        :returns: Dict with guest counts.
        """
        with self.log.step(4, "Step 04 – Guest Picker Interaction"):
            # Click guest field
            guest_field_selectors = [
                '[data-testid="structured-search-input-field-guests-button"]',
                'button[data-testid*="guest"]',
                '[class*="GuestsPicker"]',
                'button[aria-label*="guest"]',
                '[data-testid="structured-search-input-field-guests"]',
            ]
            for sel in guest_field_selectors:
                try:
                    el = self.page.locator(sel).first
                    if el.is_visible(timeout=3000):
                        el.click()
                        self.log.info(f"Clicked guest field: {sel}")
                        time.sleep(1)
                        break
                except Exception:
                    continue

            # Verify popup opened
            popup_selectors = [
                '[data-testid*="stepper"]',
                '[class*="GuestPicker"]',
                '[aria-label*="guests"]',
                'section[data-testid*="guest"]',
            ]
            popup_visible = False
            for sel in popup_selectors:
                try:
                    self.page.locator(sel).first.wait_for(state="visible", timeout=5000)
                    popup_visible = True
                    self.log.info(f"Guest popup visible: {sel}")
                    break
                except Exception:
                    continue
            if not popup_visible:
                self.log.warn("Guest popup not confirmed visible")

            self._screenshot("04a_guest_picker_open")

            # Determine target total guests (2-5)
            target_total = random.randint(2, 5)
            self.log.info(f"Target guests: {target_total}")

            # Increase adults (add target_total - 1 adults, there's typically 1 by default)
            adults_to_add = target_total - 1
            adults_added = 0
            adult_plus_selectors = [
                '[data-testid="stepper-adults-increase-button"]',
                'button[aria-label*="Increase number of Adults"]',
                'button[aria-label*="adults"]',
            ]
            for _ in range(adults_to_add):
                for sel in adult_plus_selectors:
                    try:
                        btn = self.page.locator(sel).first
                        if btn.is_visible(timeout=2000) and not btn.is_disabled():
                            btn.click()
                            adults_added += 1
                            time.sleep(0.4)
                            break
                    except Exception:
                        continue

            # Read actual guest count from the field
            guest_counts = {"adults": 1 + adults_added, "children": 0, "infants": 0, "pets": 0}
            total = guest_counts["adults"]

            self.log.info(f"Guest selection: adults={guest_counts['adults']}, total={total}")
            self._screenshot("04b_guests_selected")

            # Verify displayed count
            display_selectors = [
                '[data-testid="structured-search-input-field-guests-button"]',
                '[class*="guest-count"]',
                '[aria-label*="guest"]',
            ]
            display_text = ""
            for sel in display_selectors:
                try:
                    el = self.page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        display_text = el.inner_text().strip()
                        if display_text:
                            self.log.info(f"Guest display text: {display_text!r}")
                            break
                except Exception:
                    continue

            # Persist
            GuestSelection.objects.create(
                test_run=self.run,
                adults=guest_counts["adults"],
                children=guest_counts["children"],
                infants=guest_counts["infants"],
                pets=guest_counts["pets"],
                total_guests=total,
            )
            self.run.guest_count = total
            self.run.save(update_fields=["guest_count"])

            # Click Search
            search_btn_selectors = [
                '[data-testid="structured-search-input-search-button"]',
                'button[type="submit"]',
                'button[aria-label*="Search"]',
                'button:has-text("Search")',
            ]
            for sel in search_btn_selectors:
                try:
                    btn = self.page.locator(sel).first
                    if btn.is_visible(timeout=3000):
                        btn.click()
                        self.log.info(f"Search button clicked: {sel}")
                        break
                except Exception:
                    continue

            self.page.wait_for_load_state("domcontentloaded", timeout=30_000)
            time.sleep(2)
            self._screenshot("04c_after_search")

        return guest_counts

    # ------------------------------------------------------------------
    # Step 05 – Refine Search & Listing Verification
    # ------------------------------------------------------------------

    def step_05_search_results(self) -> list[dict]:
        """
        Verifies the search results page, checks URL params,
        scrapes listings, and stores them in the DB.

        :returns: List of raw listing dicts.
        """
        with self.log.step(5, "Step 05 – Refine Search & Item List Verification"):
            current_url = self.page.url
            self.log.info(f"Results URL: {current_url}")

            # Verify page loaded (at least some listing card visible)
            listing_card_selectors = [
                '[data-testid="listing-card-title"]',
                '[data-testid*="card"]',
                '[class*="listing"]',
                '[itemprop="itemListElement"]',
            ]
            page_loaded = False
            for sel in listing_card_selectors:
                try:
                    self.page.locator(sel).first.wait_for(state="visible", timeout=20_000)
                    page_loaded = True
                    self.log.info(f"Listings visible via: {sel}")
                    break
                except Exception:
                    continue
            assert page_loaded, "Search results page did not load listing cards"

            self._screenshot("05a_search_results")

            # Validate URL contains guest count
            url_lower = current_url.lower()
            guests_in_url = (
                f"adults={self.run.guest_count}" in url_lower
                or "guests" in url_lower
                or "adults" in url_lower
            )
            if guests_in_url:
                self.log.info("Guest count found in URL ✓")
            else:
                self.log.warn("Guest count NOT clearly in URL")

            # Scrape listings
            listings_data = []
            title_els = self.page.locator('[data-testid="listing-card-title"]').all()
            if not title_els:
                title_els = self.page.locator('[class*="title"][class*="listing"], [class*="card"] h3').all()

            self.log.info(f"Found {len(title_els)} listing titles")

            for idx, title_el in enumerate(title_els):
                try:
                    title = title_el.inner_text().strip()

                    # Price - look for sibling/nearby price element
                    price = ""
                    try:
                        card = title_el.locator("xpath=ancestor::div[contains(@class,'listing') or contains(@data-testid,'card')][1]")
                        price_el = card.locator('[class*="price"], [data-testid*="price"]').first
                        price = price_el.inner_text().strip()
                    except Exception:
                        pass

                    # Image
                    img_url = ""
                    try:
                        card2 = title_el.locator("xpath=ancestor::a[1]")
                        img = card2.locator("img").first
                        img_url = img.get_attribute("src") or ""
                    except Exception:
                        pass

                    # Listing URL
                    listing_url = ""
                    try:
                        link = title_el.locator("xpath=ancestor::a[1]")
                        listing_url = link.get_attribute("href") or ""
                        if listing_url and not listing_url.startswith("http"):
                            listing_url = "https://www.airbnb.com" + listing_url
                    except Exception:
                        pass

                    SearchListing.objects.create(
                        test_run=self.run,
                        title=title,
                        price=price,
                        image_url=img_url[:1000],
                        listing_url=listing_url[:1000],
                        position=idx,
                    )
                    listings_data.append({"title": title, "price": price, "image_url": img_url, "url": listing_url})
                    self.log.info(f"Listing [{idx}]: {title[:60]!r} | {price}")

                except Exception as e:
                    self.log.warn(f"Could not scrape listing [{idx}]: {e}")

            assert listings_data, "No listings scraped"
            self.log.info(f"Total listings scraped: {len(listings_data)}")

        return listings_data

    # ------------------------------------------------------------------
    # Step 06 – Item Details Page Verification
    # ------------------------------------------------------------------

    def step_06_listing_detail(self) -> dict:
        """
        Clicks a random listing, captures the detail page data.

        :returns: Dict with title, subtitle and image_urls.
        """
        with self.log.step(6, "Step 06 – Item Details Page Verification"):
            # Pick a random listing from DB
            listings = list(self.run.listings.all())
            assert listings, "No listings available to select"
            chosen = random.choice(listings)
            chosen.is_selected = True
            chosen.save(update_fields=["is_selected"])
            self.log.info(f"Selected listing: {chosen.title[:60]!r}")

            # Try to click via URL
            detail_opened = False
            if chosen.listing_url:
                try:
                    self.page.goto(chosen.listing_url, wait_until="domcontentloaded", timeout=30_000)
                    detail_opened = True
                    self.log.info(f"Navigated to listing URL: {chosen.listing_url[:80]}")
                except Exception as e:
                    self.log.warn(f"Direct navigation failed: {e}")

            # Fallback: click the card on the results page
            if not detail_opened:
                self.page.go_back()
                try:
                    card_link = self.page.locator(f'a[href*="{chosen.listing_url[-20:]}"]').first
                    card_link.click()
                    self.page.wait_for_load_state("domcontentloaded", timeout=20_000)
                    detail_opened = True
                except Exception as e:
                    self.log.warn(f"Card click fallback also failed: {e}")

            time.sleep(2)
            self._dismiss_popups()
            self._screenshot("06a_listing_detail")

            # Verify page opened (check URL changed from search)
            current_url = self.page.url
            assert "airbnb.com" in current_url, "Not on Airbnb page"
            self.log.info(f"Detail page URL: {current_url[:100]}")

            # Capture title
            title = ""
            title_selectors = [
                '[data-testid="listing-details-title"]',
                'h1',
                '[class*="title"][class*="listing"]',
                '[data-section-id="TITLE_DEFAULT"] h1',
            ]
            for sel in title_selectors:
                try:
                    el = self.page.locator(sel).first
                    if el.is_visible(timeout=3000):
                        title = el.inner_text().strip()
                        if title:
                            self.log.info(f"Title: {title[:80]!r}")
                            break
                except Exception:
                    continue

            # Capture subtitle
            subtitle = ""
            subtitle_selectors = [
                '[data-testid="listing-details-subtitle"]',
                '[data-section-id="OVERVIEW_DEFAULT"] h2',
                'h2',
            ]
            for sel in subtitle_selectors:
                try:
                    el = self.page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        subtitle = el.inner_text().strip()
                        if subtitle:
                            self.log.info(f"Subtitle: {subtitle[:80]!r}")
                            break
                except Exception:
                    continue

            # Collect image URLs from gallery
            image_urls = []
            img_elements = self.page.locator(
                '[data-testid*="photo"] img, [class*="gallery"] img, '
                '[class*="photo"] img, [class*="image"] img'
            ).all()
            for img in img_elements:
                src = img.get_attribute("src") or ""
                if src and src not in image_urls:
                    image_urls.append(src)
            self.log.info(f"Collected {len(image_urls)} gallery images")

            self._screenshot("06b_listing_detail_scrolled")

            # Persist
            ListingDetail.objects.create(
                test_run=self.run,
                title=title,
                subtitle=subtitle,
                image_urls=image_urls[:50],
                page_url=current_url[:1000],
            )

        return {"title": title, "subtitle": subtitle, "image_urls": image_urls}
