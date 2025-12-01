"""
Item extractor with real CSS selectors from production.
Parses and structures item data from HTML table.
"""

import asyncio
import re
from datetime import datetime, timezone
from playwright.async_api import Page
from typing import List, Optional

from app.core.logger import get_logger
from app.domain.models import Skin

logger = get_logger(__name__)


class ItemExtractor:
    """Extracts and parses items from result table with production selectors."""

    def __init__(self):
        pass

    async def extract_items(self, page: Page, url: str, limit: Optional[int] = None) -> List[Skin]:
        """Extract items from the table, optionally limiting the number of results."""
        items: List[Skin] = []
        timestamp = datetime.now(timezone.utc)

        try:
            # Wait longer to ensure table loaded
            await page.wait_for_timeout(5000)

            logger.info("analyzing_page_structure")

            # Get HTML for analysis
            content = await page.content()

            # Attempt to extract data from multiple possible structures
            rows = await self._find_table_rows(page)

            logger.info("found_rows", count=len(rows))

            # PARALLELIZE ITEM EXTRACTION
            logger.info("extracting_items_parallel")

            # Apply limit if specified
            rows_to_process = rows[:limit] if limit else rows
            logger.info("processing_limited_rows", total=len(rows), processing=len(rows_to_process))

            # Create parallel tasks to process all rows
            tasks = [
                self._extract_single_item(row, idx, timestamp)
                for idx, row in enumerate(rows_to_process)
            ]

            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter valid results
            valid_item_count = 0
            for idx, result in enumerate(results):
                # If exception occurred, log and continue
                if isinstance(result, Exception):
                    logger.warning("extraction_error", item_index=idx, error=str(result))
                    continue

                # If item is valid, add it
                if result:
                    valid_item_count += 1
                    items.append(result)

            # If no items found, save snapshot for debugging
            if len(items) == 0:
                logger.warning("no_items_found_check_selectors")

        except Exception as e:
            logger.error("extraction_failed", error=str(e))
            raise

        return items

    async def _find_table_rows(self, page: Page):
        """Find table rows using production selector for steamdt.com."""
        # More specific selector for steamdt.com - only visible rows
        selector = ".el-table__body .el-table__row"

        try:
            # Get ONLY rows that are visible in the viewport
            rows = await page.locator(selector).all()

            # Filter only those with valid content (at least 6 cells)
            valid_rows = []
            for idx, row in enumerate(rows):
                cells = await row.locator("td").all()
                if len(cells) >= 6:
                    valid_rows.append(row)
                elif idx < 5:  # Debug: first 5 rows
                    logger.debug("row_discarded_insufficient_cells", row_index=idx, cell_count=len(cells))

            logger.info("selector_results", selector=selector, total_rows=len(rows), valid_rows=len(valid_rows))

            # If no valid rows, try with alternative selector
            if len(valid_rows) == 0 and len(rows) > 0:
                logger.warning("no_valid_rows_trying_unfiltered")
                # Try directly with rows without filtering by cell count
                valid_rows = rows

            return valid_rows

        except Exception as e:
            logger.error("row_search_failed", error=str(e))
            return []

    async def _extract_single_item(self, row, idx: int, timestamp: datetime) -> Optional[Skin]:
        """Extract a single item from a table row."""
        try:
            # Extract all cells (td) from row
            cells = await row.locator("td").all()

            if len(cells) < 6:
                if idx < 3:  # Debug: first 3 rows
                    logger.debug("insufficient_cells", row_index=idx, cell_count=len(cells))
                return None

            # Column structure:
            # 0: Ranking
            # 1: Item name + URL
            # 2: BUFF - Buy price + time + LINK
            # 3: STEAM - Sell price + time + LINK
            # 4: Net sell price
            # 5: Volume/Sales
            # 6: Buy/sell ratio
            # 7: Second ratio
            # 8: Actions

            # Extract name and URL
            item_data = await self._extract_item_name_and_url(cells, idx)
            if not item_data:
                if idx < 3:
                    logger.debug("name_extraction_failed", row_index=idx)
                return None

            item_name, item_url, item_quality, is_stattrak = item_data

            # VALIDATION FILTERS

            # 1. IGNORE STICKERS
            if item_name.lower().startswith("sticker"):
                logger.debug("skipping_sticker", name=item_name)
                return None

            # 2. IGNORE MUSIC KITS
            if "music kit" in item_name.lower():
                logger.debug("skipping_music_kit", name=item_name)
                return None

            # 3. MUST CONTAIN | (pipes) to be valid weapon/skin
            # This excludes: pins, cases, keys, patches, etc.
            if "|" not in item_name:
                logger.debug("skipping_no_pipe", name=item_name)
                return None

            # Extract BUFF and Steam URLs from row
            buff_url = await self._extract_platform_url(cells, 2, "buff.163.com")
            steam_url = await self._extract_platform_url(cells, 3, "steamcommunity.com/market/listings")

            # Create Skin object (Pydantic model)
            skin = Skin(
                name=item_name,
                quality=item_quality,
                stattrak=is_stattrak,
                item_url=item_url,
                buff_url=buff_url,
                steam_url=steam_url,
            )

            return skin

        except Exception as e:
            if idx < 3:
                logger.debug("row_processing_error", row_index=idx, error=str(e))
            return None

    async def _extract_item_name_and_url(self, cells, idx: int):
        """Extract item name, URL, quality, and StatTrak status."""
        try:
            name_cell = cells[1] if len(cells) > 1 else None
            if not name_cell:
                return None

            # Find <a> link containing full name
            name_link_element = name_cell.locator("a").first
            item_name = await name_link_element.inner_text()
            item_name = item_name.strip()

            # Extract item URL
            item_url = await name_link_element.get_attribute("href")
            if item_url and not item_url.startswith("http"):
                item_url = f"https://steamdt.com{item_url}"

            # Detect StatTrak™
            is_stattrak = "StatTrak™" in item_name or "stattrak" in item_name.lower()

            # Extract quality (everything in parentheses at the end)
            item_quality = None
            quality_match = re.search(r"\(([^)]+)\)$", item_name)
            if quality_match:
                item_quality = quality_match.group(1)
                # Remove quality from item name
                item_name = re.sub(r"\s*\([^)]+\)$", "", item_name).strip()

            return (item_name, item_url, item_quality, is_stattrak)

        except Exception as e:
            logger.debug("name_extraction_error", row_index=idx, error=str(e))
            return None

    async def _extract_platform_url(self, cells, cell_idx: int, url_pattern: str) -> Optional[str]:
        """Extract platform URL from specific cell."""
        try:
            cell = cells[cell_idx] if len(cells) > cell_idx else None
            if not cell:
                return None

            # Find <a> link containing URL pattern
            link = cell.locator(f'a[href*="{url_pattern}"]').first
            url = await link.get_attribute("href")
            return url

        except Exception as e:
            logger.debug("url_extraction_error", cell_index=cell_idx, pattern=url_pattern, error=str(e))
            return None
