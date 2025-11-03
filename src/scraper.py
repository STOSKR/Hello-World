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
        self.url = "https://steamdt.com/en/hanging"
        self.headless = headless
        self.data: List[Dict] = []
        
    async def scrape(self) -> List[Dict]:
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

                # Cambiar moneda a EUR (euros)
                await self._change_currency_to_eur(page)
                
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
    
    async def _change_currency_to_eur(self, page):
        """
        Cambia la moneda a EUR (euros)
        """
        try:
            logger.info("Cambiando moneda a EUR...")
            
            # Buscar el selector de moneda (puede tener CNY, USD, etc.)
            currency_selector = page.locator('.el-dropdown-link:has-text("CNY"), .el-dropdown-link:has-text("¥")')
            
            if await currency_selector.count() > 0:
                # Click en el dropdown de moneda
                await currency_selector.first.click()
                await page.wait_for_timeout(1000)
                
                # Buscar y hacer click en "EUR"
                eur_option = page.locator('li:has-text("EUR"), li:has-text("€")')
                if await eur_option.count() > 0:
                    await eur_option.first.click()
                    logger.info("✅ Moneda cambiada a EUR")
                    await page.wait_for_timeout(3000)  # Esperar a que recargue los precios
                else:
                    logger.warning("No se encontró opción EUR en el menú")
            else:
                logger.info("✅ La moneda ya está configurada o no se encontró el selector")
                
        except Exception as e:
            logger.warning(f"No se pudo cambiar la moneda: {e}")
    
    async def _extract_items(self, page) -> List[Dict]:
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
                    # Extraer todas las celdas (td) de la fila
                    cells = await row.locator('td').all()
                    
                    if len(cells) < 6:
                        logger.debug(f"Fila {idx} tiene menos de 6 columnas, omitiendo")
                        continue

                    # Estructura real según el HTML proporcionado:
                    # Columna 0: Ranking
                    # Columna 1: Nombre del item (ej: "G3SG1 | Orange Crash (Well-Worn)")
                    # Columna 2: BUFF - Precio de compra + tiempo (ej: €0.14, "24 minutes ago")
                    # Columna 3: STEAM - Precio de venta + tiempo (ej: €0.44, "35 minutes ago")
                    # Columna 4: Precio neto de venta (ej: €0.39)
                    # Columna 5: Volumen/Ventas (ej: 28)
                    # Columna 6: Ratio compra/venta (ej: 0.358)
                    # Columna 7: Segundo ratio (ej: 0.362)
                    # Columna 8: Acciones

                    item = {
                        'id': idx + 1,
                        'scraped_at': timestamp,
                        'url': self.url
                    }
                    
                    # Columna 1: Nombre del item completo
                    try:
                        name_cell = cells[1] if len(cells) > 1 else None
                        if name_cell:
                            # Buscar el enlace <a> que contiene el nombre completo
                            name_link = await name_cell.locator('a').first.inner_text()
                            item['item_name'] = name_link.strip()
                    except Exception as e:
                        logger.debug(f"No se pudo extraer nombre en fila {idx}: {e}")
                        item['item_name'] = None
                    
                    # Columna 2: BUFF - Precio de compra
                    try:
                        buff_cell = cells[2] if len(cells) > 2 else None
                        if buff_cell:
                            # Extraer el precio (dentro del span)
                            buff_price = await buff_cell.locator('span').first.inner_text()
                            item['buff_price'] = buff_price.strip()
                            
                            # Extraer el tiempo (div con class text-12)
                            try:
                                buff_time = await buff_cell.locator('.text-12').first.inner_text()
                                item['buff_time'] = buff_time.strip()
                            except:
                                item['buff_time'] = None
                    except Exception as e:
                        logger.debug(f"No se pudo extraer precio BUFF en fila {idx}: {e}")
                        item['buff_price'] = None
                        item['buff_time'] = None
                    
                    # Columna 3: STEAM - Precio de venta
                    try:
                        steam_cell = cells[3] if len(cells) > 3 else None
                        if steam_cell:
                            # Extraer el precio
                            steam_price = await steam_cell.locator('span').first.inner_text()
                            item['steam_price'] = steam_price.strip()
                            
                            # Extraer el tiempo
                            try:
                                steam_time = await steam_cell.locator('.text-12').first.inner_text()
                                item['steam_time'] = steam_time.strip()
                            except:
                                item['steam_time'] = None
                    except Exception as e:
                        logger.debug(f"No se pudo extraer precio STEAM en fila {idx}: {e}")
                        item['steam_price'] = None
                        item['steam_time'] = None
                    
                    # Columna 4: Precio neto de venta (después de comisiones Steam)
                    try:
                        net_price_cell = cells[4] if len(cells) > 4 else None
                        if net_price_cell:
                            net_price = await net_price_cell.inner_text()
                            item['net_sale_price'] = net_price.strip()
                    except Exception as e:
                        logger.debug(f"No se pudo extraer precio neto en fila {idx}: {e}")
                        item['net_sale_price'] = None
                    
                    # Columna 5: Volumen de ventas
                    try:
                        volume_cell = cells[5] if len(cells) > 5 else None
                        if volume_cell:
                            volume = await volume_cell.inner_text()
                            item['volume'] = volume.strip()
                    except Exception as e:
                        logger.debug(f"No se pudo extraer volumen en fila {idx}: {e}")
                        item['volume'] = None
                    
                    # Columna 6: Ratio de compra/venta (BUFF/Steam)
                    try:
                        ratio_cell = cells[6] if len(cells) > 6 else None
                        if ratio_cell:
                            ratio = await ratio_cell.inner_text()
                            item['buy_sell_ratio'] = ratio.strip()
                    except Exception as e:
                        logger.debug(f"No se pudo extraer ratio en fila {idx}: {e}")
                        item['buy_sell_ratio'] = None
                    
                    # Columna 7: Segundo ratio (opcional)
                    try:
                        ratio2_cell = cells[7] if len(cells) > 7 else None
                        if ratio2_cell:
                            ratio2 = await ratio2_cell.inner_text()
                            item['secondary_ratio'] = ratio2.strip()
                    except:
                        item['secondary_ratio'] = None
                    
                    # Solo agregar si tiene nombre
                    if item.get('item_name'):
                        items.append(item)
                    else:
                        logger.debug(f"Fila {idx} sin nombre, omitiendo")
                    
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
