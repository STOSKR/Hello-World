"""Worker patterns for scraping service."""

import asyncio
import random
from datetime import datetime, timezone
from typing import List, Dict, Optional

from app.core.config import Settings
from app.core.constants import STORAGE_BATCH_SIZE
from app.core.logger import get_logger
from app.domain.models import ScrapedItem
from app.services.extractors import DetailedItemExtractor
from app.services.storage import StorageService

logger = get_logger(__name__)


def format_item_display(item_name: str, quality: Optional[str], stattrak: bool) -> str:
    quality_str = f" ({quality})" if quality else ""
    stattrak_str = "ST " if stattrak else ""
    return f"{stattrak_str}{item_name}{quality_str}"


class Producer:
    """Extracts items from table and queues them for processing."""

    def __init__(self, item_extractor, exclusion_filters: List[str]):
        self.item_extractor = item_extractor
        self.exclusion_filters = exclusion_filters

    async def run(
        self,
        page,
        target_url: str,
        item_queue: asyncio.Queue,
        limit: Optional[int],
        scraper_workers: int,
    ) -> int:
        items = await self.item_extractor.extract_items(page, target_url, limit=limit)
        logger.info("items_extracted", total=len(items))

        filtered_items = [
            item
            for item in items
            if not any(
                item["item_name"].startswith(prefix)
                for prefix in self.exclusion_filters
            )
        ]

        excluded = len(items) - len(filtered_items)
        if excluded > 0:
            logger.info("exclusion_filters_applied", excluded=excluded)

        for item in filtered_items:
            await item_queue.put(item)

        for _ in range(scraper_workers):
            await item_queue.put(None)

        logger.info("producer_finished", items_queued=len(filtered_items))
        return len(filtered_items)


class ScraperWorker:
    """Scrapes detailed item data from BUFF and Steam."""

    def __init__(
        self,
        settings: Settings,
        detailed_extractor: DetailedItemExtractor,
        page,
        buff_page,
        steam_page,
    ):
        self.settings = settings
        self.detailed_extractor = detailed_extractor
        self.page = page
        self.buff_page = buff_page
        self.steam_page = steam_page

    async def run(
        self,
        worker_id: int,
        item_queue: asyncio.Queue,
        storage_queue: Optional[asyncio.Queue],
        results: List[ScrapedItem],
        discarded_items: List[Dict],
        total_to_process: int,
    ):
        logger.info("consumer_started", worker_id=worker_id)
        processed = 0

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

                detailed_data = await self.detailed_extractor.extract_detailed_item(
                    self.page,
                    item,
                    buff_page=self.buff_page,
                    steam_page=self.steam_page,
                    worker_id=worker_id,
                )

                if detailed_data:
                    if detailed_data.get("discarded"):
                        discarded_items.append(detailed_data)
                        display_name = format_item_display(
                            item["item_name"],
                            detailed_data.get("quality"),
                            detailed_data.get("stattrak", False),
                        )
                        logger.info(
                            "item_discarded",
                            worker_id=worker_id,
                            item=display_name,
                            reason=detailed_data.get("discard_reason"),
                        )
                    else:
                        scraped_item = ScrapedItem(
                            **detailed_data, scraped_at=datetime.now(timezone.utc)
                        )
                        results.append(scraped_item)
                        processed += 1

                        if storage_queue:
                            await storage_queue.put(scraped_item)

                        display_name = format_item_display(
                            item["item_name"],
                            detailed_data.get("quality"),
                            detailed_data.get("stattrak", False),
                        )
                        logger.info(
                            "item_scraped",
                            worker_id=worker_id,
                            progress=f"{processed}/{total_to_process}",
                            item=display_name,
                            buff=f"€{detailed_data['buff_avg_price_eur']:.2f}",
                            steam=f"€{detailed_data['steam_avg_price_eur']:.2f}",
                            roi=f"{detailed_data['profitability_ratio']:.1%}",
                        )

                await self._apply_delay()

            except Exception as e:
                logger.error(
                    "item_error",
                    worker_id=worker_id,
                    name=item["item_name"],
                    error=str(e),
                )
            finally:
                item_queue.task_done()

        logger.info("consumer_finished", worker_id=worker_id, processed=processed)

    async def _apply_delay(self):
        delay = self.settings.delay_between_items
        random_delay = random.randint(
            self.settings.random_delay_min, self.settings.random_delay_max
        )
        total_delay_ms = delay + random_delay
        await asyncio.sleep(total_delay_ms / 1000)


class StorageWorker:
    """Saves scraped items to database in batches."""

    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service

    async def run(self, worker_id: int, storage_queue: asyncio.Queue):
        logger.info("storage_worker_started", worker_id=worker_id)
        saved_count = 0
        batch: List[ScrapedItem] = []

        while True:
            item = await storage_queue.get()

            if item is None:
                if batch:
                    await self._save_batch(batch, worker_id, saved_count)
                    saved_count += len(batch)
                    batch.clear()
                storage_queue.task_done()
                break

            try:
                batch.append(item)

                if len(batch) >= STORAGE_BATCH_SIZE:
                    await self._save_batch(batch, worker_id, saved_count)
                    saved_count += len(batch)
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
            "storage_worker_finished", worker_id=worker_id, total_saved=saved_count
        )

    async def _save_batch(
        self, batch: List[ScrapedItem], worker_id: int, saved_count: int
    ):
        try:
            await self.storage_service.save_items(batch)
            logger.info(
                "storage_batch_saved",
                worker_id=worker_id,
                batch_size=len(batch),
                total_saved=saved_count + len(batch),
            )
        except Exception as e:
            logger.error(
                "storage_batch_error",
                worker_id=worker_id,
                batch_size=len(batch),
                error=str(e),
            )
