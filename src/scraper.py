import asyncio
import json
import signal
import time
import sys
from datetime import datetime
from playwright.async_api import TimeoutError as PlaywrightTimeout
from typing import List, Dict, Optional
import logging
from config_manager import ScraperConfig
from scrapers import (
    BrowserManager,
    FilterManager,
    ItemExtractor,
    DetailedItemExtractor,
    FileSaver,
)
from utils.logger_config import (
    setup_logger,
    get_scraping_summary_logger,
    log_scraping_start,
    log_scraping_end,
    log_item_processed,
)

# Configurar logging centralizado
logger = setup_logger(name="cs_tracker", log_level="INFO")
summary_logger = get_scraping_summary_logger()


class SteamDTScraper:
    """Scraper para extraer datos de la página de hanging/arbitraje (Refactorizado)"""

    def __init__(
        self, config: Optional[ScraperConfig] = None, headless: Optional[bool] = None
    ):
        self.config = config or ScraperConfig()
        self.url = "https://steamdt.com/en/hanging"

        # Prioridad: 1) argumento headless, 2) variable entorno, 3) config
        import os

        if headless is not None:
            self.headless = headless
        elif "SCRAPER_HEADLESS" in os.environ:
            self.headless = os.environ["SCRAPER_HEADLESS"].lower() == "true"
        else:
            self.headless = self.config.get("scraper.headless")

        self.data: List[Dict] = []

        # Configurar nivel de log según config
        log_level = self.config.get("debug.log_level", "INFO")
        logging.getLogger().setLevel(getattr(logging, log_level))

        # Inicializar módulos
        self.filter_manager = FilterManager(self.config)
        self.item_extractor = ItemExtractor()
        self.detailed_extractor = DetailedItemExtractor()
        self.file_saver = FileSaver(self.config)

    async def scrape(self) -> List[Dict]:
        start_time = time.time()

        # Log inicio de scraping
        config_summary = {
            "currency": self.config.get("currency.code"),
            "sell_mode": self.config.get("price_mode.sell_mode"),
            "balance_type": self.config.get("balance_type.type"),
            "min_price": self.config.get("filters.min_price"),
            "max_price": self.config.get("filters.max_price"),
            "min_volume": self.config.get("filters.min_volume"),
        }
        log_scraping_start(logger, self.url, config_summary)
        log_scraping_start(summary_logger, self.url, config_summary)

        logger.info(f"Iniciando scraping de {self.url}")

        # Usar BrowserManager para gestionar el navegador
        async with BrowserManager(headless=self.headless) as browser_manager:
            page = browser_manager.get_page()

            try:
                # Navegar a la página principal
                await browser_manager.navigate(self.url, timeout=60000)

                # Esperar a que cargue el contenido dinámico
                logger.info("Esperando contenido dinámico...")
                await browser_manager.wait(5000)

                # Cerrar modales si aparecen
                await browser_manager.close_modal()

                # Configurar todos los filtros usando FilterManager
                await self.filter_manager.configure_all_filters(page)

                # Extraer lista básica de items usando ItemExtractor
                logger.info("Paso 1: Extrayendo lista de items...")
                basic_items = await self.item_extractor.extract_items(page, self.url)

                logger.info(f"Se encontraron {len(basic_items)} items en la lista")

                # Procesar cada item en detalle
                logger.info("Paso 2: Procesando cada item en detalle...")
                detailed_items = []

                # Configurar procesamiento paralelo
                MAX_CONCURRENT = 5  # Número de items a procesar en paralelo

                async def process_item_with_page(item, idx, total):
                    """Procesa un item en una nueva página del navegador"""
                    # Crear nueva página para este item
                    new_page = await browser_manager.context.new_page()

                    try:
                        logger.info(f"\n{'='*60}")
                        logger.info(f"Item {idx}/{total}")
                        logger.info(f"{'='*60}")

                        # Verificar que el item tenga URL
                        item_url = item.get("url")
                        item_name = item.get("item_name", "Unknown")
                        buff_url = item.get("buff_url")
                        steam_url = item.get("steam_url")

                        if not item_url:
                            logger.warning(f"Item sin URL, omitiendo: {item_name}")
                            return None

                        # Extraer datos detallados usando la nueva página
                        # Pasar las URLs de BUFF y Steam ya extraídas para evitar navegación duplicada
                        detailed_data = (
                            await self.detailed_extractor.extract_detailed_item(
                                new_page,
                                item_url,
                                item_name,
                                buff_url=buff_url,
                                steam_url=steam_url,
                            )
                        )

                        if detailed_data:
                            logger.info(f"Item {idx} agregado a la lista final")

                            # Log item procesado
                            log_item_processed(
                                logger,
                                item_name,
                                detailed_data.get("profit_eur", 0),
                                detailed_data.get("profitability_%", 0),
                            )
                            log_item_processed(
                                summary_logger,
                                item_name,
                                detailed_data.get("profit_eur", 0),
                                detailed_data.get("profitability_%", 0),
                            )

                            return detailed_data
                        else:
                            logger.info(f"Item {idx} descartado")
                            return None

                    finally:
                        # Cerrar la página
                        await new_page.close()

                # Procesar items en lotes paralelos
                for i in range(0, len(basic_items), MAX_CONCURRENT):
                    batch = basic_items[i : i + MAX_CONCURRENT]
                    batch_number = (i // MAX_CONCURRENT) + 1
                    total_batches = (
                        len(basic_items) + MAX_CONCURRENT - 1
                    ) // MAX_CONCURRENT

                    logger.info(
                        f"\nProcesando lote {batch_number}/{total_batches} ({len(batch)} items en paralelo)"
                    )

                    # Crear tareas para procesar items en paralelo
                    tasks = [
                        process_item_with_page(item, i + idx + 1, len(basic_items))
                        for idx, item in enumerate(batch)
                    ]

                    # Ejecutar en paralelo
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Recopilar resultados válidos
                    for result in results:
                        if result and not isinstance(result, Exception):
                            detailed_items.append(result)
                        elif isinstance(result, Exception):
                            logger.error(f"Error en procesamiento paralelo: {result}")

                    # Guardar progreso parcial después de cada lote para minimizar pérdida
                    try:
                        partial_filename = f"partial_save_batch_{batch_number}.json"
                        self.file_saver.save_json(detailed_items, partial_filename)
                        logger.info(f"Progreso parcial guardado: {partial_filename}")
                    except Exception as e:
                        logger.warning(f"No se pudo guardar progreso parcial: {e}")

                    # Pequeña pausa entre lotes
                    await page.wait_for_timeout(2000)

                logger.info(f"\n{'='*60}")
                logger.info(f"Procesamiento completado")
                logger.info(f"   Items iniciales: {len(basic_items)}")
                logger.info(f"   Items finales: {len(detailed_items)}")
                logger.info(
                    f"   Items descartados: {len(basic_items) - len(detailed_items)}"
                )
                logger.info(f"{'='*60}\n")

                self.data = detailed_items

                # Log scraping exitoso
                duration = time.time() - start_time
                log_scraping_end(logger, len(detailed_items), duration, success=True)
                log_scraping_end(
                    summary_logger, len(detailed_items), duration, success=True
                )

                # Guardar archivos de debug si está habilitado
                await self.file_saver.save_debug_files(page)

            except PlaywrightTimeout as e:
                logger.error(f"Timeout al cargar la página: {e}")

                # Log scraping fallido
                duration = time.time() - start_time
                log_scraping_end(logger, 0, duration, success=False)
                log_scraping_end(summary_logger, 0, duration, success=False)

                # Guardar progreso antes de propagar
                try:
                    timestamp = int(time.time())
                    self.file_saver.save_json(
                        self.data or detailed_items,
                        f"interrupted_timeout_{timestamp}.json",
                    )
                except Exception as e_save:
                    logger.warning(f"Error guardando datos tras timeout: {e_save}")
                raise
            except KeyboardInterrupt:
                # Usuario interrumpió; salvar datos parciales inmediatamente
                logger.info(
                    "KeyboardInterrupt recibido. Guardando datos parciales antes de salir..."
                )

                # Log scraping interrumpido
                duration = time.time() - start_time
                items_count = (
                    len(self.data or detailed_items)
                    if "detailed_items" in locals()
                    else 0
                )
                log_scraping_end(logger, items_count, duration, success=False)
                log_scraping_end(summary_logger, items_count, duration, success=False)

                try:
                    timestamp = int(time.time())
                    self.file_saver.save_json(
                        self.data or detailed_items, f"interrupted_{timestamp}.json"
                    )
                    logger.info("Datos parciales guardados.")
                except Exception as e_save:
                    logger.error(f"Error guardando datos al interrumpir: {e_save}")
                raise
            except Exception as e:
                logger.error(f"Error durante el scraping: {e}")

                # Log scraping con error
                duration = time.time() - start_time
                items_count = (
                    len(self.data or detailed_items)
                    if "detailed_items" in locals()
                    else 0
                )
                log_scraping_end(logger, items_count, duration, success=False)
                log_scraping_end(summary_logger, items_count, duration, success=False)

                # Guardar progreso parcial
                try:
                    timestamp = int(time.time())
                    self.file_saver.save_json(
                        self.data or detailed_items,
                        f"interrupted_error_{timestamp}.json",
                    )
                except Exception as e_save:
                    logger.warning(f"Error guardando datos tras excepción: {e_save}")
                raise

        return self.data

    def save_to_json(self, filename: str = "scraped_data.json"):
        self.file_saver.save_json(self.data, filename)


async def main():
    """Función principal para testing"""
    scraper = SteamDTScraper(headless=False)  # headless=False para ver el navegador

    # Registrar manejador de SIGINT para guardar datos parciales si el usuario
    # interrumpe la ejecución con Ctrl+C
    def _handle_sigint(signum, frame):
        try:
            timestamp = int(time.time())
            filename = f"interrupted_sigint_{timestamp}.json"
            scraper.file_saver.save_json(scraper.data or [], filename)
            logger.info(f"SIGINT recibido: datos parciales guardados en {filename}")
        except Exception as e:
            logger.error(f"Error guardando datos tras SIGINT: {e}")
        finally:
            # Salir inmediatamente
            sys.exit(0)

    try:
        signal.signal(signal.SIGINT, _handle_sigint)
    except Exception:
        # Algunos entornos (ej. ciertos REPLs) pueden no permitir registro de señales
        logger.debug("No se pudo registrar manejador de SIGINT")

    try:
        data = await scraper.scrape()
        scraper.save_to_json("output.json")

        print(f"\nScraping completado!")
        print(f"Items extraídos: {len(data)}")
        print(f"Datos guardados en output.json")

        # Mostrar preview
        if data:
            print("\nPreview del primer item:")
            print(json.dumps(data[0], indent=2, ensure_ascii=False))

    except KeyboardInterrupt:
        # Catch in case signal handler wasn't registered; asegurar guardado
        logger.info(
            "Interrupción por teclado detectada en main. Guardando datos parciales..."
        )
        try:
            timestamp = int(time.time())
            scraper.file_saver.save_json(
                scraper.data or [], f"interrupted_keyboard_{timestamp}.json"
            )
            logger.info("Datos parciales guardados desde main.")
        except Exception as e:
            logger.error(f"Error guardando datos en KeyboardInterrupt: {e}")
        raise
    except Exception as e:
        logger.error(f"Error en el scraping: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
