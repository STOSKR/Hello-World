"""Scraping service with Clean Architecture."""

import asyncio
from pathlib import Path
from typing import List, Optional, Dict

from app.core.logger import get_logger
from app.core.config import Settings
from app.domain.models import ScrapedItem
from app.services.extractors import ItemExtractor, DetailedItemExtractor
from app.services.filters import FilterManager
from app.services.utils import BrowserManager, FileSaver
from app.services.utils.session_manager import SessionManager
from app.services.workers import Producer, ScraperWorker, StorageWorker
from app.services.storage import StorageService

logger = get_logger(__name__)


class ScrapingService:
    """Main scraping service with producer-consumer pattern."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.item_extractor = ItemExtractor()
        self.detailed_extractor = DetailedItemExtractor(settings)
        self.filter_manager = FilterManager(settings)
        self.file_saver = FileSaver(settings)
        self.session_manager = SessionManager()

    async def scrape_items(
        self,
        limit: Optional[int] = None,
        concurrent_workers: Optional[int] = None,
        storage_workers: Optional[int] = None,
        exclusion_filters: Optional[List[str]] = None,
        async_storage: bool = False,
        headless: Optional[bool] = None,
    ) -> tuple[List[ScrapedItem], List[Dict]]:
        scraper_workers = concurrent_workers or self.settings.max_concurrent
        db_workers = storage_workers or 2
        filters = exclusion_filters or []
        headless_mode = headless if headless is not None else self.settings.headless

        logger.info(
            "scrape_started",
            limit=limit,
            scraper_workers=scraper_workers,
            storage_workers=db_workers if async_storage else 0,
        )

        results: List[ScrapedItem] = []
        discarded_items: List[Dict] = []

        storage_queue: Optional[asyncio.Queue[Optional[ScrapedItem]]] = None
        storage_service = None
        if async_storage:
            storage_queue = asyncio.Queue()
            storage_service = StorageService()

        use_persistent, storage_state = self.session_manager.get_browser_config()

        async with BrowserManager(
            headless=headless_mode,
            use_persistent_context=use_persistent,
            storage_state_path=storage_state,
        ) as browser:
            page = browser.get_page()
            await browser.navigate(self.settings.target_url)
            await self.filter_manager.configure_all_filters(page)
            await self.file_saver.save_debug_files(page)

            worker_pages = await self._create_worker_pages(page, scraper_workers)
            item_queue: asyncio.Queue[Optional[Dict]] = asyncio.Queue()

            producer = Producer(self.item_extractor, filters)
            total_to_process = await producer.run(
                page, self.settings.target_url, item_queue, limit, scraper_workers
            )

            scraper_tasks = [
                self._run_scraper_worker(
                    i,
                    item_queue,
                    storage_queue,
                    worker_pages[i],
                    results,
                    discarded_items,
                    total_to_process,
                )
                for i in range(scraper_workers)
            ]

            storage_tasks = []
            if async_storage and storage_service:
                storage_tasks = [
                    StorageWorker(storage_service).run(i, storage_queue)
                    for i in range(db_workers)
                ]

            await asyncio.gather(*scraper_tasks)

            if async_storage and storage_queue:
                for _ in range(db_workers):
                    await storage_queue.put(None)
                await asyncio.gather(*storage_tasks)

            await self._cleanup_worker_pages(worker_pages)

        logger.info(
            "scrape_completed",
            total_items=len(results),
            discarded_items=len(discarded_items),
        )
        return results, discarded_items

    async def _create_worker_pages(self, page, count: int):
        worker_pages = []
        for _ in range(count):
            buff_page = await page.context.new_page()
            steam_page = await page.context.new_page()
            worker_pages.append((buff_page, steam_page))
        logger.info("worker_pages_ready", count=len(worker_pages))
        return worker_pages

    async def _run_scraper_worker(
        self,
        worker_id,
        item_queue,
        storage_queue,
        pages,
        results,
        discarded_items,
        total_to_process,
    ):
        buff_page, steam_page = pages
        worker = ScraperWorker(
            self.settings, self.detailed_extractor, None, buff_page, steam_page
        )
        await worker.run(
            worker_id,
            item_queue,
            storage_queue,
            results,
            discarded_items,
            total_to_process,
        )

    async def _cleanup_worker_pages(self, worker_pages):
        logger.info("closing_worker_pages")
        for buff_page, steam_page in worker_pages:
            await buff_page.close()
            await steam_page.close()
        logger.info("worker_pages_closed")
