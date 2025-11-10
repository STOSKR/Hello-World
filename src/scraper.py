import asyncio
import json
from playwright.async_api import TimeoutError as PlaywrightTimeout
from typing import List, Dict, Optional
import logging
from config_manager import ScraperConfig
from scrapers import BrowserManager, FilterManager, ItemExtractor, DetailedItemExtractor, FileSaver

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SteamDTScraper:
    """Scraper para extraer datos de la página de hanging/arbitraje (Refactorizado)"""
    
    def __init__(self, config: Optional[ScraperConfig] = None, headless: Optional[bool] = None):
        """
        Inicializa el scraper
        
        Args:
            config: Instancia de ScraperConfig (si no se proporciona, carga desde archivo)
            headless: Sobrescribe el valor de headless del config (opcional)
        """
        self.config = config or ScraperConfig()
        self.url = "https://steamdt.com/en/hanging"
        
        # Prioridad: 1) argumento headless, 2) variable entorno, 3) config
        import os
        if headless is not None:
            self.headless = headless
        elif 'SCRAPER_HEADLESS' in os.environ:
            self.headless = os.environ['SCRAPER_HEADLESS'].lower() == 'true'
        else:
            self.headless = self.config.get('scraper.headless')
        
        self.data: List[Dict] = []
        
        # Configurar nivel de log según config
        log_level = self.config.get('debug.log_level', 'INFO')
        logging.getLogger().setLevel(getattr(logging, log_level))
        
        # Inicializar módulos
        self.filter_manager = FilterManager(self.config)
        self.item_extractor = ItemExtractor()
        self.detailed_extractor = DetailedItemExtractor()
        self.file_saver = FileSaver(self.config)
        
    async def scrape(self) -> List[Dict]:
        """
        Ejecuta el proceso completo de scraping
        
        Returns:
            Lista de items extraídos con datos detallados
        """
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
                logger.info("📋 Paso 1: Extrayendo lista de items...")
                basic_items = await self.item_extractor.extract_items(page, self.url)
                
                logger.info(f"✅ Se encontraron {len(basic_items)} items en la lista")
                
                # Procesar cada item en detalle
                logger.info("📋 Paso 2: Procesando cada item en detalle...")
                detailed_items = []
                
                # Configurar procesamiento paralelo
                MAX_CONCURRENT = 3  # Número de items a procesar en paralelo
                
                async def process_item_with_page(item, idx, total):
                    """Procesa un item en una nueva página del navegador"""
                    # Crear nueva página para este item
                    new_page = await browser_manager.context.new_page()
                    
                    try:
                        logger.info(f"\n{'='*60}")
                        logger.info(f"Item {idx}/{total}")
                        logger.info(f"{'='*60}")
                        
                        # Verificar que el item tenga URL
                        item_url = item.get('url')
                        item_name = item.get('item_name', 'Unknown')
                        
                        if not item_url:
                            logger.warning(f"⚠️ Item sin URL, omitiendo: {item_name}")
                            return None
                        
                        # Extraer datos detallados usando la nueva página
                        detailed_data = await self.detailed_extractor.extract_detailed_item(
                            new_page, 
                            item_url, 
                            item_name
                        )
                        
                        if detailed_data:
                            logger.info(f"✅ Item {idx} agregado a la lista final")
                            return detailed_data
                        else:
                            logger.info(f"❌ Item {idx} descartado")
                            return None
                    
                    finally:
                        # Cerrar la página
                        await new_page.close()
                
                # Procesar items en lotes paralelos
                for i in range(0, len(basic_items), MAX_CONCURRENT):
                    batch = basic_items[i:i + MAX_CONCURRENT]
                    batch_number = (i // MAX_CONCURRENT) + 1
                    total_batches = (len(basic_items) + MAX_CONCURRENT - 1) // MAX_CONCURRENT
                    
                    logger.info(f"\n🔄 Procesando lote {batch_number}/{total_batches} ({len(batch)} items en paralelo)")
                    
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
                            logger.error(f"❌ Error en procesamiento paralelo: {result}")
                    
                    # Pequeña pausa entre lotes
                    await page.wait_for_timeout(2000)
                
                logger.info(f"\n{'='*60}")
                logger.info(f"✅ Procesamiento completado")
                logger.info(f"   Items iniciales: {len(basic_items)}")
                logger.info(f"   Items finales: {len(detailed_items)}")
                logger.info(f"   Items descartados: {len(basic_items) - len(detailed_items)}")
                logger.info(f"{'='*60}\n")
                
                self.data = detailed_items
                
                # Guardar archivos de debug si está habilitado
                await self.file_saver.save_debug_files(page)
                
            except PlaywrightTimeout as e:
                logger.error(f"Timeout al cargar la página: {e}")
                raise
            except Exception as e:
                logger.error(f"Error durante el scraping: {e}")
                raise
        
        return self.data
    
    def save_to_json(self, filename: str = "scraped_data.json"):
        """
        Guarda los datos en un archivo JSON
        
        Args:
            filename: Nombre del archivo de salida
        """
        self.file_saver.save_json(self.data, filename)


async def main():
    """Función principal para testing"""
    scraper = SteamDTScraper(headless=False)  # headless=False para ver el navegador
    
    try:
        data = await scraper.scrape()
        scraper.save_to_json("output.json")
        
        print(f"\n✅ Scraping completado!")
        print(f"📊 Items extraídos: {len(data)}")
        print(f"💾 Datos guardados en output.json")
        
        # Mostrar preview
        if data:
            print("\n📋 Preview del primer item:")
            print(json.dumps(data[0], indent=2, ensure_ascii=False))
        
    except Exception as e:
        logger.error(f"Error en el scraping: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
