"""Domain models with Pydantic validation"""

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


# NOTE: Removed Skin, PriceData, MarketData models
# Using simple dicts for intermediate data during scraping
# Only validate final result with ScrapedItem


class ScrapedItem(BaseModel):
    """Complete scraped item with all calculations"""

    item_name: str = Field(..., min_length=1)
    quality: Optional[str] = Field(
        None, description="Item quality/wear (e.g., Factory New)"
    )
    stattrak: bool = Field(default=False, description="Has StatTrak counter")
    url: Optional[HttpUrl] = Field(None, description="Item page URL")

    # URLs
    steam_url: Optional[HttpUrl] = None
    buff_url: Optional[HttpUrl] = None

    # Prices
    buff_avg_price_eur: float = Field(..., gt=0)
    steam_avg_price_eur: float = Field(..., gt=0)

    # Volumes
    buff_volume: int = Field(default=0, ge=0)
    steam_volume: int = Field(default=0, ge=0)

    # Calculations
    profit_eur: float = Field(..., description="Net profit in EUR")
    profitability_percent: float = Field(..., description="ROI percentage")
    profitability_ratio: float = Field(..., description="Profit ratio (for sorting)")

    # Metadata
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = Field(default="steamdt_hanging")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: lambda v: str(v),
        }


class FilterConfig(BaseModel):
    """Filtering configuration"""

    min_price: float = Field(default=20.0, ge=0)
    max_price: Optional[float] = Field(default=None, ge=0)
    min_volume: int = Field(default=40, ge=0)
    min_roi: Optional[float] = Field(default=None, description="Minimum ROI %")

    platforms: dict[str, bool] = Field(
        default={"C5GAME": False, "UU": False, "BUFF": True}
    )


class AntibanConfig(BaseModel):
    """Anti-ban scraping configuration"""

    mode: Literal["safe", "balanced", "fast", "stealth"] = Field(default="safe")
    max_concurrent: int = Field(default=1, ge=1, le=5)
    delay_between_items: int = Field(default=5000, ge=0, description="Fixed delay (ms)")
    random_delay_min: int = Field(default=2000, ge=0)
    random_delay_max: int = Field(default=5000, ge=0)
    delay_between_batches: int = Field(default=8000, ge=0)

    def get_random_delay_range(self) -> tuple[int, int]:
        """Get random delay range in milliseconds"""
        return (self.random_delay_min, self.random_delay_max)
