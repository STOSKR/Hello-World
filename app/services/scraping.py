"""
Scraping service with Clean Architecture.
Integrates all extractors, filters, and utilities with production selectors.
"""

import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Dict

from app.core.logger import get_logger
from app.core.config import Settings
from app.domain.models import ScrapedItem
from app.services.extractors import ItemExtractor, DetailedItemExtractor
from app.services.filters import FilterManager
from app.services.utils import BrowserManager, FileSaver

logger = get_logger(__name__)


class ScrapingService:
    """Main scraping service with producer-consumer pattern and real extractors."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.item_extractor = ItemExtractor()
        self.detailed_extractor = DetailedItemExtractor()
        self.filter_manager = FilterManager(settings)
        self.file_saver = FileSaver(settings)

    async def scrape_items(
        self,
        limit: Optional[int] = None,
        concurrent_workers: Optional[int] = None,
        exclusion_filters: Optional[List[str]] = None,
    ) -> tuple[List[ScrapedItem], List[Dict]]:
        """
        Scrape items using producer-consumer pattern with real extractors.

        Args:
            limit: Maximum number of items to scrape
            concurrent_workers: Number of concurrent workers for detailed scraping
            exclusion_filters: List of name prefixes to exclude (e.g., ["Charm |"])

        Returns:
            List of scraped items with market data
        """
        workers = concurrent_workers or self.settings.max_concurrent
        filters = (
            exclusion_filters or []
        )  # Default: no additional exclusions (hardcoded in ItemExtractor)

        logger.info(
            "scrape_started",
            limit=limit,
            workers=workers,
            exclusion_filters=filters,
        )

        results: List[ScrapedItem] = []
        discarded_items: List[Dict] = []  # Items descartados con motivo
        total_to_process = 0  # Will be set by producer

        async with BrowserManager(headless=self.settings.headless) as browser:
            page = browser.get_page()

            # Navigate to target URL
            await browser.navigate(self.settings.target_url)

            # Configure web filters (currency, price, volume, platforms)
            await self.filter_manager.configure_all_filters(page)

            # Save debug files if enabled
            await self.file_saver.save_debug_files(page)

            # Pre-create pages for each worker with controlled delays
            worker_pages = []  # List of (buff_page, steam_page) tuples
            logger.info("precreating_worker_pages", count=workers)

            for worker_id in range(workers):
                if worker_id > 0:
                    # Staggered page creation to avoid simultaneous BUFF navigation
                    delay = worker_id * 5000  # 5 seconds between workers
                    logger.info(
                        "page_creation_delay", worker_id=worker_id, delay_ms=delay
                    )
                    await asyncio.sleep(delay / 1000)

                buff_page = await page.context.new_page()
                steam_page = await page.context.new_page()
                worker_pages.append((buff_page, steam_page))
                logger.info("worker_pages_created", worker_id=worker_id)

            logger.info("all_worker_pages_created", total=len(worker_pages))

            # Producer-consumer pattern
            item_queue: asyncio.Queue[Dict] = asyncio.Queue()

            # Producer task: extract item list and apply filters
            async def producer():
                """Read table and add filtered items to queue."""
                logger.info("producer_started")
                items = await self.item_extractor.extract_items(
                    page, self.settings.target_url, limit=limit
                )
                logger.info("items_extracted_from_table", total=len(items))

                # Apply exclusion filters
                filtered_items = [
                    item
                    for item in items
                    if not any(
                        item["item_name"].startswith(prefix) for prefix in filters
                    )
                ]

                logger.info(
                    "exclusion_filters_applied",
                    before=len(items),
                    after=len(filtered_items),
                    excluded=len(items) - len(filtered_items),
                )

                # Add to queue
                for item in filtered_items:
                    await item_queue.put(item)

                # Signal end of production
                for _ in range(workers):
                    await item_queue.put(None)

                logger.info("producer_finished", items_queued=len(filtered_items))

                # Store total for consumers
                nonlocal total_to_process
                total_to_process = len(filtered_items)

            # Consumer task: scrape detailed data
            async def consumer(worker_id: int):
                """Process items from queue with detailed scraping."""
                logger.info("consumer_started", worker_id=worker_id)
                processed = 0

                # Get pre-created pages for this worker
                buff_page, steam_page = worker_pages[worker_id]

                while True:
                    item = await item_queue.get()

                    # None signals end of queue
                    if item is None:
                        item_queue.task_done()
                        break

                    try:
                        # Log which worker is processing this item
                        logger.info(
                            "worker_processing_item",
                            worker_id=worker_id,
                            item=item["item_name"],
                        )

                        # Scrape BUFF and Steam data using real extractors
                        # Pass pre-created pages for full parallelism
                        detailed_data = (
                            await self.detailed_extractor.extract_detailed_item(
                                page,
                                item,
                                buff_page=buff_page,
                                steam_page=steam_page,
                                worker_id=worker_id,
                            )
                        )

                        if detailed_data:
                            # Check if item was discarded
                            if detailed_data.get("discarded"):
                                discarded_items.append(detailed_data)
                                # Show discard reason in console
                                quality_str = (
                                    f" ({detailed_data.get('quality')})"
                                    if detailed_data.get("quality")
                                    else ""
                                )
                                stattrak_str = (
                                    "ST " if detailed_data.get("stattrak") else ""
                                )
                                logger.info(
                                    "item_discarded_output",
                                    worker_id=worker_id,
                                    item=f"{stattrak_str}{item['item_name']}{quality_str}",
                                    reason=detailed_data.get("discard_reason"),
                                )
                            else:
                                # Create ScrapedItem from dict (ONLY Pydantic validation here)
                                scraped_item = ScrapedItem(
                                    **detailed_data,
                                    scraped_at=datetime.now(timezone.utc),
                                )

                                results.append(scraped_item)
                                processed += 1

                                # Log progress
                                quality_str = (
                                    f" ({detailed_data.get('quality')})"
                                    if detailed_data.get("quality")
                                    else ""
                                )
                                stattrak_str = (
                                    "ST " if detailed_data.get("stattrak") else ""
                                )

                                logger.info(
                                    "item_scraped_success",
                                    worker_id=worker_id,
                                    progress=f"[{processed}/{total_to_process}]",
                                    item=f"{stattrak_str}{item['item_name']}{quality_str}",
                                    buff_price=f"€{detailed_data['buff_avg_price_eur']:.2f}",
                                    steam_price=f"€{detailed_data['steam_avg_price_eur']:.2f}",
                                    roi=f"{detailed_data['profitability_ratio']:.1%}",
                                )

                        # Anti-ban delay
                        delay = self.settings.delay_between_items
                        random_delay = (
                            self.settings.random_delay_max
                            + self.settings.random_delay_min
                        ) / 2
                        await asyncio.sleep((delay + random_delay) / 1000)

                    except Exception as e:
                        logger.error(
                            "item_scraping_error",
                            worker_id=worker_id,
                            name=item["item_name"],
                            error=str(e),
                        )

                    finally:
                        item_queue.task_done()

                logger.info(
                    "consumer_finished", worker_id=worker_id, processed=processed
                )

            # Start producer and consumers
            producer_task = asyncio.create_task(producer())
            consumer_tasks = [asyncio.create_task(consumer(i)) for i in range(workers)]

            # Wait for all tasks to complete
            await producer_task
            await asyncio.gather(*consumer_tasks)

            # Cleanup pre-created worker pages
            logger.info("closing_worker_pages")
            for buff_page, steam_page in worker_pages:
                await buff_page.close()
                await steam_page.close()
            logger.info("worker_pages_closed")

        logger.info(
            "scrape_completed",
            total_items=len(results),
            discarded_items=len(discarded_items),
        )
        return results, discarded_items
