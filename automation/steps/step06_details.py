"""
Step 06: Item Details Page Verification
"""
import random
import time
import logging

from automation.services.browser_service import BrowserService
from automation.services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class Step06ListingDetails:
    STEP_NAME = "Item Details Page Verification"

    def __init__(self, browser: BrowserService, db: DatabaseService, persist_to_db: bool = True):
        self.browser = browser
        self.db = db
        self.persist_to_db = persist_to_db

    def run(self, listings: list) -> dict:
        logger.info(f"=== {self.STEP_NAME} ===")

        if not listings:
            logger.warning("No listings to select from")
            return {}

        listing = random.choice(listings)
        logger.info(f"Selected: {listing.get('title', 'N/A')[:60]}")

        self._open_listing(listing)
        time.sleep(1.2)

        current_url = self.browser.get_current_url()
        self.browser.take_screenshot("step06_listing_details")

        page_ok = '/rooms/' in current_url
        self.db.save_test_result(
            test_case="Listing Details Page Load",
            url=current_url,
            passed=page_ok,
            should_be="Listing details page to open with /rooms/ in URL and full listing content",
            found=f"Page {'loaded' if page_ok else 'did not load'}: {current_url[:100]}"
        )

        title = self._get_title()
        subtitle = self._get_subtitle()
        self.browser.take_screenshot("step06_title_subtitle")

        self.db.save_test_result(
            test_case="Listing Title and Subtitle Capture",
            url=current_url,
            passed=bool(title),
            should_be="Listing page to have h1 title and h2 subtitle with location details",
            found=f"Title (h1): '{title[:80]}' | Subtitle (h2): '{subtitle[:80]}'"
        )

        image_urls = self._collect_gallery_images()
        self.browser.take_screenshot("step06_gallery")

        self.db.save_test_result(
            test_case="Listing Gallery Image URLs Collection",
            url=current_url,
            passed=len(image_urls) > 0,
            should_be="Gallery to have multiple image URLs from listing photo section",
            found=f"Collected {len(image_urls)} image URLs from listing gallery"
        )

        result = {
            'title': title,
            'subtitle': subtitle,
            'image_urls': image_urls,
            'url': current_url,
        }
        self._persist(result)
        return result

    def _open_listing(self, listing: dict) -> bool:
        listing_url = listing.get('listing_url', '')

        if listing_url and 'airbnb.com/rooms/' in listing_url:
            self.browser.page.goto(listing_url, wait_until='domcontentloaded', timeout=10000)
            return '/rooms/' in self.browser.get_current_url()

        if listing_url and listing_url.startswith('/rooms/'):
            self.browser.page.goto(f"https://www.airbnb.com{listing_url}", wait_until='domcontentloaded', timeout=10000)
            return '/rooms/' in self.browser.get_current_url()

        links = self.browser.safe_find_all("//a[contains(@href,'/rooms/')]")
        if links:
            try:
                href = links[0].get_attribute('href')
                if href:
                    if href.startswith('/'):
                        href = f"https://www.airbnb.com{href}"
                    self.browser.page.goto(href, wait_until='domcontentloaded', timeout=10000)
                    return '/rooms/' in self.browser.get_current_url()
            except Exception as e:
                logger.debug(f"Listing open fallback failed: {e}")

        # Codegen-inspired fallback from provided workflow snippet.
        try:
            self.browser.page.get_by_role("button", name="Close").click(timeout=1500)
        except Exception:
            pass
        try:
            group = self.browser.page.get_by_role("group").filter(
                has_text="Guest favoriteGuest favoriteApartment in DhakaContemporary Spacious Urban"
            )
            group.get_by_label("Apartment in Dhaka", exact=True).click(timeout=2500)
            time.sleep(0.7)
            return '/rooms/' in self.browser.get_current_url()
        except Exception:
            pass

        return False

    def _get_title(self) -> str:
        selectors = [
            "h1",
            "//h1",
            "//section//h1",
        ]
        for sel in selectors:
            el = self.browser.safe_find(sel)
            if el:
                try:
                    text = (el.text_content() or '').strip()
                    if text and len(text) > 2:
                        return text
                except Exception:
                    continue
        return ''

    def _get_subtitle(self) -> str:
        selectors = [
            "//h1/following::h2[1]",
            "//div[@data-section-id='OVERVIEW_DEFAULT_V2']//h2",
            "//div[@data-plugin-in-point-id='OVERVIEW_DEFAULT_V2']//h2",
            "(//h2)[1]",
            "h2",
        ]
        for sel in selectors:
            el = self.browser.safe_find(sel)
            if el:
                try:
                    text = (el.text_content() or '').strip()
                    if text and len(text) > 2:
                        return text
                except Exception:
                    continue
        return ''

    def _collect_gallery_images(self) -> list:
        image_urls = set()

        gallery_selectors = [
            "//div[contains(@data-section-id,'HERO') or contains(@data-plugin-in-point-id,'HERO')]//img",
            "//div[@data-section-id='HERO_DEFAULT']//img",
            "//button[contains(@aria-label,'photo') or contains(@aria-label,'Photo')]//img",
            "//div[.//button[contains(text(),'Show all photos')]]//img",
            "(//div[contains(@class,'section')])[1]//img",
        ]

        for sel in gallery_selectors:
            imgs = self.browser.safe_find_all(sel)
            for img in imgs:
                try:
                    src = (
                        img.get_attribute('src') or
                        img.get_attribute('data-original-uri') or
                        img.get_attribute('data-src') or ''
                    )
                    if src and not src.startswith('data:'):
                        image_urls.add(src)
                except Exception:
                    continue

        if not image_urls:
            all_imgs = self.browser.safe_find_all("img")
            for img in all_imgs:
                try:
                    src = img.get_attribute('src') or ''
                    if src and 'http' in src:
                        image_urls.add(src)
                except Exception:
                    continue

        logger.info(f"Collected {len(image_urls)} gallery images")
        return list(image_urls)

    def _persist(self, result: dict):
        if not self.persist_to_db:
            return

        from automation.models import ListingData
        try:
            title = result.get('title', '')
            imgs = result.get('image_urls', [])
            if title:
                ListingData.objects.update_or_create(
                    listing_url=result.get('url', ''),
                    defaults={
                        'title': title,
                        'price': '',
                        'image_url': imgs[0] if imgs else '',
                    }
                )
                logger.info(f"Saved listing details: {title[:60]}")
        except Exception as e:
            logger.warning(f"Failed to persist listing details: {e}")
