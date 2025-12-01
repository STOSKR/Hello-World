"""Centralized configuration using pydantic-settings"""

import json
from pathlib import Path
from typing import Dict, Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Supabase
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_key: str = Field(..., description="Supabase anon/service key")

    # Scraper general
    scraper_headless: bool = Field(
        default=True, description="Run browser in headless mode"
    )
    scraper_timeout: int = Field(default=60000, description="Page load timeout (ms)")
    scraper_wait_time: int = Field(
        default=5000, description="Wait time for dynamic content (ms)"
    )

    # Anti-ban configuration
    max_concurrent: int = Field(
        default=1, ge=1, le=5, description="Max concurrent items to process"
    )
    delay_between_items: int = Field(
        default=5000, ge=0, description="Fixed delay between items (ms)"
    )
    random_delay_min: int = Field(
        default=2000, ge=0, description="Min random delay (ms)"
    )
    random_delay_max: int = Field(
        default=5000, ge=0, description="Max random delay (ms)"
    )
    delay_between_batches: int = Field(
        default=8000, ge=0, description="Delay between batches (ms)"
    )

    # Trading configuration
    currency_code: str = Field(default="EUR", description="Currency code")
    sell_mode: str = Field(
        default="Sell at STEAM Lowest Price", description="Steam sell mode"
    )
    balance_type: Literal["STEAM Balance", "Platform Balance"] = Field(
        default="STEAM Balance"
    )

    # Filters
    min_price: float = Field(default=20.0, ge=0, description="Minimum price filter")
    max_price: Optional[float] = Field(default=None, description="Maximum price filter")
    min_volume: int = Field(default=40, ge=0, description="Minimum volume filter")

    # Platforms
    platform_c5game: bool = Field(default=False, description="Include C5GAME")
    platform_uu: bool = Field(default=False, description="Include UU")
    platform_buff: bool = Field(default=True, description="Include BUFF163")

    # Output
    save_screenshot: bool = Field(default=True)
    save_html: bool = Field(default=True)
    output_directory: Path = Field(default=Path("data"))

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    log_format: Literal["json", "text"] = Field(
        default="json", description="Log output format"
    )

    # Optional: Future LangGraph/AI settings
    gemini_api_key: Optional[str] = Field(default=None, description="Gemini API key")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")

    @field_validator("random_delay_max")
    @classmethod
    def validate_random_delays(cls, v: int, info) -> int:
        """Ensure max >= min for random delays"""
        if "random_delay_min" in info.data and v < info.data["random_delay_min"]:
            raise ValueError("random_delay_max must be >= random_delay_min")
        return v

    @classmethod
    def load_from_json(cls, json_path: Path) -> "Settings":
        """Load settings from JSON config file"""
        with open(json_path, encoding="utf-8") as f:
            config_data = json.load(f)

        # Flatten nested JSON structure
        flat_config = {}

        if "scraper" in config_data:
            scraper = config_data["scraper"]
            flat_config["scraper_headless"] = scraper.get("headless", True)
            flat_config["scraper_timeout"] = scraper.get("timeout", 60000)
            flat_config["scraper_wait_time"] = scraper.get("wait_time", 5000)
            flat_config["max_concurrent"] = scraper.get("max_concurrent", 1)
            flat_config["delay_between_items"] = scraper.get("delay_between_items", 5000)
            flat_config["random_delay_min"] = scraper.get("random_delay_min", 2000)
            flat_config["random_delay_max"] = scraper.get("random_delay_max", 5000)
            flat_config["delay_between_batches"] = scraper.get(
                "delay_between_batches", 8000
            )

        if "currency" in config_data:
            flat_config["currency_code"] = config_data["currency"].get("code", "EUR")

        if "price_mode" in config_data:
            flat_config["sell_mode"] = config_data["price_mode"].get(
                "sell_mode", "Sell at STEAM Lowest Price"
            )

        if "balance_type" in config_data:
            flat_config["balance_type"] = config_data["balance_type"].get(
                "type", "STEAM Balance"
            )

        if "filters" in config_data:
            filters = config_data["filters"]
            flat_config["min_price"] = filters.get("min_price", 20.0)
            flat_config["max_price"] = filters.get("max_price")
            flat_config["min_volume"] = filters.get("min_volume", 40)

        if "platforms" in config_data:
            platforms = config_data["platforms"]
            flat_config["platform_c5game"] = platforms.get("C5GAME", False)
            flat_config["platform_uu"] = platforms.get("UU", False)
            flat_config["platform_buff"] = platforms.get("BUFF", True)

        if "output" in config_data:
            output = config_data["output"]
            flat_config["save_screenshot"] = output.get("save_screenshot", True)
            flat_config["save_html"] = output.get("save_html", True)
            flat_config["output_directory"] = Path(
                output.get("output_directory", "data")
            )

        if "debug" in config_data:
            flat_config["log_level"] = config_data["debug"].get("log_level", "INFO")

        return cls(**flat_config)

    def get_platforms_dict(self) -> Dict[str, bool]:
        """Get platforms configuration as dict"""
        return {
            "C5GAME": self.platform_c5game,
            "UU": self.platform_uu,
            "BUFF": self.platform_buff,
        }


# Global settings instance
try:
    config_path = Path(__file__).parent.parent.parent / "config" / "scraper_config.json"
    if config_path.exists():
        settings = Settings.load_from_json(config_path)
    else:
        settings = Settings()
except Exception:
    # Fallback to environment variables only
    settings = Settings()
