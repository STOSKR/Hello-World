"""Structured JSON logging without emojis"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from structlog.processors import JSONRenderer
from structlog.stdlib import add_log_level, filter_by_level

from app.core.config import settings


def add_timestamp(logger: Any, method_name: str, event_dict: Dict) -> Dict:
    """Add ISO timestamp to log entries"""
    event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return event_dict


def configure_logging(
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
    log_file: Optional[Path] = None,
) -> None:
    """Configure structured logging for the application
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: Format type ('json' or 'text')
        log_file: Optional file path for log output
    """
    level = log_level or settings.log_level
    format_type = log_format or settings.log_format

    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level),
    )

    # Setup processors based on format
    processors = [
        filter_by_level,
        add_log_level,
        add_timestamp,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if format_type == "json":
        processors.append(JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Optional file handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(getattr(logging, level))
        logging.root.addHandler(file_handler)


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


# Auto-configure on import
configure_logging()
