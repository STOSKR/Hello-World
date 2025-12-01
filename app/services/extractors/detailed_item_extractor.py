"""
Detailed item extractor orchestrator.
Coordinates extraction from BUFF and Steam using specialized extractors.

This module has been refactored from 605+ lines to ~160 lines by:
1. Extracting BUFF logic to BuffExtractor
2. Extracting Steam logic to SteamExtractor
3. Using domain rules for calculations
4. Removing duplicate code
"""

import re
from playwright.async_api import Page
from typing import Optional

from app.core.logger import get_logger
from app.domain.models import Skin, MarketData, PriceData
from app.domain.rules import calculate_profit, calculate_roi
from .buff_extractor import BuffExtractor
from .steam_extractor import SteamExtractor

logger = get_logger(__name__)


class DetailedItemExtractor:
    """
    Orchestrates detailed extraction from multiple platforms.

    Responsibilities:
    - Coordinate URL extraction from SteamDT
    - Delegate platform-specific extraction to specialized extractors
    - Calculate profitability metrics
    - Create structured MarketData objects
    """

    def __init__(self):
        self.buff_extractor = BuffExtractor(timeout=10000)
        self.steam_extractor = SteamExtractor(timeout=10000)
        self.screenshot_counter = 0

    async def _save_screenshot(self, page: Page, step_name: str):
        """Save screenshot for debugging."""
        try:
            import os

            os.makedirs("data/screenshots", exist_ok=True)
            self.screenshot_counter += 1
            clean_name = re.sub(r'[<>:"/\\|?*]', "_", step_name)
            filename = (
                f"data/screenshots/step_{self.screenshot_counter:03d}_{clean_name}.png"
            )
            await page.screenshot(path=filename, full_page=False)
            logger.info("screenshot_saved", filename=filename)
        except Exception as e:
            logger.warning("screenshot_error", error=str(e))

    async def extract_detailed_item(
        self,
        page: Page,
        skin: Skin,
    ) -> Optional[MarketData]:
        """
        Extract detailed market data for a skin.

        Flow:
        1. Get platform URLs (BUFF, Steam)
        2. Extract data from each platform
        3. Calculate profitability
        4. Return structured MarketData
        """
        logger.info("processing_item", name=skin.name)

        try:
            # Step 1: Get platform URLs
            buff_url, steam_url = await self._get_platform_urls(page, skin)
            if not buff_url or not steam_url:
                return None

            logger.info("platform_urls", buff=buff_url, steam=steam_url)

            # Step 2: Extract BUFF data
            buff_data = await self.buff_extractor.extract_buff_data(
                page, buff_url, skin.name
            )
            if not buff_data:
                logger.info("item_discarded_buff_validation")
                return None

            await self._save_screenshot(page, f"buff_{skin.name[:30]}")

            # Step 3: Extract Steam data
            steam_data = await self.steam_extractor.extract_steam_data(
                page, steam_url, skin.name
            )
            if not steam_data:
                logger.warning("steam_data_extraction_failed")
                return None

            await self._save_screenshot(page, f"steam_{skin.name[:30]}")

            # Step 4: Calculate profitability
            analysis = self._calculate_profitability(buff_data, steam_data)
            if not analysis:
                logger.warning("profitability_calculation_failed")
                return None

            # Step 5: Create MarketData object
            market_data = MarketData(
                skin=skin,
                buff=PriceData(
                    avg_price_cny=analysis["buff_avg_price"]
                    * 8.2,  # EUR to CNY conversion
                    avg_price_eur=analysis["buff_avg_price"],
                    selling_items_count=len(buff_data.get("selling_items", [])),
                    trade_records_count=len(buff_data.get("trade_records", [])),
                ),
                steam=PriceData(
                    avg_price_cny=analysis["steam_avg_price"] * 8.2,
                    avg_price_eur=analysis["steam_avg_price"],
                    selling_items_count=len(steam_data.get("selling_items", [])),
                ),
                profitability_ratio=analysis["profitability_ratio"],
                profit_eur=analysis["profit_eur"],
            )

            logger.info(
                "item_processed_successfully",
                profitability=f"{analysis['profitability_ratio']:.2%}",
                profit=f"€{analysis['profit_eur']:.2f}",
            )
            return market_data

        except Exception as e:
            logger.error("item_processing_error", name=skin.name, error=str(e))
            return None

    async def _get_platform_urls(
        self, page: Page, skin: Skin
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Get BUFF and Steam URLs.

        If URLs are not in the skin object, extract them from SteamDT item page.
        """
        buff_url = skin.buff_url
        steam_url = skin.steam_url

        if not buff_url or not steam_url:
            logger.info("extracting_urls_from_steamdt")
            await page.goto(skin.item_url, wait_until="networkidle", timeout=10000)
            await page.wait_for_timeout(5000)
            await self._save_screenshot(page, f"steamdt_{skin.name[:30]}")

            if not buff_url:
                buff_url = await self.buff_extractor.extract_buff_url(page)
                if not buff_url:
                    logger.warning("buff_url_not_found", name=skin.name)

            if not steam_url:
                steam_url = await self.steam_extractor.extract_steam_url(page)
                if not steam_url:
                    logger.warning("steam_url_not_found", name=skin.name)

        return buff_url, steam_url

    def _calculate_profitability(
        self, buff_data: dict, steam_data: dict
    ) -> Optional[dict]:
        """
        Calculate profitability metrics using domain rules.

        Uses:
        - calculate_profit(): Profit after fees
        - calculate_roi(): Return on investment
        """
        try:
            # Get average prices from extractors
            buff_avg = buff_data.get("avg_price", 0.0)
            steam_avg = steam_data.get("avg_price", 0.0)

            if buff_avg <= 0 or steam_avg <= 0:
                logger.warning("invalid_prices", buff=buff_avg, steam=steam_avg)
                return None

            # Calculate using domain rules (handles fees automatically)
            profit_eur = calculate_profit(buff_avg, steam_avg)
            roi = calculate_roi(buff_avg, steam_avg)

            return {
                "buff_avg_price": round(buff_avg, 2),
                "steam_avg_price": round(steam_avg, 2),
                "profitability_ratio": roi / 100.0,  # Convert percentage to ratio
                "profit_eur": round(profit_eur, 2),
            }

        except Exception as e:
            logger.error("profitability_calculation_error", error=str(e))
            return None
