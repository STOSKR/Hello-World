"""
BUFF extractor - Specialized extractor for BUFF163 marketplace data.
Uses production-tested selectors from working implementation.
"""

import re
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from typing import Optional, List, Dict
from app.core.logger import get_logger

logger = get_logger(__name__)


class BuffExtractor:
    """Handles all BUFF163-specific extraction logic with real selectors."""

    def __init__(self, timeout: int = 30000):
        self.timeout = timeout  # 30s timeout for BUFF (slow site)

    async def extract_buff_url(self, page: Page) -> Optional[str]:
        """Extract BUFF URL from SteamDT item page."""
        try:
            buff_link = page.locator('a[href*="buff.163.com"]').first
            buff_url = await buff_link.get_attribute("href")
            return buff_url
        except Exception as e:
            logger.error("buff_url_extraction_error", error=str(e))
        return None

    async def extract_buff_data(
        self, page: Page, buff_url: str, item_name: str
    ) -> Optional[dict]:
        """Extract complete BUFF market data using real selectors."""
        try:
            # Clean URL and navigate to selling tab
            base_url = buff_url.split("#")[0].split("?")[0]
            selling_url = f"{base_url}?from=market#tab=selling"

            logger.info("navigating_to_buff", url=selling_url)

            try:
                await page.goto(
                    selling_url, wait_until="domcontentloaded", timeout=self.timeout
                )
                await page.wait_for_timeout(5000)  # Wait for dynamic content
            except PlaywrightTimeout:
                logger.error("buff_navigation_timeout", url=selling_url)
                return None

            # Extract selling items
            selling_items = await self.extract_selling_items(page)

            if not selling_items:
                logger.warning("no_buff_selling_items", item=item_name)
                return None

            logger.info("buff_selling_extracted", count=len(selling_items))

            # Navigate to trade history
            history_url = f"{base_url}?from=market#tab=history"

            try:
                await page.goto(
                    history_url, wait_until="domcontentloaded", timeout=self.timeout
                )
                await page.wait_for_timeout(5000)
            except PlaywrightTimeout:
                logger.warning("buff_history_timeout")
                trade_records = []

            trade_records = await self.extract_trade_records(page)

            if trade_records:
                logger.info("buff_trades_extracted", count=len(trade_records))

            # Validate price stability (detect dumps)
            if not self.validate_price_difference(selling_items, trade_records):
                logger.warning(
                    "price_drop_detected",
                    item=item_name,
                    reason="Recent trades 10%+ cheaper than current listings",
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

        except Exception as e:
            logger.error("buff_extraction_error", error=str(e), url=buff_url)
            return None

    async def extract_selling_items(self, page: Page) -> List[Dict]:
        """Extract current BUFF selling listings with production selectors."""
        selling_items = []

        try:
            # Wait for table to load (use real selector from working version)
            logger.info("waiting_for_buff_table")

            try:
                await page.wait_for_selector("tr.selling", timeout=15000)
            except PlaywrightTimeout:
                logger.warning("no_selling_rows_trying_generic_selector")
                try:
                    await page.wait_for_selector("table tbody tr", timeout=10000)
                except PlaywrightTimeout:
                    logger.error("no_buff_table_found")
                    return []

            # Get first 5 rows (cheapest listings)
            rows = await page.locator("tr.selling").all()

            if len(rows) == 0:
                logger.warning("no_selling_rows_using_generic")
                rows = await page.locator("table tbody tr").all()

            logger.info("buff_rows_found", total=len(rows))
            rows_to_process = rows[:5]

            for idx, row in enumerate(rows_to_process):
                try:
                    # Extract price in CNY (¥ symbol)
                    price_element = row.locator("strong.f_Strong")
                    price_text = await price_element.inner_text()

                    # Clean: "¥ 10.8" -> "10.8"
                    price_cny = re.sub(r"[¥\s]", "", price_text).strip()

                    if price_cny and float(price_cny) > 0:
                        selling_items.append(
                            {
                                "price": price_cny,
                                "price_cny": float(price_cny),
                                "platform": "BUFF",
                            }
                        )

                except Exception as e:
                    logger.debug("buff_item_parse_error", row=idx, error=str(e))
                    continue

        except Exception as e:
            logger.error("buff_selling_extraction_error", error=str(e))

        return selling_items

    async def extract_trade_records(self, page: Page) -> List[Dict]:
        """Extract recent BUFF trade history with production selectors."""
        trade_records = []

        try:
            # Wait for trade history table
            try:
                await page.wait_for_selector("table tbody tr", timeout=10000)
            except PlaywrightTimeout:
                logger.warning("buff_trades_timeout")
                return []

            # Get recent trades
            rows = await page.locator("table tbody tr").all()
            logger.info("buff_trade_rows_found", total=len(rows))

            rows_to_process = rows[:5]  # Last 5 trades

            for idx, row in enumerate(rows_to_process):
                try:
                    # Extract price
                    price_element = row.locator("strong.f_Strong")
                    price_text = await price_element.inner_text()

                    price_cny = re.sub(r"[¥\s]", "", price_text).strip()

                    if price_cny and float(price_cny) > 0:
                        trade_records.append(
                            {
                                "price": price_cny,
                                "price_cny": float(price_cny),
                                "platform": "BUFF",
                            }
                        )

                except Exception as e:
                    logger.debug("buff_trade_parse_error", row=idx, error=str(e))
                    continue

        except Exception as e:
            logger.error("buff_trades_extraction_error", error=str(e))

        return trade_records

    def validate_price_difference(
        self, selling_items: List[Dict], trade_records: List[Dict]
    ) -> bool:
        """
        Check if recent trades are significantly cheaper (dump detection).
        Returns False if recent trades are 10%+ cheaper than current listings.
        """
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
