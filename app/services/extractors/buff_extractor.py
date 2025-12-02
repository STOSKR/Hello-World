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

    def __init__(self, timeout: int = 15000):
        self.timeout = timeout  # 15s timeout for BUFF

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
        self, page: Page, buff_url: str, item_name: str, worker_id: Optional[int] = None
    ) -> Optional[dict]:
        """Extract complete BUFF market data using real selectors."""
        try:
            # Clean URL and navigate to selling tab
            base_url = buff_url.split("#")[0].split("?")[0]
            selling_url = f"{base_url}?from=market#tab=selling"

            logger.info("navigating_to_buff", worker_id=worker_id, url=selling_url)

            # Random delay to avoid anti-bot (especially with concurrent workers)
            import random

            delay = random.randint(2000, 5000)  # 2-5 seconds random delay
            logger.debug("buff_initial_delay", delay_ms=delay)
            await page.wait_for_timeout(delay)

            try:
                await page.goto(
                    selling_url, wait_until="domcontentloaded", timeout=self.timeout
                )
                await page.wait_for_timeout(5000)  # Wait for dynamic content
            except PlaywrightTimeout:
                logger.error("buff_navigation_timeout", url=selling_url)
                return None
            except Exception as e:
                # Handle ERR_ABORTED and other navigation errors
                error_msg = str(e)
                if (
                    "ERR_ABORTED" in error_msg
                    or "net::" in error_msg
                    or "ERR_" in error_msg
                ):
                    logger.warning(
                        "buff_navigation_aborted_retrying",
                        worker_id=worker_id,
                        url=selling_url,
                        error=error_msg[:150],
                    )
                    # Retry with longer wait and different strategy
                    try:
                        # Wait much longer before retry (simulate human behavior)
                        import random

                        retry_delay = random.randint(8000, 15000)
                        logger.info(
                            "waiting_before_retry",
                            worker_id=worker_id,
                            delay_ms=retry_delay,
                        )
                        await page.wait_for_timeout(retry_delay)

                        # Navigate to blank first to reset page state
                        try:
                            await page.goto(
                                "about:blank",
                                wait_until="domcontentloaded",
                                timeout=5000,
                            )
                        except:
                            pass  # Ignore errors when going to blank

                        await page.wait_for_timeout(2000)

                        # Try goto again with different wait strategy
                        await page.goto(selling_url, wait_until="load", timeout=30000)
                        await page.wait_for_timeout(5000)
                        logger.info(
                            "buff_retry_succeeded", worker_id=worker_id, url=selling_url
                        )
                    except Exception as retry_error:
                        logger.error(
                            "buff_navigation_retry_failed",
                            worker_id=worker_id,
                            url=selling_url,
                            error=str(retry_error)[:150],
                        )
                        return None
                else:
                    logger.error(
                        "buff_navigation_error", url=selling_url, error=error_msg[:150]
                    )
                    return None

            # Extract selling items
            selling_items, total_volume = await self.extract_selling_items(page)

            if not selling_items:
                logger.warning("no_buff_selling_items", item=item_name)
                return None

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
                "total_volume": total_volume,  # Total items in market
                "volume_24h": len(trade_records),
            }

        except Exception as e:
            logger.error("buff_extraction_error", error=str(e), url=buff_url)
            return None

    async def extract_selling_items(self, page: Page) -> tuple[List[Dict], int]:
        """Extract current BUFF selling listings with production selectors.
        Returns: (selling_items, total_volume)
        """
        selling_items = []
        total_volume = 0

        try:
            # Wait for table to load (use real selector from working version)
            try:
                await page.wait_for_selector("tr.selling", timeout=15000)
            except PlaywrightTimeout:
                logger.warning("no_selling_rows_trying_generic_selector")
                try:
                    await page.wait_for_selector("table tbody tr", timeout=10000)
                except PlaywrightTimeout:
                    logger.error("no_buff_table_found")
                    return [], 0

            # Calculate total volume from pagination
            try:
                # Wait a bit for pagination to load
                await page.wait_for_timeout(1000)

                # Check if pagination exists - look for page links
                page_links = await page.locator("div.pager a.page-link").all()

                if len(page_links) > 0:
                    # Get all page numbers from links
                    max_page = 1
                    for link in page_links:
                        href = await link.get_attribute("href")
                        if href and "#page_num=" in href:
                            try:
                                page_num = int(href.split("#page_num=")[-1])
                                max_page = max(max_page, page_num)
                            except ValueError:
                                continue

                    # Get current page rows to know items per page
                    current_rows = await page.locator("tr.selling").all()
                    items_per_page = len(current_rows) if current_rows else 10
                    total_volume = max_page * items_per_page
                    logger.info(
                        "buff_total_calculated_from_pagination",
                        pages=max_page,
                        per_page=items_per_page,
                        total=total_volume,
                    )
                else:
                    # No pagination, just count current rows
                    current_rows = await page.locator("tr.selling").all()
                    total_volume = len(current_rows)
                    logger.info("no_pagination_found", total=total_volume)
            except Exception as e:
                logger.warning("pagination_calculation_failed", error=str(e))
                # Fallback: count current rows
                current_rows = await page.locator("tr.selling").all()
                total_volume = len(current_rows)

            # Get rows for price extraction (first page only)
            rows = await page.locator("tr.selling").all()
            logger.debug("buff_rows_located", count=len(rows))

            if len(rows) == 0:
                logger.warning("no_selling_rows_using_generic")
                rows = await page.locator("table tbody tr").all()
                if total_volume == 0:
                    total_volume = len(rows)

            rows_to_process = rows[
                :25
            ]  # Get up to 25 cheapest listings for price calculation

            logger.info("buff_extracting_prices", rows_to_process=len(rows_to_process))

            for idx, row in enumerate(rows_to_process):
                try:
                    logger.debug("buff_processing_row", row_index=idx)

                    # Extract price in CNY (¥ symbol) with timeout
                    price_element = row.locator("strong.f_Strong")
                    price_text = await price_element.inner_text(
                        timeout=5000
                    )  # 5s timeout

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
                        logger.debug(
                            "buff_price_extracted", row_index=idx, price=price_cny
                        )

                except Exception as e:
                    logger.debug("buff_item_parse_error", row=idx, error=str(e))
                    continue

        except Exception as e:
            logger.error("buff_selling_extraction_error", error=str(e))

        return selling_items, total_volume

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
