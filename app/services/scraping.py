"""Scraping service with clean architecture and parallel price fetching"""

import asyncio
import random
from datetime import datetime
from typing import List, Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.core.config import settings
from app.core.logger import get_logger
from app.domain.models import ScrapedItem
from app.domain.rules import calculate_profit, calculate_roi

logger = get_logger(__name__)


class ScrapingService:
    """Service for scraping market data with dependency injection"""

    def __init__(
        self,
        headless: bool = True,
        max_concurrent: int = 1,
        delay_config: Optional[dict] = None,
        exclude_prefixes: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ):
        """Initialize scraping service
        
        Args:
            headless: Run browser in headless mode
            max_concurrent: Maximum items to process concurrently
            delay_config: Anti-ban delay configuration
            exclude_prefixes: Item name prefixes to exclude (e.g., ['Charm |'])
            limit: Maximum items to scrape (None = unlimited)
        """
        self.headless = headless
        self.max_concurrent = max_concurrent
        self.exclude_prefixes = exclude_prefixes or ["Charm |"]
        self.limit = limit
        self.delay_config = delay_config or {
            "delay_between_items": settings.delay_between_items,
            "random_delay_min": settings.random_delay_min,
            "random_delay_max": settings.random_delay_max,
            "delay_between_batches": settings.delay_between_batches,
        }

        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self._init_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_browser()

    async def _init_browser(self) -> None:
        """Initialize Playwright browser"""
        logger.info("browser_initializing", headless=self.headless)
        
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        
        logger.info("browser_initialized")

    async def _close_browser(self) -> None:
        """Close browser and context"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        logger.info("browser_closed")

    async def _random_delay(self) -> None:
        """Apply random delay for anti-ban"""
        min_ms = self.delay_config["random_delay_min"]
        max_ms = self.delay_config["random_delay_max"]
        delay_ms = random.randint(min_ms, max_ms)
        
        await asyncio.sleep(delay_ms / 1000)
        logger.debug("random_delay_applied", delay_ms=delay_ms)

    def _should_exclude_item(self, item_name: str) -> bool:
        """Check if item should be excluded based on prefixes
        
        Args:
            item_name: Name of the item
            
        Returns:
            True if item should be excluded
        """
        for prefix in self.exclude_prefixes:
            if item_name.startswith(prefix):
                logger.debug("item_excluded", item=item_name, prefix=prefix)
                return True
        return False

    async def scrape_item_list(self, url: str) -> List[dict]:
        """Scrape basic item list from main page
        
        Args:
            url: Target URL (e.g., https://steamdt.com/en/hanging)
            
        Returns:
            List of basic item data with URLs
        """
        if not self.context:
            raise RuntimeError("Browser not initialized. Use async context manager.")

        page = await self.context.new_page()
        
        try:
            logger.info("navigating_to_list", url=url)
            await page.goto(url, timeout=settings.scraper_timeout)
            await page.wait_for_timeout(settings.scraper_wait_time)
            
            # Close potential modals
            try:
                await page.locator('button:has-text("Close")').click(timeout=2000)
            except Exception:
                pass

            # Extract items (simplified - adapt from src/scrapers/extractors/item_extractor.py)
            items_selector = "tr.item-row"  # Adjust to actual selector
            items = await page.locator(items_selector).all()
            
            basic_items = []
            for idx, item_elem in enumerate(items[:20]):  # Limit for testing
                try:
                    # Extract basic data (adapt selectors from original code)
                    name = await item_elem.locator(".item-name").inner_text()
                    item_url = await item_elem.locator("a").get_attribute("href")
                    
                    basic_items.append({
                        "item_name": name.strip(),
                        "url": item_url,
                        "index": idx,
                    })
                except Exception as e:
                    logger.warning("item_extraction_failed", index=idx, error=str(e))
                    continue
            
            logger.info("items_extracted", count=len(basic_items))
            return basic_items
            
        finally:
            await page.close()

    async def scrape_item_details(
        self, item_name: str, buff_url: str, steam_url: str
    ) -> Optional[ScrapedItem]:
        """Scrape detailed prices from Buff and Steam in PARALLEL
        
        Args:
            item_name: Name of the item
            buff_url: Buff163 URL
            steam_url: Steam market URL
            
        Returns:
            ScrapedItem with complete data or None if failed
        """
        if not self.context:
            raise RuntimeError("Browser not initialized")

        logger.info("scraping_details", item=item_name)

        # Create two pages for parallel scraping
        buff_page = await self.context.new_page()
        steam_page = await self.context.new_page()

        try:
            # Scrape Buff and Steam in PARALLEL
            buff_task = self._scrape_buff_price(buff_page, buff_url)
            steam_task = self._scrape_steam_price(steam_page, steam_url)
            
            buff_data, steam_data = await asyncio.gather(buff_task, steam_task)

            if not buff_data or not steam_data:
                logger.warning("price_data_incomplete", item=item_name)
                return None

            # Calculate profit and ROI using domain rules
            profit = calculate_profit(buff_data["price"], steam_data["price"])
            roi = calculate_roi(buff_data["price"], steam_data["price"])

            scraped_item = ScrapedItem(
                item_name=item_name,
                buff_url=buff_url,
                steam_url=steam_url,
                buff_avg_price_eur=buff_data["price"],
                steam_avg_price_eur=steam_data["price"],
                buff_volume=buff_data.get("volume", 0),
                steam_volume=steam_data.get("volume", 0),
                profit_eur=profit,
                profitability_percent=roi,
                profitability_ratio=roi / 100,
                scraped_at=datetime.utcnow(),
            )

            logger.info(
                "item_scraped",
                item=item_name,
                profit=profit,
                roi=roi,
            )

            return scraped_item

        except Exception as e:
            logger.error("scrape_details_failed", item=item_name, error=str(e))
            return None

        finally:
            await buff_page.close()
            await steam_page.close()

    async def _scrape_buff_price(self, page: Page, url: str) -> Optional[dict]:
        """Scrape price from Buff163
        
        Args:
            page: Playwright page
            url: Buff URL
            
        Returns:
            Dict with price and volume
        """
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(2000)

            # Adapt selectors from src/scrapers/extractors/detailed_item_extractor.py
            price_selector = ".price-value"  # Adjust to actual selector
            price_text = await page.locator(price_selector).first.inner_text()
            price = float(price_text.replace("€", "").replace(",", ".").strip())

            # Extract volume if available
            volume = 0
            try:
                volume_text = await page.locator(".volume").inner_text()
                volume = int(volume_text)
            except Exception:
                pass

            logger.debug("buff_price_scraped", price=price, volume=volume)
            return {"price": price, "volume": volume}

        except Exception as e:
            logger.error("buff_scrape_failed", url=url, error=str(e))
            return None

    async def _scrape_steam_price(self, page: Page, url: str) -> Optional[dict]:
        """Scrape price from Steam
        
        Args:
            page: Playwright page
            url: Steam URL
            
        Returns:
            Dict with price and volume
        """
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(2000)

            # Adapt selectors from original code
            price_selector = ".market_listing_price"  # Adjust to actual selector
            price_text = await page.locator(price_selector).first.inner_text()
            price = float(price_text.replace("€", "").replace(",", ".").strip())

            volume = 0
            try:
                volume_text = await page.locator(".market_commodity_orders_header_promote").inner_text()
                volume = int(volume_text)
            except Exception:
                pass

            logger.debug("steam_price_scraped", price=price, volume=volume)
            return {"price": price, "volume": volume}

        except Exception as e:
            logger.error("steam_scrape_failed", url=url, error=str(e))
            return None

    async def scrape_all(self, url: str) -> List[ScrapedItem]:
        """Scrape with producer-consumer pattern
        
        Producer: Extracts and filters items from table
        Consumer: Scrapes detailed prices in parallel
        
        Args:
            url: Starting URL
            
        Returns:
            List of scraped items
        """
        logger.info(
            "scraping_started",
            url=url,
            max_concurrent=self.max_concurrent,
            limit=self.limit,
            exclude_prefixes=self.exclude_prefixes,
        )

        # Shared queue for producer-consumer pattern
        item_queue: asyncio.Queue = asyncio.Queue()
        scraped_items: List[ScrapedItem] = []
        scraping_complete = asyncio.Event()

        # Producer: Extract items from table and add to queue
        async def producer():
            """Extract items from table and filter"""
            try:
                basic_items = await self.scrape_item_list(url)
                
                items_added = 0
                items_excluded = 0
                
                for item in basic_items:
                    # Apply limit
                    if self.limit and items_added >= self.limit:
                        logger.info("limit_reached", limit=self.limit)
                        break
                    
                    # Apply exclusion filter
                    if self._should_exclude_item(item["item_name"]):
                        items_excluded += 1
                        continue
                    
                    await item_queue.put(item)
                    items_added += 1
                
                logger.info(
                    "producer_finished",
                    items_added=items_added,
                    items_excluded=items_excluded,
                )
                
            finally:
                # Signal consumers to stop
                scraping_complete.set()

        # Consumer: Process items from queue
        async def consumer(consumer_id: int):
            """Scrape detailed data from queue"""
            processed = 0
            
            while True:
                try:
                    # Wait for item or completion
                    item = await asyncio.wait_for(item_queue.get(), timeout=1.0)
                    
                    # Apply random delay (anti-ban)
                    await self._random_delay()
                    
                    # Scrape details
                    result = await self.scrape_item_details(
                        item["item_name"],
                        item.get("buff_url", ""),
                        item.get("steam_url", ""),
                    )
                    
                    if result:
                        scraped_items.append(result)
                    
                    processed += 1
                    item_queue.task_done()
                    
                except asyncio.TimeoutError:
                    # Check if producer finished
                    if scraping_complete.is_set() and item_queue.empty():
                        break
                except Exception as e:
                    logger.error("consumer_error", consumer_id=consumer_id, error=str(e))
            
            logger.debug("consumer_finished", consumer_id=consumer_id, processed=processed)

        # Start producer and consumers concurrently
        producer_task = asyncio.create_task(producer())
        consumer_tasks = [
            asyncio.create_task(consumer(i)) for i in range(self.max_concurrent)
        ]

        # Wait for all tasks
        await producer_task
        await asyncio.gather(*consumer_tasks)

        logger.info(
            "scraping_completed",
            total_scraped=len(scraped_items),
        )

        return scraped_items
