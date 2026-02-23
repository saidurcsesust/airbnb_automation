"""Screenshot helpers."""

import os
from pathlib import Path
from datetime import datetime

from django.conf import settings


def get_screenshot_dir() -> Path:
    path = Path(settings.SCREENSHOT_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def take_screenshot(page, run_id: int, step_name: str) -> str:
    """
    Capture a full-page screenshot and return the file path string.

    :param page: Playwright Page object
    :param run_id: TestRun primary key
    :param step_name: Human-readable step label (used in filename)
    :return: Absolute path to the saved screenshot
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_name = "".join(c if c.isalnum() else "_" for c in step_name)[:60]
    filename = f"run{run_id:04d}_step_{safe_name}_{timestamp}.png"
    filepath = get_screenshot_dir() / filename
    page.screenshot(path=str(filepath), full_page=True)
    return str(filepath)
