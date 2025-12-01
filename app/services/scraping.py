"""
Scraping service with Clean Architecture.
Integrates all extractors, filters, and utilities with production selectors.
"""

import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from playwright.async_api import Page

from app.core.logger import get_logger
from app.core.config import Settings
from app.domain.models import Skin, MarketData, ScrapedItem
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
    ) -> List[ScrapedItem]:
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
        filters = exclusion_filters or ["Charm |"]  # Default exclusion

        logger.info(
            "scrape_started",
            limit=limit,
            workers=workers,
            exclusion_filters=filters,
        )

        results: List[ScrapedItem] = []

        async with BrowserManager(headless=self.settings.headless) as browser:
            page = browser.get_page()

            # Navigate to target URL
            await browser.navigate(self.settings.target_url)

            # Configure web filters (currency, price, volume, platforms)
            await self.filter_manager.configure_all_filters(page)

            # Save debug files if enabled
            await self.file_saver.save_debug_files(page)

            # Producer-consumer pattern
            item_queue: asyncio.Queue[Skin] = asyncio.Queue()

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
                    if not any(item.name.startswith(prefix) for prefix in filters)
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

            # Consumer task: scrape detailed data
            async def consumer(worker_id: int):
                """Process items from queue with detailed scraping."""
                logger.info("consumer_started", worker_id=worker_id)
                processed = 0

                while True:
                    skin = await item_queue.get()

                    # None signals end of queue
                    if skin is None:
                        item_queue.task_done()
                        break

                    try:
                        # Scrape BUFF and Steam data using real extractors
                        market_data = await self.detailed_extractor.extract_detailed_item(
                            page, skin
                        )

                        if market_data:
                            # Create ScrapedItem
                            scraped_item = ScrapedItem(
                                skin=skin,
                                market=market_data,
                                scraped_at=datetime.now(timezone.utc),
                            )

                            results.append(scraped_item)
                            processed += 1

                            logger.info(
                                "item_scraped",
                                worker_id=worker_id,
                                name=skin.name,
                                profit=market_data.profit_eur,
                                roi=f"{market_data.profitability_ratio:.2%}",
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
                            name=skin.name,
                            error=str(e),
                        )

                    finally:
                        item_queue.task_done()

                logger.info("consumer_finished", worker_id=worker_id, processed=processed)

            # Start producer and consumers
            producer_task = asyncio.create_task(producer())
            consumer_tasks = [asyncio.create_task(consumer(i)) for i in range(workers)]

            # Wait for all tasks to complete
            await producer_task
            await asyncio.gather(*consumer_tasks)

        logger.info("scrape_completed", total_items=len(results))
        return results
