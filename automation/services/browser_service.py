"""
Browser Service: Manages Playwright browser lifecycle and common browser operations.
"""
import os
import time
import logging
from datetime import datetime

from django.conf import settings
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


class BrowserService:
    """
    Handles browser initialization, screenshots, and common interactions.
    Implements context manager protocol for safe resource management.
    """

    DEFAULT_WAIT = 3
    SLOW_WAIT = 3

    def __init__(self, mobile: bool = False, headless: bool = False, screenshots_enabled: bool = True, keep_browser_open: bool = False):
        self.mobile = mobile
        self.headless = headless
        self.screenshots_enabled = bool(screenshots_enabled)
        self.keep_browser_open = bool(keep_browser_open)

        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        self.console_logs = []
        self.network_logs = []

        self.screenshot_dir = settings.SCREENSHOT_DIR
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def __enter__(self):
        self._init_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.keep_browser_open:
            logger.info("Browser kept open (--keep-browser-open flag set)")
            return
        try:
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            logger.debug(f"Browser cleanup warning: {e}")

    def _init_browser(self):
                """Initialize and configure Playwright Chromium."""
                self.playwright = sync_playwright().start()

                self.browser = self.playwright.chromium.launch(
                        headless=self.headless,
                        args=[
                                '--no-sandbox',
                                '--disable-dev-shm-usage',
                                '--disable-gpu',
                                '--disable-blink-features=AutomationControlled',
                        ],
                )

                context_args = {
                        'viewport': {'width': 1920, 'height': 1080},
                }

                if self.mobile:
                        context_args.update(
                                {
                                        'viewport': {'width': 390, 'height': 844},
                                        'device_scale_factor': 3.0,
                                        'is_mobile': True,
                                        'has_touch': True,
                                        'user_agent': (
                                                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                                                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                                                "Version/16.0 Mobile/15E148 Safari/604.1"
                                        ),
                                }
                        )

                self.context = self.browser.new_context(**context_args)

                # Mask webdriver property
                self.context.add_init_script(
                        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
                )

                # Auto-close common modal/popups as soon as they appear in the DOM.
                # This injects a MutationObserver into every page in the context to
                # attempt to click close/dismiss buttons on dialogs and modals.
                try:
                        self.context.add_init_script(
                                """
                                (() => {
                                    const CLOSE_TEXTS = ['Close','Dismiss','Accept','Got it','No thanks','Not now','×','×'];
                                    const modalSelectors = ['[role="dialog"]', '.modal', '.dialog', '[data-testid*="modal"]', '[data-testid*="dialog"]'];

                                    function findCloseButton(root) {
                                        const buttons = Array.from((root || document).querySelectorAll('button, [role=button], a'));
                                        for (const b of buttons) {
                                            try {
                                                const txt = (b.innerText || b.textContent || '').trim();
                                                const aria = (b.getAttribute && (b.getAttribute('aria-label') || '') ) || '';
                                                if (!txt && !aria) continue;
                                                for (const t of CLOSE_TEXTS) {
                                                    if (txt.indexOf(t) !== -1 || aria.indexOf(t) !== -1) return b;
                                                }
                                            } catch (e) {}
                                        }
                                        // fallback: common attributes
                                        const byAttr = (root || document).querySelector('[aria-label="Close"], [aria-label*="close" i], .close, button.close');
                                        if (byAttr) return byAttr;
                                        return null;
                                    }

                                    function closeIfModal(node) {
                                        try {
                                            if (!(node instanceof HTMLElement)) return;
                                            let isModal = false;
                                            for (const sel of modalSelectors) {
                                                try {
                                                    if (node.matches && node.matches(sel)) { isModal = true; break; }
                                                } catch (e) {}
                                                try {
                                                    if (node.querySelector && node.querySelector(sel)) { isModal = true; break; }
                                                } catch (e) {}
                                            }
                                            if (!isModal) return;
                                            const btn = findCloseButton(node) || findCloseButton(node.parentElement) || findCloseButton(document);
                                            if (btn) {
                                                try { btn.click(); } catch(e) {}
                                            }
                                        } catch (e) {}
                                    }

                                    const observer = new MutationObserver((mutations) => {
                                        for (const m of mutations) {
                                            for (const n of m.addedNodes) {
                                                try { closeIfModal(n); } catch (e) {}
                                            }
                                        }
                                    });

                                    try {
                                        observer.observe(document, { childList: true, subtree: true });
                                    } catch (e) {}

                                    // initial scan
                                    try {
                                        const nodes = Array.from(document.querySelectorAll(modalSelectors.join(',')));
                                        for (const n of nodes) { try { closeIfModal(n); } catch (e) {} }
                                    } catch (e) {}
                                })();
                                """
                        )
                except Exception:
                        # add_init_script may not be supported in all contexts; ignore if it fails
                        pass

                self.context.on("response", self._on_response)

                self.page = self.context.new_page()
                self.page.on("console", self._on_console)

    def _on_console(self, msg):
        self.console_logs.append(
            {
                'level': (msg.type or 'info').upper(),
                'message': msg.text,
                'source': msg.location.get('url', '') if msg.location else '',
            }
        )

    def _on_response(self, response):
        request = response.request
        self.network_logs.append(
            {
                'url': response.url,
                'method': request.method,
                'status_code': response.status,
                'resource_type': request.resource_type,
            }
        )

    @staticmethod
    def _selector(selector: str) -> str:
        selector = selector.strip()
        if selector.startswith('xpath='):
            return selector
        if selector.startswith('//') or selector.startswith('(//') or selector.startswith('.//'):
            return f'xpath={selector}'
        return selector

    def wait_for_element(self, selector: str, timeout: int = None):
        """Wait until an element is visible and return it."""
        timeout_sec = min(timeout or self.DEFAULT_WAIT, 3)
        timeout_ms = int(timeout_sec * 1000)
        loc = self.page.locator(self._selector(selector)).first
        loc.wait_for(state='visible', timeout=timeout_ms)
        return loc

    def wait_for_clickable(self, selector: str, timeout: int = None):
        """Wait until an element is visible and enabled and return it."""
        timeout_sec = min(timeout or self.DEFAULT_WAIT, 3)
        loc = self.wait_for_element(selector, timeout=timeout_sec)

        start = time.time()
        while time.time() - start < timeout_sec:
            try:
                if loc.is_enabled():
                    return loc
            except Exception:
                pass
            time.sleep(0.1)

        return loc

    def safe_find(self, selector: str):
        """Find first element without raising exception if not found."""
        try:
            loc = self.page.locator(self._selector(selector))
            if loc.count() > 0:
                return loc.first
        except Exception:
            pass
        return None

    def safe_find_all(self, selector: str) -> list:
        """Find all elements without raising exception."""
        try:
            loc = self.page.locator(self._selector(selector))
            return [loc.nth(i) for i in range(loc.count())]
        except Exception:
            return []

    def take_screenshot(self, step_name: str) -> str:
        """Take a full-page screenshot and save to screenshots directory."""
        if not self.screenshots_enabled:
            return None

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{step_name}_{timestamp}.png"
        filepath = os.path.join(self.screenshot_dir, filename)
        try:
            self.page.screenshot(path=filepath, full_page=True)
            logger.info(f"Screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            logger.debug(f"Failed to take screenshot: {e}")
            return None

    def dismiss_popups(self):
        """Try to close common popup/cookie/modal dialogs."""
        popup_selectors = [
            "//button[contains(text(),'Accept')]",
            "//button[contains(text(),'Close')]",
            "//button[@aria-label='Close']",
            "//button[contains(@class,'close')]",
            "//div[@role='dialog']//button[1]",
        ]

        for selector in popup_selectors:
            try:
                btn = self.page.locator(self._selector(selector)).first
                if btn.is_visible(timeout=700):
                    btn.click(timeout=700)
                    logger.info(f"Dismissed popup: {selector}")
                    time.sleep(0.2)
            except Exception:
                continue

    def clear_browser_data(self):
        """Clear cache, cookies, and storage."""
        try:
            cdp = self.context.new_cdp_session(self.page)
            cdp.send("Network.enable")
            cdp.send("Network.clearBrowserCache")
            cdp.send("Network.clearBrowserCookies")
        except Exception:
            # CDP may be unavailable depending on browser/context; continue with storage cleanup.
            pass

        self.context.clear_cookies()

        # localStorage/sessionStorage may be blocked on about:blank or restricted origins.
        try:
            self.page.evaluate("window.localStorage.clear();")
        except Exception:
            pass

        try:
            self.page.evaluate("window.sessionStorage.clear();")
        except Exception:
            pass

        logger.info("Browser data cleared (cache, cookies, localStorage, sessionStorage)")

    def slow_type(self, element, text: str, delay: float = 0.04, clear_first: bool = False):
        """Type text character by character to simulate real user input."""
        if clear_first:
            try:
                element.fill('')
            except Exception:
                pass
        element.type(text, delay=int(delay * 1000))

    def get_current_url(self) -> str:
        """Return current page URL."""
        return self.page.url

    def get_console_logs(self) -> list:
        """Retrieve browser console logs."""
        return list(self.console_logs)

    def get_network_logs(self) -> list:
        """Retrieve network logs captured from response events."""
        return list(self.network_logs)

    def scroll_to_bottom(self):
        """Scroll the page to the bottom."""
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.4)
