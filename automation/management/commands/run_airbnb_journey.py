"""
Django management command: run_airbnb_journey

Usage:
    python manage.py run_airbnb_journey
    python manage.py run_airbnb_journey --mobile
    python manage.py run_airbnb_journey --headless false
"""

import os
# Required: Playwright's sync API triggers Django's async-unsafe guard.
# This is safe for a single-threaded management command.
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

from django.core.management.base import BaseCommand
from django.utils import timezone

from automation.models import TestRun
from automation.utils.browser import BrowserManager
from automation.utils.logger import StepLogger
from automation.utils.steps import AirbnbJourney


class Command(BaseCommand):
    help = "Run the full Airbnb end-to-end user journey automation"

    def add_arguments(self, parser):
        parser.add_argument(
            "--mobile",
            action="store_true",
            default=False,
            help="Run the journey in mobile mode (iPhone 13 viewport)",
        )
        parser.add_argument(
            "--headless",
            type=str,
            default=None,
            help="Override HEADLESS setting: 'true' or 'false'",
        )

    def handle(self, *args, **options):
        mobile = options["mobile"]
        headless_override = options.get("headless")

        if headless_override is not None:
            from django.conf import settings
            settings.HEADLESS = headless_override.lower() == "true"

        self.stdout.write(self.style.SUCCESS(
            f"\n{'#'*60}\n"
            f"  Airbnb E2E Automation\n"
            f"  Mode: {'📱 Mobile' if mobile else '🖥  Desktop'}\n"
            f"{'#'*60}\n"
        ))

        test_run = TestRun.objects.create(is_mobile=mobile)
        self.stdout.write(f"Created TestRun #{test_run.pk}")

        overall_passed = True
        try:
            with BrowserManager(mobile=mobile) as bm:
                logger = StepLogger(test_run)
                journey = AirbnbJourney(bm.page, test_run, logger)

                steps = [
                    journey.step_01_landing_and_search_setup,
                    journey.step_02_autosuggestion,
                    journey.step_03_date_picker,
                    journey.step_04_guest_picker,
                    journey.step_05_search_results,
                    journey.step_06_listing_detail,
                ]

                for step_fn in steps:
                    try:
                        step_fn()
                    except Exception as exc:
                        overall_passed = False
                        self.stdout.write(self.style.ERROR(f"\n❌  Step raised an exception: {exc}\n"))

                    for net in bm.drain_network_logs():
                        logger.log_network(**net)
                    for con in bm.drain_console_logs():
                        logger.log_console(**con)

        except Exception as fatal:
            overall_passed = False
            test_run.notes = f"Fatal error: {fatal}"
            self.stdout.write(self.style.ERROR(f"\n💥  Fatal error: {fatal}\n"))

        finally:
            test_run.status = "passed" if overall_passed else "failed"
            test_run.finished_at = timezone.now()
            test_run.save(update_fields=["status", "finished_at", "notes"])

        final_style = self.style.SUCCESS if overall_passed else self.style.ERROR
        symbol = "✅" if overall_passed else "❌"
        self.stdout.write(final_style(
            f"\n{'#'*60}\n"
            f"  {symbol}  Journey complete – TestRun #{test_run.pk} [{test_run.status.upper()}]\n"
            f"  Duration: {(test_run.finished_at - test_run.started_at).seconds}s\n"
            f"  View results: http://127.0.0.1:8000/run/{test_run.pk}/\n"
            f"  Admin: http://127.0.0.1:8000/admin/\n"
            f"{'#'*60}\n"
        ))