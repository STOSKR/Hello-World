"""
Script principal que orquesta el scraping y almacenamiento
Se ejecuta periódicamente via GitHub Actions
"""

import asyncio
import os
import sys
import json
import glob
from datetime import datetime
from dotenv import load_dotenv

# Añadir directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from scraper import SteamDTScraper
from config_manager import load_config
import logging

# Crear directorio de logs ANTES de configurar logging
os.makedirs("logs", exist_ok=True)

# Timestamp para archivos
timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"logs/scraper_{timestamp_str}.log"

# Configurar logging con múltiples handlers
logging.basicConfig(
    level=logging.DEBUG,  # Cambiado a DEBUG para diagnóstico
    format="%(asctime)s - %(levelname)s - %(message)s",  # Sin nombre de logger
    handlers=[
        logging.StreamHandler(sys.stdout),  # Consola
        logging.FileHandler(
            log_filename, encoding="utf-8", mode="w"
        ),  # Archivo con timestamp
        logging.FileHandler(
            "logs/latest.log", mode="w", encoding="utf-8"
        ),  # Último log (sobrescrito)
    ],
    force=True,  # Forzar reconfiguración si ya existe
)
logger = logging.getLogger(__name__)

# Log inicial
logger.info(f"Log guardado en: {log_filename}")
logger.info(f"Log actualizado en: logs/latest.log")


