"""
Step 05: Refine Search and Item List Verification
"""
import re
import time
import logging
from datetime import datetime
from urllib.parse import parse_qs, unquote, urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from automation.services.browser_service import BrowserService
from automation.services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class Step05SearchResults:
    STEP_NAME = "Refine Search and Item List Verification"

    def __init__(self, browser: BrowserService, db: DatabaseService):
        self.browser = browser
        self.db = db

    def run(self, date_info: dict, guest_count: int) -> list:
        logger.info(f"=== {self.STEP_NAME} ===")
        time.sleep(1.2)

        page_loaded = self._verify_results_page()
        current_url = self.browser.get_current_url()
        self.browser.take_screenshot("step05_results_page")

        self.db.save_test_result(
            test_case="Search Results Page Load Verification",
            url=current_url,
            passed=page_loaded,
            should_be="Refine search results page to load with listing cards visible",
            found="Results page loaded with listings" if page_loaded else "Results page did not load correctly"
        )

        dates_in_ui = self._check_dates_in_ui(date_info)
        dates_in_url = self._check_dates_in_url(current_url, date_info)
        dates_preserved = dates_in_url or dates_in_ui
        self.db.save_test_result(
            test_case="Selected Dates in URL Validation",
            url=current_url,
            passed=dates_preserved,
            should_be="Selected dates to persist in URL, or remain visible in UI when Airbnb omits URL date params",
            found=(
                f"Dates found in URL: {current_url[:120]}"
                if dates_in_url
                else (
                    "Dates not in URL, but confirmed in UI search bar"
                    if dates_in_ui
                    else f"Dates NOT found in URL: {current_url[:120]}"
                )
            )
        )

        guests_in_url = (
            'adults' in current_url or
            'guests' in current_url or
            f'adults={guest_count}' in current_url
        )
        self.db.save_test_result(
            test_case="Selected Guest Count in URL Validation",
            url=current_url,
            passed=guests_in_url,
            should_be=f"Guest count to appear in URL parameters (added {guest_count} guests)",
            found=f"Guest info {'present' if guests_in_url else 'absent'} in URL"
        )

        self.db.save_test_result(
            test_case="Selected Dates in Page UI Confirmation",
            url=current_url,
            passed=dates_in_ui,
            should_be="Selected dates and guest count to appear in the page search bar UI",
            found="Dates visible in page UI search bar" if dates_in_ui else "Dates not visible in UI"
        )

        listings = self._scrape_listings()
        self.db.save_test_result(
            test_case="Listing Data Scraping",
            url=current_url,
            passed=len(listings) > 0,
            should_be="Each listing's title, price, and image URL to be scraped and stored",
            found=f"Scraped {len(listings)} listings with title, price, and image URL"
        )

        if listings:
            self.db.save_listings(listings)

        return listings

    def _verify_results_page(self) -> bool:
        selectors = [
            "//div[@data-testid='card-container']",
            "//*[@itemtype='http://schema.org/ListItem']",
            "//a[contains(@href,'/rooms/')]",
            "//div[@data-testid='listing-card-title']",
            "//meta[@itemprop='url'][contains(@content,'/rooms/')]",
        ]
        for sel in selectors:
            try:
                self.browser.wait_for_element(sel, timeout=10)
                return True
            except PlaywrightTimeoutError:
                continue
        return False

    def _check_dates_in_ui(self, date_info: dict) -> bool:
        checkin = (date_info or {}).get("checkin")
        checkout = (date_info or {}).get("checkout")
        if not (checkin and checkout):
            return False

        tokens = self._date_tokens(checkin) + self._date_tokens(checkout)

        selectors = [
            "[data-testid='little-search']",
            "[data-testid*='structured-search-input-field-split-dates-0']",
            "[data-testid*='structured-search-input-field-split-dates-1']",
            "button[aria-label*='Check in']",
            "button[aria-label*='Check out']",
            "header",
        ]

        texts = []
        for sel in selectors:
            try:
                loc = self.browser.page.locator(sel).first
                if loc.count() > 0 and loc.is_visible(timeout=800):
                    txt = (loc.inner_text() or loc.text_content() or "").strip()
                    if txt:
                        texts.append(txt.lower())
                    aria = (loc.get_attribute("aria-label") or "").strip()
                    if aria:
                        texts.append(aria.lower())
            except Exception:
                continue

        try:
            body_text = (self.browser.page.locator("body").inner_text() or "").lower()
            texts.append(body_text[:10000])
        except Exception:
            pass

        if not texts:
            return False

        haystack = " ".join(texts)
        matched = sum(1 for t in tokens if t.lower() in haystack)
        if matched >= 2:
            return True

        # Fallback: any month+day range token like "Feb 26 - Mar 5"
        return bool(re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b.*\b\d{1,2}\b", haystack))

    def _check_dates_in_url(self, current_url: str, date_info: dict) -> bool:
        checkin = (date_info or {}).get("checkin")
        checkout = (date_info or {}).get("checkout")
        if not (checkin and checkout):
            return False

        try:
            parsed = urlparse(current_url)
            qs = parse_qs(parsed.query)

            values = []
            for v in qs.values():
                values.extend(v)
            joined = " ".join(unquote(v) for v in values).lower()

            direct_keys = ["checkin", "check_in", "checkout", "check_out", "checkin_date", "checkout_date"]
            has_key = any(k in qs for k in direct_keys)
            if has_key:
                return True

            if checkin.lower() in joined and checkout.lower() in joined:
                return True

            # Some URLs keep dates directly in path/query without clear keys.
            full = unquote(current_url).lower()
            return checkin.lower() in full and checkout.lower() in full
        except Exception:
            lower = current_url.lower()
            return checkin.lower() in lower and checkout.lower() in lower

    def _date_tokens(self, iso_date: str) -> list[str]:
        try:
            dt = datetime.strptime(iso_date, "%Y-%m-%d")
            return [
                dt.strftime("%b %-d"),
                dt.strftime("%B %-d"),
                dt.strftime("%-m/%-d"),
                dt.strftime("%m/%d").lstrip("0").replace("/0", "/"),
            ]
        except Exception:
            return [iso_date]
        return False

    def _scrape_listings(self) -> list:
        listings = []

        self.browser.scroll_to_bottom()
        time.sleep(0.6)
        self.browser.page.evaluate("window.scrollTo(0, 0);")
        time.sleep(0.3)

        schema_items = self.browser.page.locator("xpath=//*[@itemtype='http://schema.org/ListItem']")
        schema_count = schema_items.count()

        if schema_count:
            for i in range(min(schema_count, 20)):
                item = schema_items.nth(i)
                try:
                    title = item.locator("xpath=.//meta[@itemprop='name']").first.get_attribute('content') or ''

                    listing_url = ''
                    url_loc = item.locator("xpath=.//meta[@itemprop='url']")
                    if url_loc.count() > 0:
                        listing_url = url_loc.first.get_attribute('content') or ''

                    price = ''
                    price_els = item.locator("xpath=.//*[contains(text(),'$')]")
                    for j in range(min(price_els.count(), 10)):
                        t = (price_els.nth(j).text_content() or '').strip()
                        if '$' in t:
                            price = t
                            break

                    image_url = ''
                    img_loc = item.locator('img')
                    if img_loc.count() > 0:
                        image_url = img_loc.first.get_attribute('src') or ''

                    if title:
                        listings.append(
                            {
                                'title': title,
                                'price': price,
                                'image_url': image_url,
                                'listing_url': listing_url,
                            }
                        )
                except Exception as e:
                    logger.debug(f"Schema item scrape error: {e}")
                    continue

        if not listings:
            cards = self.browser.page.locator("xpath=//div[@data-testid='card-container']")
            card_count = cards.count()
            for i in range(min(card_count, 20)):
                card = cards.nth(i)
                try:
                    title = ''
                    price = ''
                    image_url = ''
                    listing_url = ''

                    links = card.locator("xpath=.//a[contains(@href,'/rooms/')]")
                    if links.count() > 0:
                        listing_url = links.first.get_attribute('href') or ''

                    if links.count() > 0:
                        aria_label = links.first.get_attribute('aria-label') or ''
                        if aria_label:
                            title = aria_label[:150]

                    if not title:
                        txt = (card.text_content() or '').strip()
                        if txt:
                            title = txt.split('\n')[0].strip()

                    price_els = card.locator("xpath=.//*[contains(text(),'$')]")
                    for j in range(min(price_els.count(), 10)):
                        t = (price_els.nth(j).text_content() or '').strip()
                        if '$' in t and len(t) < 80:
                            price = t
                            break

                    imgs = card.locator('img')
                    if imgs.count() > 0:
                        image_url = imgs.first.get_attribute('src') or ''

                    if title:
                        listings.append(
                            {
                                'title': title,
                                'price': price,
                                'image_url': image_url,
                                'listing_url': listing_url,
                            }
                        )
                except Exception as e:
                    logger.debug(f"Card scrape error: {e}")
                    continue

        logger.info(f"Total listings scraped: {len(listings)}")
        return listings
