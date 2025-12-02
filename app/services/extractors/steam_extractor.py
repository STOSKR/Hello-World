"""
Steam extractor - Specialized extractor for Steam Market data.
"""

import re
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from typing import Optional, List, Dict
from app.core.logger import get_logger
from app.domain.rules import convert_cny_to_eur

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
        self,
        page: Page,
        steam_url: str,
        item_name: str,
        worker_id: Optional[int] = None,
    ) -> Optional[dict]:
        """Extract complete Steam Market data."""
        try:
            await page.goto(steam_url, wait_until="networkidle", timeout=self.timeout)
            await page.wait_for_timeout(5000)

            # Get total volume from Steam's counter
            total_volume = 0
            try:
                total_elem = await page.query_selector("#searchResults_total")
                if total_elem:
                    total_text = await total_elem.inner_text()
                    total_volume = int(total_text.strip())
                    logger.info(
                        "steam_total_volume_found",
                        worker_id=worker_id,
                        total=total_volume,
                    )
            except Exception as e:
                logger.warning(
                    "steam_total_volume_extraction_failed",
                    worker_id=worker_id,
                    error=str(e),
                )

            # Extract selling items
            selling_items = await self.extract_selling_items(page)

            if not selling_items:
                logger.warning("no_steam_listings", item=item_name)
                return None

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
                "total_volume": total_volume,  # Total listings available
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

            for row in rows[:25]:  # Get up to 25 cheapest listings
                try:
                    # Price
                    price_elem = await row.query_selector(".market_listing_price")
                    price_text = await price_elem.inner_text() if price_elem else "0"

                    # Detect currency and convert if needed
                    is_cny = "¥" in price_text or "￥" in price_text

                    # Clean price (remove currency symbols, whitespace)
                    price_raw = re.sub(r"[^\d.]", "", price_text)

                    if price_raw and float(price_raw) > 0:
                        # Convert CNY to EUR if needed
                        if is_cny:
                            price_eur = convert_cny_to_eur(float(price_raw))
                            logger.debug(
                                "steam_price_converted",
                                cny=f"¥{price_raw}",
                                eur=f"€{price_eur:.2f}",
                            )
                        else:
                            price_eur = float(price_raw)

                        # Quantity (usually 1 per listing on Steam)
                        quantity = 1

                        selling_items.append(
                            {
                                "price": str(price_eur),
                                "quantity": quantity,
                                "platform": "Steam",
                                "currency": "CNY" if is_cny else "EUR",
                            }
                        )

                except Exception as e:
                    logger.debug("steam_listing_parse_error", error=str(e))
                    continue

        except PlaywrightTimeout:
            logger.warning("steam_listings_timeout")
        except Exception as e:
            logger.error("steam_listings_error", error=str(e))

        return selling_items
