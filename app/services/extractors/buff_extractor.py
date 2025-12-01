"""
BUFF extractor - Specialized extractor for BUFF163 marketplace data.
"""

import re
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from typing import Optional, List, Dict
from app.core.logger import get_logger

logger = get_logger(__name__)


class BuffExtractor:
    """Handles all BUFF163-specific extraction logic."""

    def __init__(self, timeout: int = 10000):
        self.timeout = timeout

    async def extract_buff_url(self, page: Page) -> Optional[str]:
        """Extract BUFF URL from SteamDT item page."""
        try:
            buff_links = await page.query_selector_all('a[href*="buff.163.com"]')
            if buff_links:
                return await buff_links[0].get_attribute("href")
        except Exception as e:
            logger.error("buff_url_extraction_error", error=str(e))
        return None

    async def extract_buff_data(
        self, page: Page, buff_url: str, item_name: str
    ) -> Optional[dict]:
        """Extract complete BUFF market data."""
        try:
            logger.info("navigating_to_buff", url=buff_url)
            await page.goto(buff_url, wait_until="networkidle", timeout=self.timeout)
            await page.wait_for_timeout(5000)

            # Extract selling items and trade records in parallel
            import asyncio

            selling_items, trade_records = await asyncio.gather(
                self.extract_selling_items(page),
                self.extract_trade_records(page),
                return_exceptions=True,
            )

            if isinstance(selling_items, Exception):
                logger.error("selling_items_error", error=str(selling_items))
                selling_items = []

            if isinstance(trade_records, Exception):
                logger.error("trade_records_error", error=str(trade_records))
                trade_records = []

            logger.info(
                "buff_data_extracted",
                selling=len(selling_items),
                trades=len(trade_records),
            )

            # Validate price stability
            if not self.validate_price_difference(selling_items, trade_records):
                logger.warning(
                    "price_drop_detected",
                    item=item_name,
                    reason="Recent trades 10%+ cheaper",
                )
                return None

            # Calculate averages
            avg_selling = (
                sum(float(item["price"]) for item in selling_items) / len(selling_items)
                if selling_items
                else 0.0
            )
            avg_trade = (
                sum(float(trade["price"]) for trade in trade_records)
                / len(trade_records)
                if trade_records
                else 0.0
            )

            return {
                "platform": "BUFF",
                "avg_price": avg_selling if avg_selling > 0 else avg_trade,
                "lowest_price": min(
                    (float(i["price"]) for i in selling_items), default=0.0
                ),
                "selling_items": selling_items,
                "trade_records": trade_records,
                "volume_24h": len(trade_records),
            }

        except PlaywrightTimeout:
            logger.error("buff_timeout", url=buff_url)
            return None
        except Exception as e:
            logger.error("buff_extraction_error", error=str(e), url=buff_url)
            return None

    async def extract_selling_items(self, page: Page) -> List[Dict]:
        """Extract current BUFF selling listings."""
        selling_items = []

        try:
            # Wait for selling items section
            await page.wait_for_selector(".selling-list", timeout=5000)

            # Extract selling items
            items = await page.query_selector_all(".selling-list .item")

            for item in items[:10]:  # Limit to 10 items
                try:
                    # Price
                    price_elem = await item.query_selector(".price")
                    price_text = await price_elem.inner_text() if price_elem else "0"
                    price = re.sub(r"[^\d.]", "", price_text)

                    # Quantity
                    qty_elem = await item.query_selector(".quantity")
                    qty_text = await qty_elem.inner_text() if qty_elem else "1"
                    quantity = int(re.sub(r"\D", "", qty_text)) if qty_text else 1

                    if price and float(price) > 0:
                        selling_items.append(
                            {
                                "price": price,
                                "quantity": quantity,
                                "platform": "BUFF",
                            }
                        )

                except Exception as e:
                    logger.debug("item_parse_error", error=str(e))
                    continue

            logger.info("buff_selling_extracted", count=len(selling_items))

        except PlaywrightTimeout:
            logger.warning("buff_selling_timeout")
        except Exception as e:
            logger.error("buff_selling_error", error=str(e))

        return selling_items

    async def extract_trade_records(self, page: Page) -> List[Dict]:
        """Extract recent BUFF trade history."""
        trade_records = []

        try:
            # Wait for trade history section
            await page.wait_for_selector(".trade-history", timeout=5000)

            # Extract recent trades
            trades = await page.query_selector_all(".trade-history .trade-item")

            for trade in trades[:10]:  # Limit to 10 recent trades
                try:
                    # Price
                    price_elem = await trade.query_selector(".price")
                    price_text = await price_elem.inner_text() if price_elem else "0"
                    price = re.sub(r"[^\d.]", "", price_text)

                    # Time
                    time_elem = await trade.query_selector(".time")
                    time_text = await time_elem.inner_text() if time_elem else ""

                    if price and float(price) > 0:
                        trade_records.append(
                            {
                                "price": price,
                                "time": time_text,
                                "platform": "BUFF",
                            }
                        )

                except Exception as e:
                    logger.debug("trade_parse_error", error=str(e))
                    continue

            logger.info("buff_trades_extracted", count=len(trade_records))

        except PlaywrightTimeout:
            logger.warning("buff_trades_timeout")
        except Exception as e:
            logger.error("buff_trades_error", error=str(e))

        return trade_records

    def validate_price_difference(
        self, selling_items: List[Dict], trade_records: List[Dict]
    ) -> bool:
        """Check if recent trades are significantly cheaper (dump detection)."""
        if not selling_items or not trade_records:
            return True  # Cannot validate without data

        # Current average selling price
        current_avg = sum(float(i["price"]) for i in selling_items) / len(selling_items)

        # Recent trades average
        recent_avg = sum(float(t["price"]) for t in trade_records) / len(trade_records)

        # If recent trades are 10%+ cheaper, it's a potential dump
        threshold = 0.90
        if recent_avg < current_avg * threshold:
            logger.warning(
                "price_drop_alert",
                current=current_avg,
                recent=recent_avg,
                diff_percent=((current_avg - recent_avg) / current_avg) * 100,
            )
            return False

        return True
