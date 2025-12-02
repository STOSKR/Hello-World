import asyncio
from playwright.async_api import Page, BrowserContext
from typing import Optional, Dict

from app.core.logger import get_logger
from app.domain.rules import calculate_profit, calculate_roi, convert_cny_to_eur
from .buff_extractor import BuffExtractor
from .steam_extractor import SteamExtractor

logger = get_logger(__name__)


class DetailedItemExtractor:

    def __init__(self):
        self.buff_extractor = BuffExtractor(timeout=10000)
        self.steam_extractor = SteamExtractor(timeout=10000)
        self.buff_page = None
        self.steam_page = None

    async def extract_detailed_item(
        self,
        page: Page,
        item: Dict,
        context: Optional[BrowserContext] = None,
        worker_id: Optional[int] = None,
    ) -> Optional[Dict]:
        try:
            # Step 1: Get platform URLs
            buff_url, steam_url = await self._get_platform_urls(page, item)
            if not buff_url or not steam_url:
                return None

            # Log URLs being processed
            logger.info(
                "processing_item_urls",
                worker_id=worker_id,
                item=item["item_name"],
                buff_url=buff_url,
                steam_url=steam_url,
            )

            # Step 2 & 3: Extract BUFF and Steam data in parallel
            if context:
                # Create persistent pages once, reuse for all items

                if not self.buff_page:
                    self.buff_page = await context.new_page()
                if not self.steam_page:
                    self.steam_page = await context.new_page()

                buff_data, steam_data = await asyncio.gather(
                    self.buff_extractor.extract_buff_data(
                        self.buff_page, buff_url, item["item_name"], worker_id=worker_id
                    ),
                    self.steam_extractor.extract_steam_data(
                        self.steam_page,
                        steam_url,
                        item["item_name"],
                        worker_id=worker_id,
                    ),
                )
            else:
                # Fallback: sequential scraping with single page
                buff_data = await self.buff_extractor.extract_buff_data(
                    page, buff_url, item["item_name"], worker_id=worker_id
                )
                steam_data = await self.steam_extractor.extract_steam_data(
                    page, steam_url, item["item_name"], worker_id=worker_id
                )

            if not buff_data:
                logger.info("item_discarded_buff_validation")
                return {
                    "item_name": item["item_name"],
                    "quality": item.get("quality"),
                    "stattrak": item.get("stattrak", False),
                    "discarded": True,
                    "discard_reason": "BUFF data validation failed",
                }

            if not steam_data:
                logger.warning("steam_data_extraction_failed")
                return {
                    "item_name": item["item_name"],
                    "quality": item.get("quality"),
                    "stattrak": item.get("stattrak", False),
                    "discarded": True,
                    "discard_reason": "Steam data extraction failed",
                }

            # Validate minimum volume (liquidity check)
            buff_volume = buff_data.get(
                "total_volume", 0
            )  # Use total available, not just extracted
            steam_volume = steam_data.get(
                "total_volume", 0
            )  # Use total available from Steam counter

            if buff_volume < 20:
                logger.info(
                    "item_discarded_low_buff_volume",
                    item=item["item_name"],
                    volume=buff_volume,
                    required=20,
                )
                return {
                    "item_name": item["item_name"],
                    "quality": item.get("quality"),
                    "stattrak": item.get("stattrak", False),
                    "discarded": True,
                    "discard_reason": f"Low BUFF volume ({buff_volume}/20)",
                }

            if steam_volume < 20:
                logger.info(
                    "item_discarded_low_steam_volume",
                    item=item["item_name"],
                    volume=steam_volume,
                    required=20,
                )
                return {
                    "item_name": item["item_name"],
                    "quality": item.get("quality"),
                    "stattrak": item.get("stattrak", False),
                    "discarded": True,
                    "discard_reason": f"Low Steam volume ({steam_volume}/20)",
                }

            # Step 4: Calculate profitability
            analysis = self._calculate_profitability(buff_data, steam_data)
            if not analysis:
                logger.warning("profitability_calculation_failed")
                return {
                    "item_name": item["item_name"],
                    "quality": item.get("quality"),
                    "stattrak": item.get("stattrak", False),
                    "discarded": True,
                    "discard_reason": "Profitability calculation failed",
                }

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

    async def cleanup(self):
        """Close persistent pages."""
        if self.buff_page:
            await self.buff_page.close()
            self.buff_page = None
        if self.steam_page:
            await self.steam_page.close()
            self.steam_page = None
        logger.info("persistent_pages_closed")
