"""
Web scraper para SteamDT - Hanging (搬砖榜)
Extrae información de precios y arbitraje de skins de CS2
"""
import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from typing import List, Dict, Optional
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SteamDTScraper:
    """Scraper para extraer datos de la página de hanging/arbitraje"""
    
    def __init__(self, headless: bool = True):
        self.url = "https://steamdt.com/hanging"
        self.headless = headless
        self.data: List[Dict] = []
        
    async def scrape(self) -> List[Dict]:
        """
        Ejecuta el scraping principal
        
        Returns:
            Lista de diccionarios con los datos extraídos
        """
        logger.info(f"Iniciando scraping de {self.url}")
        
        async with async_playwright() as p:
            # Lanzar navegador
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            try:
                # Navegar a la página
                logger.info("Navegando a la página...")
                await page.goto(self.url, wait_until='networkidle', timeout=60000)
                
                # Esperar a que cargue el contenido dinámico
                logger.info("Esperando contenido dinámico...")
                await page.wait_for_timeout(5000)  # Esperar 5 segundos para JS
                
                # Cerrar modales si aparecen (nuevo feature popup)
                try:
                    close_button = page.locator('button:has-text("我已知晓")')
                    if await close_button.count() > 0:
                        await close_button.first.click()
                        logger.info("Modal cerrado")
                        await page.wait_for_timeout(1000)
                except Exception as e:
                    logger.debug(f"No se encontró modal o ya estaba cerrado: {e}")
                
                # Extraer datos de la tabla/lista de items
                items = await self._extract_items(page)
                
                logger.info(f"Se extrajeron {len(items)} items")
                self.data = items
                
            except PlaywrightTimeout as e:
                logger.error(f"Timeout al cargar la página: {e}")
                raise
            except Exception as e:
                logger.error(f"Error durante el scraping: {e}")
                raise
            finally:
                await browser.close()
        
        return self.data
    
    async def _extract_items(self, page) -> List[Dict]:
        """
        Extrae los items de la página
        
        Args:
            page: Objeto Page de Playwright
            
        Returns:
            Lista de items extraídos
        """
        items = []
        timestamp = datetime.utcnow().isoformat()
        
        try:
            # Intentar múltiples selectores para encontrar los items
            # Nota: Estos selectores pueden necesitar ajuste según la estructura real
            
            # Esperar más tiempo y ser más flexible con los selectores
            await page.wait_for_timeout(3000)  # Esperar 3 segundos adicionales
            
            # Intentar detectar elementos comunes en la página
            logger.info("Analizando estructura de la página...")
            
            # Guardar screenshot para depuración
            await page.screenshot(path="data/debug_screenshot.png")
            logger.info("Screenshot guardado en data/debug_screenshot.png")
            
            # Obtener el HTML para análisis
            content = await page.content()
            
            # Guardar HTML para análisis
            with open("data/page_content.html", "w", encoding="utf-8") as f:
                f.write(content)
            logger.info("HTML de la página guardado en data/page_content.html")
            
            # Intentar extraer datos de múltiples posibles estructuras
            # Probar diferentes selectores comunes
            selectors = [
                'table tbody tr',
                'div[class*="item"]',
                'div[class*="row"]',
                'li[class*="item"]',
                'div[class*="card"]',
                '[class*="list"] > div',
                '[class*="table"] tr'
            ]
            
            rows = []
            for selector in selectors:
                try:
                    temp_rows = await page.locator(selector).all()
                    if len(temp_rows) > 0:
                        logger.info(f"Encontrados {len(temp_rows)} elementos con selector: {selector}")
                        rows = temp_rows
                        break
                except:
                    continue
            
            logger.info(f"Se encontraron {len(rows)} filas/items para procesar")
            
            for idx, row in enumerate(rows):
                try:
                    # Extraer texto de toda la fila
                    text = await row.inner_text()
                    
                    # Crear item básico
                    item = {
                        'id': idx + 1,
                        'scraped_at': timestamp,
                        'raw_text': text.strip(),
                        'url': self.url
                    }
                    
                    # Intentar extraer campos específicos
                    # (Estos selectores deben ajustarse según la estructura real)
                    try:
                        name_elem = await row.locator('[class*="name"], .item-name, td:nth-child(1)').first
                        if name_elem:
                            item['item_name'] = await name_elem.inner_text()
                    except:
                        pass
                    
                    try:
                        price_elems = await row.locator('[class*="price"], .price, td:has-text("¥")').all()
                        if len(price_elems) >= 2:
                            item['buy_price'] = await price_elems[0].inner_text()
                            item['sell_price'] = await price_elems[1].inner_text()
                    except:
                        pass
                    
                    try:
                        profit_elem = await row.locator('[class*="profit"], .profit, [class*="rate"]').first
                        if profit_elem:
                            item['profit'] = await profit_elem.inner_text()
                    except:
                        pass
                    
                    items.append(item)
                    
                except Exception as e:
                    logger.warning(f"Error extrayendo item {idx}: {e}")
                    continue
            
            # Si no se encontraron items con la estructura esperada, guardar el HTML para análisis
            if len(items) == 0:
                logger.warning("No se encontraron items con los selectores actuales")
                logger.info("Guardando HTML de la página para análisis...")
                
                # Guardar snapshot del contenido
                items.append({
                    'type': 'html_snapshot',
                    'scraped_at': timestamp,
                    'content': content[:5000],  # Primeros 5000 caracteres
                    'url': self.url,
                    'note': 'Los selectores necesitan ajuste. Analiza este HTML.'
                })
                
        except Exception as e:
            logger.error(f"Error al extraer items: {e}")
            raise
        
        return items
    
    def save_to_json(self, filename: str = "scraped_data.json"):
        """
        Guarda los datos en un archivo JSON
        
        Args:
            filename: Nombre del archivo de salida
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        logger.info(f"Datos guardados en {filename}")


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
