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
from typing import Optional, Dict

from app.core.logger import get_logger
from app.domain.rules import calculate_profit, calculate_roi, convert_cny_to_eur
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
        item: Dict,
    ) -> Optional[Dict]:
        """
        Extract detailed market data for an item.

        Flow:
        1. Get platform URLs (BUFF, Steam)
        2. Extract data from each platform
        3. Calculate profitability
        4. Return dict with all data
        """
        logger.info("processing_item", name=item["item_name"])

        try:
            # Step 1: Get platform URLs
            buff_url, steam_url = await self._get_platform_urls(page, item)
            if not buff_url or not steam_url:
                return None

            logger.info("platform_urls", buff=buff_url, steam=steam_url)

            # Step 2: Extract BUFF data
            buff_data = await self.buff_extractor.extract_buff_data(
                page, buff_url, item["item_name"]
            )
            if not buff_data:
                logger.info("item_discarded_buff_validation")
                return None

            await self._save_screenshot(page, f"buff_{item['item_name'][:30]}")

            # Step 3: Extract Steam data
            steam_data = await self.steam_extractor.extract_steam_data(
                page, steam_url, item["item_name"]
            )
            if not steam_data:
                logger.warning("steam_data_extraction_failed")
                return None

            await self._save_screenshot(page, f"steam_{item['item_name'][:30]}")

            # Step 4: Calculate profitability
            analysis = self._calculate_profitability(buff_data, steam_data)
            if not analysis:
                logger.warning("profitability_calculation_failed")
                return None

            # Log precios scrapeados
            logger.info(
                "prices_scraped",
                buff_cny=f"¥{buff_data.get('avg_price', 0):.2f}",
                buff_eur=f"€{analysis['buff_avg_price']:.2f}",
                steam_eur=f"€{analysis['steam_avg_price']:.2f}",
            )

            # Step 5: Create detailed data dictionary (like old implementation)
            detailed_data = {
                "item_name": item["item_name"],
                "quality": item.get("quality"),
                "stattrak": item.get("stattrak", False),
                "url": item.get("url"),
                "buff_url": buff_url,
                "steam_url": steam_url,
                "buff_avg_price_eur": analysis["buff_avg_price"],
                "steam_avg_price_eur": analysis["steam_avg_price"],
                "buff_volume": len(buff_data.get("selling_items", [])),
                "steam_volume": len(steam_data.get("selling_items", [])),
                "profit_eur": analysis["profit_eur"],
                "profitability_percent": analysis["profitability_ratio"] * 100,
                "profitability_ratio": analysis["profitability_ratio"],
            }

            logger.info(
                "item_processed_successfully",
                profitability=f"{analysis['profitability_ratio']:.2%}",
                profit=f"€{analysis['profit_eur']:.2f}",
            )
            return detailed_data

        except Exception as e:
            logger.error("item_processing_error", name=item["item_name"], error=str(e))
            return None

    async def _get_platform_urls(
        self, page: Page, item: Dict
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Get BUFF and Steam URLs.

        If URLs are not in the item dict, extract them from SteamDT item page.
        """
        buff_url = item.get("buff_url")
        steam_url = item.get("steam_url")

        if not buff_url or not steam_url:
            logger.info("extracting_urls_from_steamdt")
            item_url = item.get("url")
            if not item_url:
                logger.error("no_item_url")
                return None, None
            await page.goto(item_url, wait_until="networkidle", timeout=10000)
            await page.wait_for_timeout(5000)
            await self._save_screenshot(page, f"steamdt_{item['item_name'][:30]}")

            if not buff_url:
                buff_url = await self.buff_extractor.extract_buff_url(page)
                if not buff_url:
                    logger.warning("buff_url_not_found", name=item["item_name"])

            if not steam_url:
                steam_url = await self.steam_extractor.extract_steam_url(page)
                if not steam_url:
                    logger.warning("steam_url_not_found", name=item["item_name"])

        return buff_url, steam_url

    def _calculate_profitability(
        self, buff_data: dict, steam_data: dict
    ) -> Optional[dict]:
        """
        Calculate profitability metrics using domain rules.

        Uses:
        - convert_cny_to_eur(): Currency conversion
        - calculate_profit(): Profit after fees
        - calculate_roi(): Return on investment
        """
        try:
            # Get average prices from extractors (in CNY for BUFF, EUR for Steam)
            buff_avg_cny = buff_data.get("avg_price", 0.0)
            steam_avg_eur = steam_data.get("avg_price", 0.0)

            if buff_avg_cny <= 0 or steam_avg_eur <= 0:
                logger.warning("invalid_prices", buff=buff_avg_cny, steam=steam_avg_eur)
                return None

            # Convert BUFF price from CNY to EUR
            buff_avg_eur = convert_cny_to_eur(buff_avg_cny)

            # Calculate using domain rules (handles fees automatically)
            profit_eur = calculate_profit(buff_avg_eur, steam_avg_eur)
            roi = calculate_roi(buff_avg_eur, steam_avg_eur)

            return {
                "buff_avg_price": round(buff_avg_eur, 2),
                "steam_avg_price": round(steam_avg_eur, 2),
                "profitability_ratio": roi / 100.0,  # Convert percentage to ratio
                "profit_eur": round(profit_eur, 2),
            }

        except Exception as e:
            logger.error("profitability_calculation_error", error=str(e))
            return None
