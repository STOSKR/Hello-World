"""Domain models with Pydantic validation"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class Skin(BaseModel):
    """CS2 Skin representation"""

    name: str = Field(..., description="Full skin name", min_length=1)
    wear: Optional[str] = Field(None, description="Wear (FN, MW, FT, WW, BS)")
    float_value: Optional[float] = Field(None, ge=0.0, le=1.0, description="Float value")
    stattrak: bool = Field(default=False, description="StatTrak skin")

    class Config:
        frozen = True  # Immutable


class PriceData(BaseModel):
    """Price information from a marketplace"""

    lowest_price: float = Field(..., gt=0, description="Lowest listing price")
    avg_price: Optional[float] = Field(None, gt=0, description="Average price")
    highest_buy_order: Optional[float] = Field(None, gt=0, description="Highest buy order")
    volume_24h: int = Field(default=0, ge=0, description="24h trading volume")
    listings_count: int = Field(default=0, ge=0, description="Active listings")


class MarketData(BaseModel):
    """Complete market data for a skin"""

    skin_name: str = Field(..., min_length=1)
    steam: PriceData = Field(..., description="Steam market data")
    buff: PriceData = Field(..., description="Buff163 market data")
    currency: str = Field(default="EUR", description="Price currency")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def calculate_spread(self) -> float:
        """Calculate price spread between markets"""
        return self.steam.lowest_price - self.buff.lowest_price


class ScrapedItem(BaseModel):
    """Complete scraped item with all calculations"""

    item_name: str = Field(..., min_length=1)
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
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
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
