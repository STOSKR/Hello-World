"""
Detailed item extractor for navigating to individual items.
Extracts comprehensive data from BUFF and Steam.
"""

import re
from datetime import datetime, timezone
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from typing import Optional

from app.core.logger import get_logger
from app.domain.models import Skin, MarketData, PriceData
from app.domain.rules import calculate_fees, calculate_profit, calculate_roi

logger = get_logger(__name__)


class DetailedItemExtractor:
    """Extracts detailed data by navigating to each individual item."""

    def __init__(self):
        self.buff_timeout = 10000  # 10 seconds
        self.steam_timeout = 10000  # 10 seconds
        self.screenshot_counter = 0

    async def _save_screenshot(self, page: Page, step_name: str):
        """Save screenshot for debugging."""
        try:
            import os

            # Ensure directory exists
            os.makedirs("data/screenshots", exist_ok=True)

            self.screenshot_counter += 1
            # Clean filename (no special characters)
            clean_name = re.sub(r'[<>:"/\\|?*]', "_", step_name)
            filename = f"data/screenshots/step_{self.screenshot_counter:03d}_{clean_name}.png"
            await page.screenshot(path=filename, full_page=False)
            logger.info("screenshot_saved", filename=filename)
        except Exception as e:
            logger.warning("screenshot_error", error=str(e))

    async def extract_detailed_item(
        self,
        page: Page,
        skin: Skin,
    ) -> Optional[MarketData]:
        """Extract detailed market data for a skin."""
        logger.info("processing_item", name=skin.name)
        logger.info("item_urls", item_url=skin.item_url, buff_url=skin.buff_url, steam_url=skin.steam_url)

        try:
            # If URLs not provided, extract from steamdt.com
            buff_url = skin.buff_url
            steam_url = skin.steam_url

            if not buff_url or not steam_url:
                logger.info("extracting_urls_from_steamdt")
                await page.goto(skin.item_url, wait_until="networkidle", timeout=self.buff_timeout)
                await page.wait_for_timeout(5000)
                await self._save_screenshot(page, f"steamdt_{skin.name[:30]}")

                if not buff_url:
                    buff_url = await self._extract_buff_url(page)
                    if not buff_url:
                        logger.warning("buff_url_not_found", name=skin.name)
                        return None

                if not steam_url:
                    steam_url = await self._extract_steam_url(page)
                    if not steam_url:
                        logger.warning("steam_url_not_found", name=skin.name)
                        return None

            logger.info("platform_urls", buff_url=buff_url, steam_url=steam_url)

            # Navigate to BUFF and extract data
            buff_data = await self._extract_buff_data(page, buff_url, skin.name)
            if not buff_data:
                logger.info("item_discarded_buff_validation")
                return None

            await self._save_screenshot(page, f"buff_{skin.name[:30]}")

            # Navigate to Steam and extract data
            logger.info("navigating_to_steam")
            steam_data = await self._extract_steam_data(page, steam_url, skin.name)

            if not steam_data:
                logger.warning("steam_data_extraction_failed")
                return None

            logger.info("steam_data_extracted")
            await self._save_screenshot(page, f"steam_{skin.name[:30]}")

            # Calculate averages and profitability
            analysis = self._calculate_profitability(buff_data, steam_data)

            if not analysis:
                logger.warning("profitability_calculation_failed")
                return None

            # Create MarketData object
            market_data = MarketData(
                skin=skin,
                buff=PriceData(
                    avg_price_cny=analysis["buff_avg_price_cny"],
                    avg_price_eur=analysis["buff_avg_price_eur"],
                    selling_items_count=buff_data["selling_items_count"],
                    trade_records_count=buff_data["trade_records_count"],
                ),
                steam=PriceData(
                    avg_price_cny=analysis["steam_avg_price_cny"],
                    avg_price_eur=analysis["steam_avg_price_eur"],
                    selling_items_count=steam_data["selling_items_count"],
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

    def _calculate_profitability(self, buff_data: dict, steam_data: dict) -> Optional[dict]:
        """Calculate profitability metrics."""
        CNY_TO_EUR = 8.2  # Conversion rate CNY to EUR

        try:
            # Calculate average BUFF price in CNY
            buff_prices_cny = [
                float(item["price_cny"])
                for item in buff_data.get("selling_items", [])
                if item.get("price_cny")
            ]

            if not buff_prices_cny:
                logger.warning("no_valid_buff_prices")
                return None

            buff_avg_cny = sum(buff_prices_cny) / len(buff_prices_cny)
            buff_avg_eur = buff_avg_cny / CNY_TO_EUR

            # Calculate average Steam price in CNY (after fee 0.87)
            steam_prices_raw = [
                float(item["price_raw"])
                for item in steam_data.get("selling_items", [])
                if item.get("price_raw")
            ]

            if not steam_prices_raw:
                logger.warning("no_valid_steam_prices")
                return None

            # Average Steam price (before fee)
            steam_avg_cny_before_fee = sum(steam_prices_raw) / len(steam_prices_raw)

            # Apply Steam fee (0.87 = seller receives 87%)
            steam_avg_cny = steam_avg_cny_before_fee * 0.87
            steam_avg_eur = steam_avg_cny / CNY_TO_EUR

            # Calculate profitability
            # Profitability = (Steam sell price - BUFF buy price) / BUFF buy price
            profitability_ratio = (steam_avg_eur - buff_avg_eur) / buff_avg_eur if buff_avg_eur > 0 else 0
            profit_eur = steam_avg_eur - buff_avg_eur

            return {
                "buff_avg_price_cny": round(buff_avg_cny, 2),
                "buff_avg_price_eur": round(buff_avg_eur, 2),
                "steam_avg_price_cny": round(steam_avg_cny, 2),
                "steam_avg_price_eur": round(steam_avg_eur, 2),
                "profitability_ratio": profitability_ratio,
                "profit_eur": round(profit_eur, 2),
            }

        except Exception as e:
            logger.error("profitability_calculation_error", error=str(e))
            return None

    async def _extract_buff_url(self, page: Page) -> Optional[str]:
        """Extract BUFF URL from page."""
        try:
            buff_link = page.locator('a[href*="buff.163.com"]').first
            buff_url = await buff_link.get_attribute("href")
            return buff_url
        except Exception as e:
            logger.debug("buff_url_extraction_error", error=str(e))
            return None

    async def _extract_steam_url(self, page: Page) -> Optional[str]:
        """Extract Steam URL from page."""
        try:
            steam_link = page.locator('a[href*="steamcommunity.com/market/listings"]').first
            steam_url = await steam_link.get_attribute("href")
            return steam_url
        except Exception as e:
            logger.debug("steam_url_extraction_error", error=str(e))
            return None

    async def _extract_buff_data(self, page: Page, buff_url: str, item_name: str) -> Optional[dict]:
        """Extract data from BUFF marketplace."""
        try:
            # Navigate to BUFF tab=selling (items for sale)
            logger.info("navigating_to_buff_selling")
            base_url = buff_url.split("#")[0].split("?")[0]
            selling_url = f"{base_url}?from=market#tab=selling"

            try:
                await page.goto(selling_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(5000)
            except PlaywrightTimeout:
                logger.error("buff_selling_timeout")
                return None

            # Extract 5 cheapest items for sale
            selling_items = await self._extract_buff_selling_items(page)

            if not selling_items:
                logger.warning("no_buff_selling_items")
                return None

            logger.info("buff_selling_items_found", count=len(selling_items))

            # Navigate to BUFF tab=history (trade records)
            logger.info("navigating_to_trade_records")
            history_url = f"{base_url}?from=market#tab=history"

            logger.info("trade_records_url", url=history_url)
            try:
                await page.goto(history_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(5000)
            except PlaywrightTimeout:
                logger.warning("trade_records_timeout_continuing_without")
                trade_records = []
                return {
                    "selling_items": selling_items,
                    "selling_items_count": len(selling_items),
                    "trade_records": trade_records,
                    "trade_records_count": 0,
                }

            trade_records = await self._extract_buff_trade_records(page)

            if not trade_records:
                logger.warning("no_trade_records_found")
                trade_records = []
            else:
                logger.info("trade_records_found", count=len(trade_records))

            # Validate: If last 5 sales are 10% higher than current prices, discard
            should_discard = self._validate_price_difference(selling_items, trade_records)

            if should_discard:
                logger.info("item_discarded_recent_sales_10percent_higher")
                return None

            return {
                "selling_items": selling_items,
                "selling_items_count": len(selling_items),
                "trade_records": trade_records,
                "trade_records_count": len(trade_records),
            }

        except PlaywrightTimeout:
            logger.error("buff_timeout")
            return None
        except Exception as e:
            logger.error("buff_extraction_error", error=str(e))
            return None

    async def _extract_buff_selling_items(self, page: Page) -> list[dict]:
        """Extract selling items from BUFF."""
        selling_items = []

        try:
            logger.info("waiting_for_selling_items_table")
            try:
                await page.wait_for_selector("tr.selling", timeout=15000)
            except Exception as e:
                logger.warning("tr_selling_not_found", error=str(e))
                try:
                    await page.wait_for_selector("table tbody tr", timeout=10000)
                    logger.info("using_generic_table_selector")
                except Exception as e2:
                    logger.error("no_table_found", error=str(e2))
                    return []

            rows = await page.locator("tr.selling").all()

            if len(rows) == 0:
                logger.warning("no_rows_with_tr_selling_trying_generic")
                rows = await page.locator("table tbody tr").all()

            logger.info("rows_found", total=len(rows))
            rows_to_process = rows[:5]

            for idx, row in enumerate(rows_to_process):
                try:
                    # Extract price (find CNY price with ¥ symbol)
                    price_element = row.locator("strong.f_Strong")
                    price_text = await price_element.inner_text()

                    # Clean price: "¥ 10.8" -> "10.8"
                    price_clean = re.sub(r"[¥\s]", "", price_text).strip()

                    # Extract EUR price if available
                    eur_price = None
                    try:
                        eur_element = row.locator("span.c_Gray.f_12px")
                        eur_text = await eur_element.inner_text()
                        eur_match = re.search(r"€\s*([\d.]+)", eur_text)
                        if eur_match:
                            eur_price = eur_match.group(1)
                    except:
                        pass

                    # Extract wear (paintwear)
                    wear = None
                    try:
                        wear_element = row.locator("div.wear-value")
                        wear_text = await wear_element.inner_text()
                        wear_match = re.search(r"([\d.]+)", wear_text)
                        if wear_match:
                            wear = wear_match.group(1)
                    except:
                        pass

                    # Extract seller
                    seller = None
                    try:
                        seller_element = row.locator("span.user-name")
                        seller = await seller_element.inner_text()
                    except:
                        pass

                    selling_items.append({
                        "position": idx + 1,
                        "price_cny": price_clean,
                        "price_eur": eur_price,
                        "wear": wear,
                        "seller": seller,
                    })

                except Exception as e:
                    logger.debug("selling_item_extraction_error", index=idx, error=str(e))
                    continue

        except PlaywrightTimeout:
            logger.warning("timeout_waiting_buff_selling_items")
        except Exception as e:
            logger.error("selling_items_extraction_error", error=str(e))

        return selling_items

    async def _extract_buff_trade_records(self, page: Page) -> list[dict]:
        """Extract trade records from BUFF."""
        trade_records = []

        try:
            logger.info("waiting_for_trade_records_table")
            await page.wait_for_timeout(5000)

            logger.info("searching_trade_records_table")

            try:
                await page.wait_for_selector("tbody.list_tb_csgo tr", timeout=15000)
                all_rows = await page.locator("tbody.list_tb_csgo tr").all()
                logger.info("total_rows_found", count=len(all_rows))

                # Filter rows that are NOT header (have td, not th)
                data_rows = []
                for row in all_rows:
                    td_count = await row.locator("td").count()
                    th_count = await row.locator("th").count()

                    if td_count > 0 and th_count == 0:
                        data_rows.append(row)

                logger.info("data_rows_found_without_header", count=len(data_rows))

                if len(data_rows) == 0:
                    logger.warning("no_data_rows_in_trade_records")
                    return []

                all_rows = data_rows

            except Exception as e:
                logger.warning("trade_records_table_not_found", error=str(e))
                try:
                    await page.screenshot(path="data/screenshots/debug_no_trade_table.png")
                    logger.info("debug_screenshot_saved", filename="debug_no_trade_table.png")
                    html_content = await page.content()
                    with open("data/screenshots/debug_page_content.html", "w", encoding="utf-8") as f:
                        f.write(html_content)
                    logger.info("debug_html_saved", filename="debug_page_content.html")
                except:
                    pass
                return []

            logger.info("processing_data_rows", count=len(all_rows))

            records_to_process = all_rows[:5]

            for idx, row in enumerate(records_to_process):
                try:
                    price_cny = None
                    price_eur = None
                    date_text = None

                    cells = await row.locator("td").all()

                    if len(cells) < 6:
                        logger.warning("insufficient_cells_in_row", row=idx + 1, cells=len(cells))
                        continue

                    # Cell 3 (index 3): Price
                    try:
                        price_cell = cells[3]
                        price_strong = await price_cell.locator("strong.f_Strong").inner_text()
                        price_text = price_strong.replace("¥", "").strip()
                        price_match = re.search(r"([\d]+(?:\.[\d]+)?)", price_text)
                        if price_match:
                            price_cny = price_match.group(1)

                        try:
                            eur_span = await price_cell.locator("p.hide-cny span").inner_text()
                            eur_match = re.search(r"€\s*([\d.]+)", eur_span)
                            if eur_match:
                                price_eur = eur_match.group(1)
                        except:
                            pass
                    except Exception as e:
                        logger.warning("price_extraction_error", row=idx + 1, error=str(e))

                    # Cell 5 (index 5): Date
                    try:
                        date_cell = cells[5]
                        date_text = await date_cell.inner_text()
                        date_text = date_text.strip()
                    except:
                        pass

                    if price_cny:
                        trade_records.append({
                            "position": idx + 1,
                            "price_cny": price_cny,
                            "price_eur": price_eur,
                            "date": date_text,
                        })
                        logger.info(
                            "trade_record_extracted",
                            record=idx + 1,
                            price_cny=price_cny,
                            price_eur=price_eur or "N/A",
                            date=date_text or "No date",
                        )
                    else:
                        logger.warning("no_price_in_row", row=idx + 1)

                except Exception as e:
                    logger.warning("trade_record_extraction_error", record=idx + 1, error=str(e))
                    continue

            logger.info("trade_records_extracted", count=len(trade_records))

        except Exception as e:
            logger.warning("trade_records_extraction_error", error=str(e))

        return trade_records

    def _validate_price_difference(self, selling_items: list[dict], trade_records: list[dict]) -> bool:
        """Validate if recent sales are significantly lower than current prices."""
        if not selling_items or not trade_records:
            return False

        try:
            # Calculate average current selling price (CNY)
            selling_prices = [float(item["price_cny"]) for item in selling_items if item.get("price_cny")]
            if not selling_prices:
                return False

            avg_selling_price = sum(selling_prices) / len(selling_prices)

            # Calculate average recent trade price (CNY)
            trade_prices = [float(record["price_cny"]) for record in trade_records if record.get("price_cny")]
            if not trade_prices:
                return False

            avg_trade_price = sum(trade_prices) / len(trade_prices)

            # If recent sales are 10% or MORE LOWER, discard (price falling)
            if avg_trade_price <= avg_selling_price * 0.90:
                logger.info(
                    "price_falling_detected",
                    recent_avg=f"{avg_trade_price:.2f}",
                    current_avg=f"{avg_selling_price:.2f}",
                )
                return True

            logger.info(
                "price_validation_ok",
                current_avg=f"{avg_selling_price:.2f}",
                recent_avg=f"{avg_trade_price:.2f}",
            )
            return False

        except Exception as e:
            logger.warning("price_validation_error", error=str(e))
            return False

    async def _extract_steam_data(self, page: Page, steam_url: str, item_name: str) -> Optional[dict]:
        """Extract data from Steam marketplace."""
        try:
            logger.info("navigating_to_steam")
            await page.goto(steam_url, wait_until="domcontentloaded", timeout=self.steam_timeout)
            await page.wait_for_timeout(5000)

            # Extract first items for sale
            selling_items = await self._extract_steam_selling_items(page)

            if not selling_items:
                logger.warning("no_steam_selling_items")
                return None

            logger.info("steam_selling_items_found", count=len(selling_items))

            return {
                "selling_items": selling_items,
                "selling_items_count": len(selling_items),
            }

        except PlaywrightTimeout:
            logger.error("steam_timeout")
            return None
        except Exception as e:
            logger.error("steam_extraction_error", error=str(e))
            return None

    async def _extract_steam_selling_items(self, page: Page) -> list[dict]:
        """Extract selling items from Steam."""
        selling_items = []

        try:
            await page.wait_for_selector(".market_listing_row", timeout=10000)

            all_rows = await page.locator(".market_listing_row").all()

            logger.info("steam_rows_found", count=len(all_rows))

            # Process rows until we find 5 valid ones
            for idx, row in enumerate(all_rows):
                if len(selling_items) >= 5:
                    break

                try:
                    # Check if item is sold
                    row_text = await row.inner_text()

                    if "已售出" in row_text or "Sold!" in row_text:
                        logger.debug("row_sold_skipping", row=idx + 1)
                        continue

                    # Extract price
                    price_element = row.locator(".market_listing_price.market_listing_price_with_fee").first

                    if await price_element.count() == 0:
                        logger.debug("row_no_price_skipping", row=idx + 1)
                        continue

                    price_text = await price_element.inner_text()

                    # Clean price: "¥ 18.48" -> "18.48"
                    price_clean = re.sub(r"[¥€$\s]", "", price_text).strip()

                    if not price_clean or price_clean == "":
                        logger.debug("row_empty_price_skipping", row=idx + 1)
                        continue

                    selling_items.append({
                        "position": len(selling_items) + 1,
                        "price": price_text.strip(),
                        "price_raw": price_clean,
                    })

                    logger.debug("steam_item_added", item=len(selling_items), price=price_text.strip())

                except Exception as e:
                    logger.debug("row_extraction_error_skipping", row=idx, error=str(e))
                    continue

            logger.info("steam_valid_items_extracted", count=len(selling_items))

        except PlaywrightTimeout:
            logger.warning("steam_items_timeout")
        except Exception as e:
            logger.error("steam_selling_items_error", error=str(e))

        return selling_items
