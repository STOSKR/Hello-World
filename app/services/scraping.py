"""
Scraping service with Clean Architecture.
Integrates all extractors, filters, and utilities with production selectors.
"""

import asyncio
import random
from datetime import datetime, timezone
from typing import List, Optional, Dict

from app.core.logger import get_logger
from app.core.config import Settings
from app.domain.models import ScrapedItem
from app.services.extractors import ItemExtractor, DetailedItemExtractor
from app.services.filters import FilterManager
from app.services.utils import BrowserManager, FileSaver

logger = get_logger(__name__)


def _format_item_display(item_name: str, quality: Optional[str], stattrak: bool) -> str:
    """Helper to format item display string with quality and StatTrak."""
    quality_str = f" ({quality})" if quality else ""
    stattrak_str = "ST " if stattrak else ""
    return f"{stattrak_str}{item_name}{quality_str}"


class ScrapingService:
    """Main scraping service with producer-consumer pattern and real extractors."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.item_extractor = ItemExtractor()
        self.detailed_extractor = DetailedItemExtractor(settings)
        self.filter_manager = FilterManager(settings)
        self.file_saver = FileSaver(settings)

    async def scrape_items(
        self,
        limit: Optional[int] = None,
        concurrent_workers: Optional[int] = None,
        storage_workers: Optional[int] = None,
        exclusion_filters: Optional[List[str]] = None,
        async_storage: bool = False,
    ) -> tuple[List[ScrapedItem], List[Dict]]:
        """
        Scrape items using specialized worker pattern.

        Architecture:
            - Producer: Extracts items from table
            - Scraper Workers: Navigate BUFF/Steam and extract detailed data
            - Storage Workers: Save scraped items to database (if async_storage=True)

        Args:
            limit: Maximum number of items to scrape
            concurrent_workers: Number of concurrent scraper workers
            storage_workers: Number of dedicated storage workers (default: 2)
            exclusion_filters: List of name prefixes to exclude (e.g., ["Charm |"])
            async_storage: If True, saves items to DB as they're scraped (requires StorageService)

        Returns:
            Tuple of (scraped_items, discarded_items)
        """
        scraper_workers = concurrent_workers or self.settings.max_concurrent
        db_workers = storage_workers or 2  # Default: 2 dedicated storage workers
        filters = exclusion_filters or []

        logger.info(
            "scrape_started",
            limit=limit,
            scraper_workers=scraper_workers,
            storage_workers=db_workers if async_storage else 0,
            exclusion_filters=filters,
            async_storage=async_storage,
        )

        results: List[ScrapedItem] = []
        discarded_items: List[Dict] = []
        total_to_process = 0

        # Storage setup if async mode enabled
        storage_queue: Optional[asyncio.Queue[Optional[ScrapedItem]]] = None
        storage_service = None
        if async_storage:
            from app.services.storage import StorageService

            storage_queue = asyncio.Queue()
            storage_service = StorageService()

        async with BrowserManager(headless=self.settings.headless) as browser:
            page = browser.get_page()
            await browser.navigate(self.settings.target_url)
            await self.filter_manager.configure_all_filters(page)
            await self.file_saver.save_debug_files(page)

            # Pre-create worker pages
            worker_pages = []
            logger.info("precreating_worker_pages", count=scraper_workers)
            for worker_id in range(scraper_workers):
                buff_page = await page.context.new_page()
                steam_page = await page.context.new_page()
                worker_pages.append((buff_page, steam_page))
                logger.info("worker_pages_created", worker_id=worker_id)
            logger.info("all_worker_pages_created", total=len(worker_pages))

            item_queue: asyncio.Queue[Optional[Dict]] = asyncio.Queue()
            total_to_process = 0  # Initialize before tasks start

            # Producer: extract and filter items
            async def producer():
                logger.info("producer_started")
                items = await self.item_extractor.extract_items(
                    page, self.settings.target_url, limit=limit
                )
                logger.info("items_extracted_from_table", total=len(items))

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

                # Set total BEFORE queuing to avoid race condition
                nonlocal total_to_process
                total_to_process = len(filtered_items)

                for item in filtered_items:
                    await item_queue.put(item)

                # Send sentinel values to stop scraper workers
                for _ in range(scraper_workers):
                    await item_queue.put(None)

                logger.info("producer_finished", items_queued=len(filtered_items))

            # Consumer: scrape detailed data
            async def consumer(worker_id: int):
                logger.info("consumer_started", worker_id=worker_id)
                processed = 0
                buff_page, steam_page = worker_pages[worker_id]

                while True:
                    item = await item_queue.get()
                    if item is None:
                        item_queue.task_done()
                        break

                    try:
                        logger.info(
                            "worker_processing_item",
                            worker_id=worker_id,
                            item=item["item_name"],
                        )

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
                            if detailed_data.get("discarded"):
                                discarded_items.append(detailed_data)
                                display_name = _format_item_display(
                                    item["item_name"],
                                    detailed_data.get("quality"),
                                    detailed_data.get("stattrak", False),
                                )
                                logger.info(
                                    "item_discarded_output",
                                    worker_id=worker_id,
                                    item=display_name,
                                    reason=detailed_data.get("discard_reason"),
                                )
                            else:
                                scraped_item = ScrapedItem(
                                    **detailed_data,
                                    scraped_at=datetime.now(timezone.utc),
                                )
                                results.append(scraped_item)
                                processed += 1

                                # Send to async storage if enabled
                                if async_storage and storage_queue:
                                    await storage_queue.put(scraped_item)

                                display_name = _format_item_display(
                                    item["item_name"],
                                    detailed_data.get("quality"),
                                    detailed_data.get("stattrak", False),
                                )
                                logger.info(
                                    "item_scraped_success",
                                    worker_id=worker_id,
                                    progress=f"[{processed}/{total_to_process}]",
                                    item=display_name,
                                    buff_price=f"€{detailed_data['buff_avg_price_eur']:.2f}",
                                    steam_price=f"€{detailed_data['steam_avg_price_eur']:.2f}",
                                    roi=f"{detailed_data['profitability_ratio']:.1%}",
                                )

                        # Anti-ban delay
                        delay = self.settings.delay_between_items
                        random_delay = random.randint(
                            self.settings.random_delay_min,
                            self.settings.random_delay_max,
                        )
                        total_delay_ms = delay + random_delay
                        logger.debug(
                            "anti_ban_wait",
                            worker_id=worker_id,
                            delay_ms=total_delay_ms,
                            message=f"Esperando {total_delay_ms}ms antes del siguiente item",
                        )
                        await asyncio.sleep(total_delay_ms / 1000)

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

            # Storage worker (only if async_storage enabled) - BATCH PROCESSING
            async def storage_worker(worker_id: int):
                """Dedicated storage worker with batch processing for better performance."""
                if not storage_queue or not storage_service:
                    return

                logger.info("storage_worker_started", worker_id=worker_id)
                saved_count = 0
                batch: List[ScrapedItem] = []

                while True:
                    item = await storage_queue.get()

                    if item is None:
                        # Flush remaining batch before stopping
                        if batch:
                            try:
                                await storage_service.save_items(batch)
                                saved_count += len(batch)
                                logger.info(
                                    "storage_batch_flushed",
                                    worker_id=worker_id,
                                    batch_size=len(batch),
                                    total_saved=saved_count,
                                )
                            except Exception as e:
                                logger.error(
                                    "storage_batch_error",
                                    worker_id=worker_id,
                                    batch_size=len(batch),
                                    error=str(e),
                                )
                            batch.clear()

                        storage_queue.task_done()
                        break

                    try:
                        batch.append(item)

                        # Flush batch when reaching batch size
                        from app.core.constants import STORAGE_BATCH_SIZE

                        if len(batch) >= STORAGE_BATCH_SIZE:
                            await storage_service.save_items(batch)
                            saved_count += len(batch)
                            logger.info(
                                "storage_batch_saved",
                                worker_id=worker_id,
                                batch_size=len(batch),
                                total_saved=saved_count,
                            )
                            batch.clear()

                    except Exception as e:
                        logger.error(
                            "storage_error",
                            worker_id=worker_id,
                            item=item.item_name,
                            error=str(e),
                        )
                    finally:
                        storage_queue.task_done()

                logger.info(
                    "storage_worker_finished",
                    worker_id=worker_id,
                    total_saved=saved_count,
                )

            # Start all tasks
            producer_task = asyncio.create_task(producer())

            # Scraper workers (navigate and extract data)
            scraper_tasks = [
                asyncio.create_task(consumer(i)) for i in range(scraper_workers)
            ]

            # Storage workers (save to database) - Multiple workers for better throughput
            storage_tasks = []
            if async_storage:
                storage_tasks = [
                    asyncio.create_task(storage_worker(i)) for i in range(db_workers)
                ]

            # Wait for scraping to complete
            await producer_task
            await asyncio.gather(*scraper_tasks)

            # Signal storage workers to stop and wait
            if async_storage and storage_queue and storage_tasks:
                for _ in range(db_workers):
                    await storage_queue.put(None)
                await asyncio.gather(*storage_tasks)

            # Cleanup worker pages
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
