"""
Script principal que orquesta el scraping y almacenamiento
Se ejecuta periódicamente via GitHub Actions
"""
import asyncio
import os
import sys
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
        scraper = SteamDTScraper(headless=True)
        items = await scraper.scrape()
        
        if not items:
            logger.warning("⚠️ No se extrajeron items")
            return
        
        logger.info(f"✅ {len(items)} items extraídos exitosamente")
        
        # 2. Guardar en archivo local (backup)
        scraper.save_to_json("data/latest_scrape.json")
        
        # 3. Guardar en Supabase
        logger.info("💾 Paso 2: Guardando en Supabase...")
        db = SupabaseDB()
        await db.save_scraped_items(items)
        
        logger.info("✅ Trabajo completado exitosamente")
        
        # 4. Estadísticas
        logger.info("\n📊 Estadísticas:")
        logger.info(f"  - Items procesados: {len(items)}")
        logger.info(f"  - Timestamp: {datetime.now().isoformat()}")
        
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
        db = SupabaseDB()
        
        # Obtener últimos 200 items
        recent_items = db.get_latest_items(limit=200)
        
        if not recent_items:
            logger.warning("No hay datos históricos para comparar")
            return
        
        # Agrupar por item_name y detectar cambios
        items_dict = {}
        for item in recent_items:
            name = item.get('item_name')
            if not name:
                continue
                
            if name not in items_dict:
                items_dict[name] = []
            items_dict[name].append(item)
        
        # Analizar cambios
        logger.info(f"\n📈 Items únicos rastreados: {len(items_dict)}")
        
        for name, history in items_dict.items():
            if len(history) >= 2:
                latest = history[0]
                previous = history[1]
                
                # Aquí puedes implementar lógica de comparación
                logger.debug(f"  {name}: {len(history)} registros históricos")
        
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