async def run_scraping_job():
    """
    Ejecuta el trabajo completo de scraping y almacenamiento
    """
    logger.info("=" * 60)
    logger.info(f"Iniciando trabajo de scraping - {datetime.now()}")
    logger.info("=" * 60)

    try:
        # 1. Cargar configuración
        logger.info("Cargando configuración...")

        # Verificar si se especificó un preset (argumento 2)
        preset = None
        if len(sys.argv) > 2:
            preset = sys.argv[2]
            logger.info(f"Usando preset: {preset}")

        config = load_config(preset=preset)
        config.print_summary()

        # 2. Ejecutar scraper con configuración
        logger.info("Paso 1: Scraping de datos...")
        scraper = SteamDTScraper(config=config)
        items = await scraper.scrape()

        if not items:
            logger.warning("No se extrajeron items")
            return

        logger.info(f"{len(items)} items extraídos exitosamente")

        # 2. Guardar en archivo local (JSON)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"data/scrape_{timestamp_str}.json"
        scraper.save_to_json(json_filename)

        # También guardar como latest para fácil acceso
        scraper.save_to_json("data/latest_scrape.json")

        logger.info(f"Datos guardados en:")
        logger.info(f"  - {json_filename}")
        logger.info(f"  - data/latest_scrape.json")

        # 3. DESHABILITADO: Guardar en Supabase (comentado temporalmente)
        # logger.info("Paso 2: Guardando en Supabase...")
        # db = SupabaseDB()
        # await db.save_scraped_items(items)

        logger.info("Trabajo completado exitosamente")

        # 4. Estadísticas
        logger.info("\nEstadísticas:")
        logger.info(f"  - Items procesados: {len(items)}")
        logger.info(f"  - Timestamp: {datetime.now().isoformat()}")

        # Mostrar preview de algunos items
        logger.info("\nPreview (primeros 3 items):")
        for i, item in enumerate(items[:3], 1):
            logger.info(f"\n  Item {i}:")
            logger.info(f"    Nombre: {item.get('item_name', 'N/A')}")
            logger.info(f"    BUFF URL: {item.get('buff_url', 'N/A')}")
            logger.info(f"    Steam URL: {item.get('steam_url', 'N/A')}")
            logger.info(
                f"    Precio BUFF (EUR): €{item.get('buff_avg_price_eur', 'N/A')}"
            )
            logger.info(
                f"    Precio Steam (EUR): €{item.get('steam_avg_price_eur', 'N/A')}"
            )
            logger.info(
                f"    Rentabilidad: {item.get('profitability_ratio', 0)*100:.2f}%"
            )
            logger.info(f"    Profit: €{item.get('profit_eur', 'N/A')}")

        # Guardar resumen en archivo
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_items": len(items),
            "log_file": log_filename,
            "data_file": json_filename,
            "items_preview": items[:5] if len(items) > 0 else [],
        }

        summary_filename = f"logs/summary_{timestamp_str}.json"
        with open(summary_filename, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info(f"\nResumen guardado en: {summary_filename}")

        return True

    except Exception as e:
        logger.error(f"Error en el trabajo de scraping: {e}", exc_info=True)
        raise


async def compare_with_history():
    logger.info("\nAnalizando cambios en el historial...")

    try:
        # DESHABILITADO: Comparación con base de datos
        # db = SupabaseDB()
        # recent_items = db.get_latest_items(limit=200)

        # En su lugar, comparar archivos JSON locales
        json_files = sorted(glob.glob("data/scrape_*.json"))

        if len(json_files) < 2:
            logger.info("No hay suficientes archivos históricos para comparar")
            return

        # Cargar los dos archivos más recientes
        with open(json_files[-1], "r", encoding="utf-8") as f:
            latest_data = json.load(f)

        with open(json_files[-2], "r", encoding="utf-8") as f:
            previous_data = json.load(f)

        logger.info(f"\nComparando:")
        logger.info(f"  - Archivo anterior: {json_files[-2]}")
        logger.info(f"  - Archivo actual: {json_files[-1]}")
        logger.info(f"  - Items anteriores: {len(previous_data)}")
        logger.info(f"  - Items actuales: {len(latest_data)}")

    except Exception as e:
        logger.error(f"Error en comparación histórica: {e}")


def main():
    # Cargar variables de entorno
    load_dotenv()

    # Crear directorio de datos si no existe
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/screenshots", exist_ok=True)

    # Mostrar ayuda de uso
    print("\nUso: python src/main.py [HEADLESS] [PRESET]")
    print("  HEADLESS: 0 = oculto (defecto), 1 = visible")
    print("  PRESET: 1-6 = configuracion predefinida")
    print("\nPresets disponibles:")
    print("  1: STEAM Balance - Sell at STEAM Lowest Price")
    print("  2: STEAM Balance - Sell to STEAM Highest Buy Order")
    print("  3: Platform Balance - Lowest Buy + Lowest Sell")
    print("  4: Platform Balance - Lowest Buy + Highest Sell Order")
    print("  5: Platform Balance - Buy Order + Lowest Sell")
    print("  6: Platform Balance - Buy Order + Highest Sell Order")
    print("\nEjemplos:")
    print("  python src/main.py          # Headless, config por defecto")
    print("  python src/main.py 1        # Visible, config por defecto")
    print("  python src/main.py 0 3      # Headless, preset 3")
    print("  python src/main.py 1 2      # Visible, preset 2")
    print()

    # Procesar argumentos de línea de comandos para headless
    headless_mode = True
    if len(sys.argv) > 1:
        if sys.argv[1] == "1":
            headless_mode = False
            logger.info("Modo headless DESACTIVADO (navegador visible)")
        elif sys.argv[1] == "0":
            headless_mode = True
            logger.info("Modo headless ACTIVADO (navegador oculto)")
    else:
        logger.info(
            "Modo headless ACTIVADO por defecto (usa '1' para ver el navegador)"
        )

    # Guardar en variable de entorno para que el scraper lo use
    os.environ["SCRAPER_HEADLESS"] = str(headless_mode)

    try:
        # Ejecutar scraping
        success = asyncio.run(run_scraping_job())

        if success:
            # Analizar historial
            asyncio.run(compare_with_history())

        logger.info("\n" + "=" * 60)
        logger.info("Proceso completado")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.info("\nProceso interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\nError fatal: {e}")
        sys.exit(1)
    finally:
        # Limpiar event loop en Windows para evitar warnings
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.stop()
            if not loop.is_closed():
                loop.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
