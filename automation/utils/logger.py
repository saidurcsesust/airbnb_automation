"""Logging utilities: prints to stdout and persists TestCase records."""

import time
from datetime import datetime, timezone

from automation.models import TestCase, ConsoleLog, NetworkLog


class StepLogger:
    """
    Records test step results to both stdout and the database.

    Usage::

        logger = StepLogger(test_run=run)
        with logger.step(1, "Step 01 – Landing Page"):
            # do stuff
            logger.info("Page loaded OK")
    """

    def __init__(self, test_run):
        self.test_run = test_run
        self._current_step: int | None = None
        self._current_name: str | None = None
        self._step_start: float | None = None
        self._step_messages: list[str] = []
        self._step_status: str = "passed"
        self._screenshot_path: str = ""

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def info(self, message: str) -> None:
        print(f"    [INFO] {message}")
        self._step_messages.append(f"[INFO] {message}")

    def warn(self, message: str) -> None:
        print(f"    [WARN] {message}")
        self._step_messages.append(f"[WARN] {message}")

    def error(self, message: str) -> None:
        print(f"    [ERROR] {message}")
        self._step_messages.append(f"[ERROR] {message}")
        self._step_status = "failed"

    def set_screenshot(self, path: str) -> None:
        self._screenshot_path = path

    # ------------------------------------------------------------------
    # Context-manager step
    # ------------------------------------------------------------------

    def step(self, number: int, name: str):
        return _StepContext(self, number, name)

    def _begin_step(self, number: int, name: str) -> None:
        self._current_step = number
        self._current_name = name
        self._step_start = time.monotonic()
        self._step_messages = []
        self._step_status = "passed"
        self._screenshot_path = ""
        print(f"\n{'='*60}")
        print(f"  STEP {number:02d}: {name}")
        print(f"{'='*60}")

    def _end_step(self, exc: BaseException | None) -> None:
        duration_ms = int((time.monotonic() - self._step_start) * 1000)
        if exc is not None:
            self._step_status = "failed"
            self._step_messages.append(f"[EXCEPTION] {exc}")

        status_label = "✅ PASSED" if self._step_status == "passed" else "❌ FAILED"
        print(f"  → {status_label} ({duration_ms}ms)")

        TestCase.objects.create(
            test_run=self.test_run,
            step_number=self._current_step,
            step_name=self._current_name,
            status=self._step_status,
            message="\n".join(self._step_messages),
            screenshot_path=self._screenshot_path,
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------
    # Network / Console helpers
    # ------------------------------------------------------------------

    def log_network(self, url: str, method: str, status_code, resource_type: str) -> None:
        NetworkLog.objects.create(
            test_run=self.test_run,
            url=url[:2000],
            method=method,
            status_code=status_code,
            resource_type=resource_type,
            step_name=self._current_name or "",
        )

    def log_console(self, log_type: str, message: str) -> None:
        ConsoleLog.objects.create(
            test_run=self.test_run,
            log_type=log_type,
            message=message[:2000],
            step_name=self._current_name or "",
        )


class _StepContext:
    def __init__(self, logger: StepLogger, number: int, name: str):
        self._logger = logger
        self._number = number
        self._name = name

    def __enter__(self):
        self._logger._begin_step(self._number, self._name)
        return self._logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._logger._end_step(exc_val)
        return False  # do not suppress exceptions
