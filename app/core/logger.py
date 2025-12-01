"""Structured JSON logging without emojis with rotating file handlers"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler

import structlog
from structlog.processors import JSONRenderer
from structlog.stdlib import add_log_level, filter_by_level

from app.core.config import settings


def add_timestamp(logger: Any, method_name: str, event_dict: Dict) -> Dict:
    """Add compact timestamp to log entries"""
    # Formato compacto: HH:MM:SS en lugar de ISO completo
    event_dict["timestamp"] = datetime.now().strftime("%H:%M:%S")
    return event_dict


def configure_logging(
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
    log_dir: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 30,  # Keep 30 backup files
) -> None:
    """Configure structured logging with rotating file handlers

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: Format type ('json' or 'text')
        log_dir: Directory for log files (default: 'logs')
        max_bytes: Maximum size per log file before rotation
        backup_count: Number of backup files to keep
    """
    level = log_level or settings.log_level
    format_type = log_format or settings.log_format
    log_directory = Path(log_dir or "logs")
    log_directory.mkdir(parents=True, exist_ok=True)

    # Single log file (rotating) - no duplicados
    log_file = log_directory / "scraper.log"

    # File handler sin colores ANSI
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )

    # Console handler con colores
    console_handler = logging.StreamHandler(sys.stdout)

    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, level),
        handlers=[file_handler, console_handler],
    )

    # Processors para archivos (sin colores)
    file_processors = [
        filter_by_level,
        add_log_level,
        add_timestamp,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if format_type == "json":
        file_processors.append(JSONRenderer())
    else:
        # Texto plano para archivos (sin códigos ANSI)
        file_processors.append(
            structlog.dev.ConsoleRenderer(
                colors=False,  # Sin colores en archivos
                pad_event=30,
            )
        )

    # Processors para consola (con colores)
    console_processors = [
        filter_by_level,
        add_log_level,
        add_timestamp,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(
            colors=True,  # Colores solo en consola
            pad_event=30,
        ),
    ]

    # Configure structlog (usar procesadores de consola por defecto para colores)
    structlog.configure(
        processors=console_processors,  # Colores en consola por defecto
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured structlog logger

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("scraping_started", url="https://example.com", items=10)
    """
    return structlog.get_logger(name)


# Legacy helpers for compatibility with src/


def get_scraping_summary_logger(log_dir: str = "logs") -> logging.Logger:
    """Get logger for scraping summaries (legacy compatibility)."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    summary_file = log_path / f"scraping_summary_{today}.log"

    # Separate logger for summaries
    summary_logger = logging.getLogger("scraping_summary")
    summary_logger.setLevel(logging.INFO)

    # Avoid duplicating handlers
    if summary_logger.handlers:
        return summary_logger

    # Specific format for summaries
    summary_formatter = logging.Formatter(
        fmt="%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler for summary file
    summary_handler = logging.FileHandler(summary_file, encoding="utf-8")
    summary_handler.setFormatter(summary_formatter)

    summary_logger.addHandler(summary_handler)

    return summary_logger


def log_scraping_start(logger, url: str, config: dict = None):
    """Log scraping start event."""
    logger.info("=" * 80)
    logger.info("scraping_started", url=url, timestamp=datetime.now().isoformat())

    if config:
        logger.info("scraping_configuration", config=config)

    logger.info("=" * 80)


def log_scraping_end(
    logger, items_found: int, duration_seconds: float, success: bool = True
):
    """Log scraping end event."""
    status = "completed" if success else "failed"

    logger.info("=" * 80)
    logger.info(
        "scraping_finished",
        status=status,
        items_found=items_found,
        duration_seconds=round(duration_seconds, 2),
        duration_minutes=round(duration_seconds / 60, 2),
        timestamp=datetime.now().isoformat(),
    )
    logger.info("=" * 80)


def log_item_processed(logger, item_name: str, profit_eur: float, profitability: float):
    """Log individual item processing."""
    logger.info(
        "item_processed",
        item_name=item_name,
        profit_eur=round(profit_eur, 2),
        roi=f"{profitability:.2%}",
    )


# Auto-configure on import
configure_logging()
