"""Browser / context factory."""

from django.conf import settings
from playwright.sync_api import sync_playwright, BrowserContext, Page

from .constants import DESKTOP_VIEWPORT, MOBILE_DEVICE


class BrowserManager:
    """
    Wraps Playwright lifecycle.

    Usage::

        with BrowserManager() as bm:
            page = bm.page
            page.goto("https://www.airbnb.com/")
    """

    def __init__(self, mobile: bool = False):
        self._mobile = mobile
        self._playwright = None
        self._browser = None
        self._context: BrowserContext | None = None
        self.page: Page | None = None
        self._network_logs: list[dict] = []
        self._console_logs: list[dict] = []

    # ------------------------------------------------------------------
    # Context-manager protocol
    # ------------------------------------------------------------------

    def __enter__(self):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=settings.HEADLESS,
            slow_mo=settings.SLOW_MO,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx_kwargs = {"ignore_https_errors": True}
        if self._mobile:
            ctx_kwargs.update(MOBILE_DEVICE)
        else:
            ctx_kwargs["viewport"] = DESKTOP_VIEWPORT

        self._context = self._browser.new_context(**ctx_kwargs)
        self._context.grant_permissions(["geolocation"])

        self.page = self._context.new_page()
        self._attach_listeners()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        return False

    # ------------------------------------------------------------------
    # Listeners
    # ------------------------------------------------------------------

    def _attach_listeners(self) -> None:
        self.page.on("response", self._on_response)
        self.page.on("console", self._on_console)

    def _on_response(self, response) -> None:
        try:
            self._network_logs.append(
                {
                    "url": response.url,
                    "method": response.request.method,
                    "status_code": response.status,
                    "resource_type": response.request.resource_type,
                }
            )
        except Exception:
            pass

    def _on_console(self, msg) -> None:
        self._console_logs.append({"log_type": msg.type, "message": msg.text})

    # ------------------------------------------------------------------
    # Drain helpers (call after each step to persist logs)
    # ------------------------------------------------------------------

    def drain_network_logs(self) -> list[dict]:
        logs, self._network_logs = self._network_logs, []
        return logs

    def drain_console_logs(self) -> list[dict]:
        logs, self._console_logs = self._console_logs, []
        return logs

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def clear_browser_state(self) -> None:
        """Clear cookies, localStorage, sessionStorage, and cache."""
        self._context.clear_cookies()
        self.page.evaluate(
            """() => {
                try { localStorage.clear(); } catch(e) {}
                try { sessionStorage.clear(); } catch(e) {}
            }"""
        )
