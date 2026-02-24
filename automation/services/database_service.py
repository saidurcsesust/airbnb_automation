"""
Database Service: Handles all database operations for test results and scraped data.
"""
import json
import logging

from automation.models import (
    TestResult, ListingData, SuggestionData, NetworkLog, ConsoleLog
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Centralized service for persisting automation results to the database.
    All test case results follow the pattern: "Should be ___, found ___"
    """

    @staticmethod
    def save_test_result(
        test_case: str,
        url: str,
        passed: bool,
        should_be: str,
        found: str
    ) -> TestResult:
        """
        Save a test case result.
        Comment format: "should be <expected>, found <actual>"
        """
        comment = f"should be {should_be}, found {found}"
        result = TestResult.objects.create(
            test_case=test_case,
            url=url,
            passed=passed,
            comment=comment,
        )
        status = "PASSED" if passed else "FAILED"
        logger.info(f"[{status}] {test_case} | {comment}")
        return result

    @staticmethod
    def save_suggestions(suggestions: list, search_query: str) -> None:
        """Bulk save auto-suggestion items."""
        objs = [
            SuggestionData(text=s, search_query=search_query)
            for s in suggestions if s
        ]
        SuggestionData.objects.bulk_create(objs)
        logger.info(f"Saved {len(objs)} suggestions for query '{search_query}'")

    @staticmethod
    def save_listings(listings: list) -> None:
        """Bulk save listing data from search results."""
        objs = [
            ListingData(
                title=l.get('title', ''),
                price=l.get('price', ''),
                image_url=l.get('image_url', ''),
                listing_url=l.get('listing_url', ''),
            )
            for l in listings
        ]
        ListingData.objects.bulk_create(objs)
        logger.info(f"Saved {len(objs)} listings")

    @staticmethod
    def save_network_logs(logs: list) -> None:
        """Save network request logs from Selenium or Playwright formats."""
        import json as json_module
        saved = 0
        for log in logs:
            try:
                # Playwright shape
                if 'url' in log and 'status_code' in log:
                    url = log.get('url', '')
                    if url and not url.startswith('data:'):
                        NetworkLog.objects.create(
                            url=url[:2048],
                            method=(log.get('method') or 'GET')[:10],
                            status_code=log.get('status_code'),
                            resource_type=(log.get('resource_type') or '')[:50],
                        )
                        saved += 1
                    continue

                # Selenium performance log shape
                message = json_module.loads(log.get('message', '{}')).get('message', {})
                method_name = message.get('method', '')

                if method_name == 'Network.responseReceived':
                    params = message.get('params', {})
                    response = params.get('response', {})
                    url = response.get('url', '')
                    status = response.get('status', None)
                    resource_type = params.get('type', '')

                    if url and not url.startswith('data:'):
                        NetworkLog.objects.create(
                            url=url[:2048],
                            method='GET',
                            status_code=status,
                            resource_type=resource_type,
                        )
                        saved += 1
            except Exception:
                continue
        logger.info(f"Saved {saved} network log entries")

    @staticmethod
    def save_console_logs(logs: list) -> None:
        """Save browser console log entries."""
        level_map = {
            'INFO': 'INFO',
            'WARNING': 'WARNING',
            'SEVERE': 'ERROR',
            'DEBUG': 'DEBUG',
        }
        objs = []
        for log in logs:
            level = level_map.get(log.get('level', 'INFO'), 'INFO')
            message = log.get('message', '')
            source = log.get('source', '')
            objs.append(ConsoleLog(level=level, message=message[:2000], source=source[:512]))

        if objs:
            ConsoleLog.objects.bulk_create(objs)
            logger.info(f"Saved {len(objs)} console log entries")
