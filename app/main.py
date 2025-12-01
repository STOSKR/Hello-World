"""Main entry point for CS-Tracker with clean architecture"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from app.core.config import settings
from app.core.logger import configure_logging, get_logger
from app.domain.models import ScrapedItem
from app.services.scraping import ScrapingService
from app.services.storage import StorageService

# Configure logging on startup
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
configure_logging(log_file=log_file)

logger = get_logger(__name__)


async def scrape_only(
    headless: bool = True,
    max_concurrent: int = 1,
    save_to_db: bool = False,
    output_file: Optional[str] = None,
    limit: Optional[int] = None,
    exclude_prefixes: Optional[list[str]] = None,
) -> list[ScrapedItem]:
    """Run scraper without agents or graph
    
    Args:
        headless: Run browser in headless mode
        max_concurrent: Number of items to process concurrently
        save_to_db: Whether to save results to Supabase
        output_file: Optional JSON file to save results
        limit: Maximum items to scrape (None = unlimited)
        exclude_prefixes: Item name prefixes to exclude
        
    Returns:
        List of scraped items
    """
    logger.info(
        "scrape_started",
        headless=headless,
        max_concurrent=max_concurrent,
        save_to_db=save_to_db,
        limit=limit,
        exclude_prefixes=exclude_prefixes,
    )

    url = "https://steamdt.com/en/hanging"
    items: list[ScrapedItem] = []

    # Initialize scraping service with DI
    async with ScrapingService(
        headless=headless,
        max_concurrent=max_concurrent,
        limit=limit,
        exclude_prefixes=exclude_prefixes or ["Charm |"],
        delay_config={
            "delay_between_items": settings.delay_between_items,
            "random_delay_min": settings.random_delay_min,
            "random_delay_max": settings.random_delay_max,
            "delay_between_batches": settings.delay_between_batches,
        },
    ) as scraper:
        items = await scraper.scrape_all(url)

    logger.info("scrape_completed", items_count=len(items))

    # Save to database if requested
    if save_to_db and items:
        try:
            storage = StorageService()
            await storage.save_items(items)
            logger.info("items_saved_to_db", count=len(items))
        except Exception as e:
            logger.error("db_save_failed", error=str(e))

    # Save to JSON file if requested
    if output_file and items:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        import json
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                [item.model_dump(mode="json") for item in items],
                f,
                indent=2,
                ensure_ascii=False,
            )
        logger.info("items_saved_to_file", path=str(output_path), count=len(items))

    return items


@click.group()
def cli():
    """CS-Tracker - Clean Architecture Version"""
    pass


@cli.command()
@click.option("--headless/--visible", default=True, help="Browser mode")
@click.option("--concurrent", default=1, type=int, help="Max concurrent items (1-5)")
@click.option("--save-db/--no-db", default=False, help="Save to Supabase")
@click.option("--output", default=None, help="Output JSON file path")
@click.option("--limit", default=None, type=int, help="Max items to scrape (default: unlimited)")
@click.option(
    "--exclude",
    multiple=True,
    default=["Charm |"],
    help="Item prefixes to exclude (can use multiple times)",
)
def scrape(
    headless: bool,
    concurrent: int,
    save_db: bool,
    output: Optional[str],
    limit: Optional[int],
    exclude: tuple[str],
):
    """Run scraper only (no agents, no graph)
    
    Examples:
        python -m app.main scrape --limit 10
        python -m app.main scrape --visible --concurrent 2 --limit 5
        python -m app.main scrape --exclude "Charm |" --exclude "Graffiti |"
        python -m app.main scrape --save-db --output data/results.json
    """
    if concurrent < 1 or concurrent > 5:
        click.echo("Error: concurrent must be between 1 and 5", err=True)
        sys.exit(1)

    exclude_list = list(exclude) if exclude else ["Charm |"]
    
    click.echo(f"Starting scraper (headless={headless}, concurrent={concurrent})")
    if limit:
        click.echo(f"Limit: {limit} items")
    click.echo(f"Excluding prefixes: {exclude_list}")
    
    items = asyncio.run(
        scrape_only(
            headless=headless,
            max_concurrent=concurrent,
            save_to_db=save_db,
            output_file=output,
            limit=limit,
            exclude_prefixes=exclude_list,
        )
    )

    click.echo(f"\nCompleted! Scraped {len(items)} items")
    
    if items:
        click.echo("\nTop 3 items by ROI:")
        sorted_items = sorted(items, key=lambda x: x.profitability_percent, reverse=True)
        for idx, item in enumerate(sorted_items[:3], 1):
            click.echo(
                f"  {idx}. {item.item_name}: "
                f"€{item.profit_eur:.2f} profit ({item.profitability_percent:.2f}% ROI)"
            )


@cli.command()
def test_config():
    """Test configuration loading"""
    click.echo("Configuration Test")
    click.echo(f"  Supabase URL: {settings.supabase_url[:30]}...")
    click.echo(f"  Headless: {settings.scraper_headless}")
    click.echo(f"  Max Concurrent: {settings.max_concurrent}")
    click.echo(f"  Currency: {settings.currency_code}")
    click.echo(f"  Min Price: €{settings.min_price}")
    click.echo(f"  Log Level: {settings.log_level}")
    click.echo(f"  Anti-ban delays: {settings.random_delay_min}-{settings.random_delay_max}ms")


@cli.command()
@click.option("--item", required=True, help="Item name to query")
@click.option("--limit", default=10, help="Max records")
def history(item: str, limit: int):
    """Get price history from database"""
    
    async def get_history():
        storage = StorageService()
        records = await storage.get_item_history(item, limit)
        return records
    
    records = asyncio.run(get_history())
    
    if not records:
        click.echo(f"No history found for '{item}'")
        return
    
    click.echo(f"\nPrice history for '{item}' ({len(records)} records):\n")
    for rec in records:
        click.echo(
            f"  {rec['scraped_at']}: "
            f"Buy €{rec['buy_price']:.2f} | Sell €{rec['sell_price']:.2f} | "
            f"Profit €{rec['profit']:.2f}"
        )


@cli.command()
def health():
    """Check database connection"""
    
    async def check():
        storage = StorageService()
        is_healthy = await storage.health_check()
        return is_healthy
    
    is_healthy = asyncio.run(check())
    
    if is_healthy:
        click.echo("✓ Database connection healthy")
    else:
        click.echo("✗ Database connection failed", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
