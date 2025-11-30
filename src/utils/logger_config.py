"""
Configuración centralizada de logging para CS-Tracker
Logs rotativos con archivos separados por fecha
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(
    name: str = "cs_tracker",
    log_dir: str = "logs",
    log_level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 30,  # Mantener 30 archivos de backup
) -> logging.Logger:
    # Crear directorio de logs si no existe
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Crear logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Evitar duplicar handlers si ya existe
    if logger.handlers:
        return logger

    # Formato detallado para archivos
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Formato simple para consola
    console_formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )

    # --- Handler 1: Archivo rotativo general ---
    general_log_file = log_path / "scraper.log"
    file_handler = RotatingFileHandler(
        general_log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)  # Capturar todo en archivo
    file_handler.setFormatter(file_formatter)

    # --- Handler 2: Archivo diario de scrapings ---
    # Nombrado por fecha: scraping_2025-11-30.log
    today = datetime.now().strftime("%Y-%m-%d")
    scraping_log_file = log_path / f"scraping_{today}.log"
    scraping_handler = RotatingFileHandler(
        scraping_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    scraping_handler.setLevel(logging.INFO)  # Solo INFO y superiores
    scraping_handler.setFormatter(file_formatter)

    # --- Handler 3: Consola ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Añadir handlers al logger
    logger.addHandler(file_handler)
    logger.addHandler(scraping_handler)
    logger.addHandler(console_handler)

    return logger


def get_scraping_summary_logger(log_dir: str = "logs") -> logging.Logger:
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    summary_file = log_path / f"scraping_summary_{today}.log"

    # Logger separado para resúmenes
    summary_logger = logging.getLogger("scraping_summary")
    summary_logger.setLevel(logging.INFO)

    # Evitar duplicar handlers
    if summary_logger.handlers:
        return summary_logger

    # Formato específico para resúmenes
    summary_formatter = logging.Formatter(
        fmt="%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler para archivo de resúmenes
    summary_handler = logging.FileHandler(summary_file, encoding="utf-8")
    summary_handler.setFormatter(summary_formatter)

    summary_logger.addHandler(summary_handler)

    return summary_logger


def log_scraping_start(logger: logging.Logger, url: str, config: dict = None):
    logger.info("=" * 80)
    logger.info("INICIO DE SCRAPING")
    logger.info(f"URL: {url}")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")

    if config:
        logger.info("Configuración:")
        for key, value in config.items():
            logger.info(f"  - {key}: {value}")

    logger.info("=" * 80)


def log_scraping_end(
    logger: logging.Logger,
    items_found: int,
    duration_seconds: float,
    success: bool = True,
):
    status = "COMPLETADO" if success else "FALLIDO"

    logger.info("=" * 80)
    logger.info(f"{status} - FIN DE SCRAPING")
    logger.info(f"Items encontrados: {items_found}")
    logger.info(
        f"Duración: {duration_seconds:.2f} segundos ({duration_seconds/60:.2f} minutos)"
    )
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 80)


def log_item_processed(
    logger: logging.Logger, item_name: str, profit_eur: float, profitability: float
):
    logger.info(
        f"Item procesado: {item_name} | "
        f"Profit: €{profit_eur:.2f} | "
        f"ROI: {profitability:.2%}"
    )
