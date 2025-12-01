"""
Steam extractor - Specialized extractor for Steam Market data.
"""

import re
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from typing import Optional, List, Dict
from app.core.logger import get_logger

logger = get_logger(__name__)


class SteamExtractor:
    """Handles all Steam Market-specific extraction logic."""

    def __init__(self, timeout: int = 10000):
        self.timeout = timeout

    async def extract_steam_url(self, page: Page) -> Optional[str]:
        """Extract Steam Market URL from SteamDT item page."""
        try:
            steam_links = await page.query_selector_all(
                'a[href*="steamcommunity.com/market"]'
            )
            if steam_links:
                return await steam_links[0].get_attribute("href")
        except Exception as e:
            logger.error("steam_url_extraction_error", error=str(e))
        return None

    async def extract_steam_data(
        self, page: Page, steam_url: str, item_name: str
    ) -> Optional[dict]:
        """Extract complete Steam Market data."""
        try:
            logger.info("navigating_to_steam", url=steam_url)
            await page.goto(steam_url, wait_until="networkidle", timeout=self.timeout)
            await page.wait_for_timeout(5000)

            # Extract selling items
            selling_items = await self.extract_selling_items(page)

            if not selling_items:
                logger.warning("no_steam_listings", item=item_name)
                return None

            logger.info("steam_data_extracted", selling=len(selling_items))

            # Calculate averages
            avg_price = (
                sum(float(item["price"]) for item in selling_items) / len(selling_items)
                if selling_items
                else 0.0
            )

            lowest_price = min((float(i["price"]) for i in selling_items), default=0.0)

            return {
                "platform": "Steam",
                "avg_price": avg_price,
                "lowest_price": lowest_price,
                "selling_items": selling_items,
                "volume_24h": len(selling_items),  # Approximation
            }

        except PlaywrightTimeout:
            logger.error("steam_timeout", url=steam_url)
            return None
        except Exception as e:
            logger.error("steam_extraction_error", error=str(e), url=steam_url)
            return None

    async def extract_selling_items(self, page: Page) -> List[Dict]:
        """Extract current Steam Market listings."""
        selling_items = []

        try:
            # Wait for listings section
            await page.wait_for_selector("#searchResultsRows", timeout=5000)

            # Extract listing rows
            rows = await page.query_selector_all(
                "#searchResultsRows .market_listing_row"
            )

            for row in rows[:15]:  # Limit to 15 items
                try:
                    # Price
                    price_elem = await row.query_selector(".market_listing_price")
                    price_text = await price_elem.inner_text() if price_elem else "0"

                    # Clean price (remove currency symbols, whitespace)
                    price = re.sub(r"[^\d.]", "", price_text)

                    # Quantity (usually 1 per listing on Steam)
                    quantity = 1

                    if price and float(price) > 0:
                        selling_items.append(
                            {
                                "price": price,
                                "quantity": quantity,
                                "platform": "Steam",
                            }
                        )

                except Exception as e:
                    logger.debug("steam_listing_parse_error", error=str(e))
                    continue

            logger.info("steam_listings_extracted", count=len(selling_items))

        except PlaywrightTimeout:
            logger.warning("steam_listings_timeout")
        except Exception as e:
            logger.error("steam_listings_error", error=str(e))

        return selling_items
