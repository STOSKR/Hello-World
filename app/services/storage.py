"""Supabase storage service with proper async support"""

import asyncio
from datetime import datetime
from typing import List, Optional

from supabase import Client, create_client

from app.core.config import settings
from app.core.logger import get_logger
from app.domain.models import ScrapedItem

logger = get_logger(__name__)


class StorageService:
    """Async Supabase storage service using run_in_executor"""

    def __init__(
        self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None
    ):
        """Initialize Supabase client

        Args:
            supabase_url: Override default URL from settings
            supabase_key: Override default key from settings
        """
        self.url = supabase_url or settings.supabase_url
        self.key = supabase_key or settings.supabase_key

        if not self.url or not self.key:
            raise ValueError(
                "Supabase credentials required. Set SUPABASE_URL and SUPABASE_KEY in .env"
            )

        self.client: Client = create_client(self.url, self.key)
        logger.info("storage_initialized", url=self.url[:30] + "...")

    async def save_items(
        self, items: List[ScrapedItem], source: str = "steamdt_hanging"
    ) -> bool:
        """Save scraped items to database

        Args:
            items: List of scraped items
            source: Data source identifier

        Returns:
            True if successful
        """
        if not items:
            logger.warning("save_items_skipped", reason="empty_list")
            return False

        try:
            records = []
            for item in items:
                record = {
                    "item_name": item.item_name,
                    "quality": item.quality,
                    "stattrak": item.stattrak,
                    "profitability": round(item.profitability_percent, 2),
                    "profit_eur": round(item.profit_eur, 2),
                    "buff_url": str(item.buff_url) if item.buff_url else None,
                    "buff_price_eur": round(item.buff_avg_price_eur, 2),
                    "steam_url": str(item.steam_url) if item.steam_url else None,
                    "steam_price_eur": round(item.steam_avg_price_eur, 2),
                    "scraped_at": item.scraped_at.strftime("%Y/%m/%d-%H:%M"),
                    "source": source,
                }
                records.append(record)

            # Run sync operation in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.table("scraped_items").insert(records).execute(),
            )

            logger.info("items_saved", count=len(records), source=source)
            return True

        except Exception as e:
            logger.error("save_items_failed", error=str(e), item_count=len(items))
            raise

    async def get_latest_items(self, limit: int = 100) -> List[dict]:
        """Get latest scraped items

        Args:
            limit: Maximum items to retrieve

        Returns:
            List of item records
        """
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.table("scraped_items")
                .select("*")
                .order("scraped_at", desc=True)
                .limit(limit)
                .execute(),
            )

            logger.info("items_retrieved", count=len(response.data))
            return response.data

        except Exception as e:
            logger.error("get_items_failed", error=str(e))
            raise

    async def get_item_history(self, item_name: str, limit: int = 50) -> List[dict]:
        """Get price history for specific item

        Args:
            item_name: Name of the item
            limit: Maximum records

        Returns:
            Historical records
        """
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.table("scraped_items")
                .select("*")
                .eq("item_name", item_name)
                .order("scraped_at", desc=True)
                .limit(limit)
                .execute(),
            )

            logger.info(
                "item_history_retrieved", item=item_name, count=len(response.data)
            )
            return response.data

        except Exception as e:
            logger.error("get_history_failed", item=item_name, error=str(e))
            raise

    async def health_check(self) -> bool:
        """Check database connection

        Returns:
            True if connection is healthy
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.table("scraped_items")
                .select("id")
                .limit(1)
                .execute(),
            )
            logger.info("health_check_passed")
            return True
        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            return False
