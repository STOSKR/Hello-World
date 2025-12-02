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
from app.services.scraping import ScrapingService, _format_item_display
from app.services.storage import StorageService

# Configure logging on startup
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
configure_logging(log_dir=str(log_dir))

logger = get_logger(__name__)


async def scrape_only(
    headless: bool = True,
    max_concurrent: int = 1,
    save_to_db: bool = False,
    output_file: Optional[str] = None,
    limit: Optional[int] = None,
    exclude_prefixes: Optional[list[str]] = None,
    quiet: bool = False,
    async_storage: bool = False,
) -> list[ScrapedItem]:
    logger.info(
        "scrape_started",
        headless=headless,
        max_concurrent=max_concurrent,
        save_to_db=save_to_db,
        limit=limit,
        exclude_prefixes=exclude_prefixes,
    )

    # Override settings with runtime parameters
    settings.headless = headless
    settings.max_concurrent = max_concurrent

    # Initialize scraping service with settings
    scraping_service = ScrapingService(settings)

    # Run scraper (unified method with async_storage parameter)
    items, discarded_items = await scraping_service.scrape_items(
        limit=limit,
        concurrent_workers=max_concurrent,
        exclusion_filters=exclude_prefixes or [],
        async_storage=async_storage and save_to_db,
    )

    # Save to database if requested and NOT using async storage
    if save_to_db and not async_storage and items:
        try:
            storage = StorageService()
            await storage.save_items(items)
            logger.info("items_saved_to_db", count=len(items))
        except Exception as e:
            logger.error("db_save_failed", error=str(e))

    logger.info(
        "scrape_completed",
        items_count=len(items),
        discarded_count=len(discarded_items),
    )

    # Save to JSON file if requested
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        import json

        json_data = []

        # Add valid items (sorted by profitability)
        if items:
            sorted_items = sorted(
                items, key=lambda x: x.profitability_percent, reverse=True
            )

            json_data.extend(
                [
                    {
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
                        "source": "steamdt_hanging",
                    }
                    for item in sorted_items
                ]
            )

        # Add discarded items at the end
        if discarded_items:
            json_data.extend(
                [
                    {
                        "item_name": disc["item_name"],
                        "quality": disc.get("quality"),
                        "stattrak": disc.get("stattrak", False),
                        "discarded": True,
                        "discard_reason": disc.get("discard_reason"),
                    }
                    for disc in discarded_items
                ]
            )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        logger.info(
            "items_saved_to_file",
            path=str(output_path),
            valid=len(items),
            discarded=len(discarded_items),
        )

    return items, discarded_items


@click.group()
def cli():
    """CS-Tracker - Clean Architecture Version"""
    pass


@cli.command()
@click.option(
    "--headless/--visible", default=False, help="Browser mode (default: visible)"
)
@click.option(
    "--concurrent", default=2, type=int, help="Max concurrent items (1-5, default: 2)"
)
@click.option(
    "--save-db/--no-db", default=True, help="Save to Supabase (default: enabled)"
)
@click.option(
    "--output",
    default=None,
    help="Output JSON file path (default: auto-generated with timestamp)",
)
@click.option("--limit", default=200, type=int, help="Max items to scrape (default: 50)")
@click.option(
    "--exclude",
    multiple=True,
    default=[],
    help="Item prefixes to exclude (can use multiple times). Charms and Patches already excluded by default.",
)
@click.option("--quiet", "-q", is_flag=True, help="Reduce console output (for CI/CD)")
@click.option(
    "--no-async-storage",
    is_flag=True,
    default=False,
    help="Disable async storage (saves all items at the end instead of incrementally)",
)
def scrape(
    headless: bool,
    concurrent: int,
    save_db: bool,
    output: Optional[str],
    limit: Optional[int],
    exclude: tuple[str],
    quiet: bool,
    no_async_storage: bool,
):
    """Run scraper only (no agents, no graph)

    Examples:
        python -m app.main scrape --limit 10
        python -m app.main scrape --visible --concurrent 2 --limit 5
        python -m app.main scrape --exclude "Charm |" --exclude "Patch |" --exclude "Graffiti |"
        python -m app.main scrape --save-db --output data/results.json
    """
    if concurrent < 1 or concurrent > 5:
        click.echo("Error: concurrent must be between 1 and 5", err=True)
        sys.exit(1)

    exclude_list = list(exclude) if exclude else []

    # Auto-generate JSON output file with timestamp if not specified
    if output is None:
        output_dir = Path("data")
        output_dir.mkdir(exist_ok=True)
        output = str(
            output_dir
            / f"scraper_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

    if not quiet:
        click.echo(f"\n🚀 CS-Tracker Scraper")
        click.echo(f"{'='*60}")
        click.echo(
            f"Mode: {'Headless' if headless else 'Visible'} | Workers: {concurrent} | Limit: {limit or 'No limit'}"
        )
        if exclude_list:
            click.echo(f"Exclusions: {', '.join(exclude_list)}")
        click.echo(f"Output: {output}")
        click.echo(f"{'='*60}\n")

    items, discarded = asyncio.run(
        scrape_only(
            headless=headless,
            max_concurrent=concurrent,
            save_to_db=save_db,
            output_file=output,
            limit=limit,
            exclude_prefixes=exclude_list,
            quiet=quiet,
            async_storage=not no_async_storage,  # Inverted: async by default
        )
    )

    if not quiet:
        click.echo(f"\n{'='*60}")

    # Log completion summary
    logger.info(
        "scrape_summary", valid_items=len(items), discarded_items=len(discarded)
    )

    click.echo(f"✅ Completed! {len(items)} valid items, {len(discarded)} discarded")
    if not quiet:
        click.echo(f"{'='*60}")

    if items and not quiet:
        click.echo(f"\n{'='*60}")
        click.echo(f"📊 Top Items by ROI (Best to Worst)")
        click.echo(f"{'='*60}")
        sorted_items = sorted(
            items, key=lambda x: x.profitability_percent, reverse=True
        )

        # Log top items to file
        logger.info("top_items_by_roi", count=len(sorted_items))

        for idx, item in enumerate(sorted_items, 1):
            display_name = _format_item_display(item.item_name, item.quality, item.stattrak)

            # Log each top item
            logger.info(
                "top_item",
                rank=idx,
                item=display_name,
                buff_price=f"€{item.buff_avg_price_eur:.2f}",
                steam_price=f"€{item.steam_avg_price_eur:.2f}",
                profit=f"€{item.profit_eur:.2f}",
                roi=f"{item.profitability_percent:.2f}%",
            )

            # Color based on ROI: green (>30%), yellow (20-30%), white (<20%)
            roi_color = (
                "\033[92m"
                if item.profitability_percent > 30
                else "\033[93m" if item.profitability_percent > 20 else "\033[0m"
            )

            click.echo(
                f"  {idx:2d}. \033[1m{display_name}\033[0m\n"
                f"      \033[96m€{item.buff_avg_price_eur:.2f}\033[0m → "
                f"\033[96m€{item.steam_avg_price_eur:.2f}\033[0m "
                f"({roi_color}€{item.profit_eur:.2f} - {item.profitability_percent:.2f}%\033[0m)"
            )
        click.echo(f"{'='*60}")


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
    click.echo(
        f"  Anti-ban delays: {settings.random_delay_min}-{settings.random_delay_max}ms"
    )


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
