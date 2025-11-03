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
from database import SupabaseDB
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('scraper.log')
    ]
)
logger = logging.getLogger(__name__)


async def run_scraping_job():
    """
    Ejecuta el trabajo completo de scraping y almacenamiento
    """
    logger.info("=" * 60)
    logger.info(f"🚀 Iniciando trabajo de scraping - {datetime.now()}")
    logger.info("=" * 60)
    
    try:
        # 1. Ejecutar scraper
        logger.info("📡 Paso 1: Scraping de datos...")
        scraper = SteamDTScraper(headless=True)  # Modo headless
        items = await scraper.scrape()
        
        if not items:
            logger.warning("⚠️ No se extrajeron items")
            return
        
        logger.info(f"✅ {len(items)} items extraídos exitosamente")
        
        # 2. Guardar en archivo local (JSON)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"data/scrape_{timestamp_str}.json"
        scraper.save_to_json(json_filename)
        
        # También guardar como latest para fácil acceso
        scraper.save_to_json("data/latest_scrape.json")
        
        logger.info(f"💾 Datos guardados en:")
        logger.info(f"  - {json_filename}")
        logger.info(f"  - data/latest_scrape.json")
        
        # 3. DESHABILITADO: Guardar en Supabase (comentado temporalmente)
        # logger.info("💾 Paso 2: Guardando en Supabase...")
        # db = SupabaseDB()
        # await db.save_scraped_items(items)
        
        logger.info("✅ Trabajo completado exitosamente")
        
        # 4. Estadísticas
        logger.info("\n📊 Estadísticas:")
        logger.info(f"  - Items procesados: {len(items)}")
        logger.info(f"  - Timestamp: {datetime.now().isoformat()}")
        
        # Mostrar preview de algunos items
        logger.info("\n📋 Preview (primeros 3 items):")
        for i, item in enumerate(items[:3], 1):
            logger.info(f"\n  Item {i}:")
            logger.info(f"    Nombre: {item.get('item_name', 'N/A')}")
            logger.info(f"    Plataforma: {item.get('platform', 'N/A')}")
            logger.info(f"    Precio plataforma: {item.get('platform_price', 'N/A')}")
            logger.info(f"    Precio Steam: {item.get('steam_price', 'N/A')}")
            logger.info(f"    Profit: {item.get('profit', 'N/A')}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en el trabajo de scraping: {e}", exc_info=True)
        raise


async def compare_with_history():
    """
    Compara los últimos datos con el historial
    Detecta cambios significativos
    """
    logger.info("\n🔍 Analizando cambios en el historial...")
    
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
        with open(json_files[-1], 'r', encoding='utf-8') as f:
            latest_data = json.load(f)
        
        with open(json_files[-2], 'r', encoding='utf-8') as f:
            previous_data = json.load(f)
        
        logger.info(f"\n📈 Comparando:")
        logger.info(f"  - Archivo anterior: {json_files[-2]}")
        logger.info(f"  - Archivo actual: {json_files[-1]}")
        logger.info(f"  - Items anteriores: {len(previous_data)}")
        logger.info(f"  - Items actuales: {len(latest_data)}")
        
    except Exception as e:
        logger.error(f"Error en comparación histórica: {e}")


def main():
    """Función principal"""
    # Cargar variables de entorno
    load_dotenv()
    
    # Crear directorio de datos si no existe
    os.makedirs("data", exist_ok=True)
    
    try:
        # Ejecutar scraping
        success = asyncio.run(run_scraping_job())
        
        if success:
            # Analizar historial
            asyncio.run(compare_with_history())
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Proceso completado")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Proceso interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ Error fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
