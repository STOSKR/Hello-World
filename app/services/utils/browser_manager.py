"""
Browser manager for Playwright.
Handles browser initialization and configuration.
Supports both persistent context (local) and storage_state (CI/manual sessions).
"""

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from typing import Optional
import os
import json
from pathlib import Path

from app.core.logger import get_logger

logger = get_logger(__name__)


class BrowserManager:
    """Manages creation and configuration of Playwright browser."""

    def __init__(
        self,
        headless: bool = True,
        profile_dir: Optional[str] = None,
        storage_state_path: Optional[str] = None,
        use_persistent_context: bool = True,
    ):
        self.headless = headless
        self.profile_dir = profile_dir or os.path.join(
            os.path.expanduser("~"), ".cs_tracker_profile"
        )
        self.storage_state_path = storage_state_path
        self.use_persistent_context = use_persistent_context
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """Start browser with persistent context or storage state."""
        logger.info(
            "starting_browser",
            mode="persistent" if self.use_persistent_context else "storage_state",
        )

        self.playwright = await async_playwright().start()

        if self.use_persistent_context:
            # Use persistent profile in user directory
            # First time: manually login to BUFF and Steam
            # Subsequent times: sessions will persist
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.profile_dir,
                headless=self.headless,
                channel="chrome",  # Use installed Chrome
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ],
                ignore_default_args=["--enable-automation"],
            )

            # Persistent context comes with pages, use first or create new
            if len(self.context.pages) > 0:
                self.page = self.context.pages[0]
            else:
                self.page = await self.context.new_page()
        else:
            # Use regular browser with storage_state for CI/manual sessions
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                channel="chrome",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ],
            )

            # Load storage state if available
            context_options = {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "ignore_https_errors": True,
            }

            if self.storage_state_path and os.path.exists(self.storage_state_path):
                context_options["storage_state"] = self.storage_state_path
                logger.info("loading_storage_state", path=self.storage_state_path)

            self.context = await self.browser.new_context(**context_options)
            self.page = await self.context.new_page()

        # Hide webdriver property
        await self.page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
        )

        logger.info(
            "browser_started",
            profile_path=self.profile_dir if self.use_persistent_context else None,
        )

    async def close(self):
        """Close browser and cleanup."""
        if self.context:
            await self.context.close()
            logger.info("browser_closed")
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def save_storage_state(self, path: str):
        """Save current storage state (cookies, local storage) to file."""
        if not self.context:
            raise RuntimeError("Browser not started. Call start() first.")

        # Ensure directory exists
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        await self.context.storage_state(path=path)
        logger.info("storage_state_saved", path=path)

    async def navigate(self, url: str, timeout: int = 60000):
        """Navigate to URL."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")

        logger.info("navigating_to_url", url=url)
        await self.page.goto(url, wait_until="networkidle", timeout=timeout)
        logger.info("page_loaded")

    async def wait(self, milliseconds: int):
        """Wait for specified milliseconds."""
        if not self.page:
            raise RuntimeError("Browser not started.")

        await self.page.wait_for_timeout(milliseconds)

    async def close_modal(self):
        """Close modal if present."""
        if not self.page:
            return

        try:
            # Look for close button (Chinese text)
            close_button = self.page.locator('button:has-text("我已知晓")')
            if await close_button.count() > 0:
                await close_button.first.click()
                logger.info("modal_closed")
                await self.wait(1000)
        except Exception as e:
            logger.debug("modal_not_found_or_already_closed", error=str(e))

    def get_page(self) -> Page:
        """Get current page instance."""
        if not self.page:
            raise RuntimeError("Browser not started.")
        return self.page
