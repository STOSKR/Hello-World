"""
File saving utilities for scraper.
Handles JSON, HTML, screenshots and debug data.
"""

import json
import os
from typing import List
from playwright.async_api import Page

from app.core.logger import get_logger
from app.core.config import Settings
from app.domain.models import ScrapedItem

logger = get_logger(__name__)


class FileSaver:
    """Manages file saving for scraper."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.output_dir = settings.output_dir

        # Create directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    def save_json(self, data: List[ScrapedItem], filename: str = "scraped_data.json"):
        """Save scraped data as JSON."""
        # Ensure path includes directory
        if not filename.startswith(self.output_dir):
            filename = os.path.join(self.output_dir, os.path.basename(filename))

        # Convert Pydantic models to dict
        data_dicts = [item.model_dump() for item in data]

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data_dicts, f, ensure_ascii=False, indent=2, default=str)

        logger.info("data_saved_to_file", filename=filename, items=len(data))

    async def save_debug_files(self, page: Page):
        """Save debug files (screenshot and HTML)."""
        if not self.settings.save_debug_info:
            return

        # Save screenshot
        if self.settings.save_screenshot:
            await self.save_screenshot(page, "debug_screenshot.png")

        # Save HTML
        if self.settings.save_html:
            await self.save_html(page, "page_content.html")

    async def save_screenshot(self, page: Page, filename: str = "screenshot.png"):
        """Save page screenshot."""
        try:
            screenshot_path = os.path.join(self.output_dir, filename)
            await page.screenshot(path=screenshot_path)
            logger.info("screenshot_saved", path=screenshot_path)
        except Exception as e:
            logger.warning("screenshot_save_error", error=str(e))

    async def save_html(self, page: Page, filename: str = "page_content.html"):
        """Save page HTML content."""
        try:
            html_path = os.path.join(self.output_dir, filename)
            content = await page.content()

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info("html_saved", path=html_path)
        except Exception as e:
            logger.warning("html_save_error", error=str(e))

    def ensure_output_directory_exists(self):
        """Ensure output directory exists."""
        os.makedirs(self.output_dir, exist_ok=True)
