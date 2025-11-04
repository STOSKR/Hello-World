import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from typing import List, Dict, Optional
import logging
from config_manager import ScraperConfig

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SteamDTScraper:
    """Scraper para extraer datos de la página de hanging/arbitraje"""
    
    def __init__(self, config: Optional[ScraperConfig] = None, headless: Optional[bool] = None):
        """
        Inicializa el scraper
        
        Args:
            config: Instancia de ScraperConfig (si no se proporciona, carga desde archivo)
            headless: Sobrescribe el valor de headless del config (opcional)
        """
        self.config = config or ScraperConfig()
        self.url = "https://steamdt.com/en/hanging"
        
        # headless puede ser sobrescrito o tomado del config
        self.headless = headless if headless is not None else self.config.get('scraper.headless')
        self.data: List[Dict] = []
        
        # Configurar nivel de log según config
        log_level = self.config.get('debug.log_level', 'INFO')
        logging.getLogger().setLevel(getattr(logging, log_level))
        
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

                # Configurar todos los filtros (moneda, precio, volumen, plataforma)
                await self._configure_filters(page)
                
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
    
    async def _configure_filters(self, page):
        """Configura todos los filtros antes de scrapear usando la configuración"""
        logger.info("Configurando filtros de búsqueda...")
        
        # 1. Verificar y cambiar moneda según config
        try:
            currency = self.config.get('currency.code')
            await self._change_currency(page, currency)
        except Exception as e:
            logger.warning(f"Error al cambiar moneda: {e}")
        
        # 2. Verificar que está seleccionado el modo de venta correcto
        try:
            sell_mode = self.config.get('price_mode.sell_mode')
            logger.info(f"Verificando opción '{sell_mode}'...")
            sell_tab = page.locator(f'.tabs-item:has-text("{sell_mode}")')
            if await sell_tab.count() > 0:
                tab_class = await sell_tab.first.get_attribute('class')
                if 'active' not in tab_class:
                    await sell_tab.first.click()
                    await page.wait_for_timeout(1000)
                    logger.info(f"✅ '{sell_mode}' seleccionado")
                else:
                    logger.info(f"✅ '{sell_mode}' ya estaba seleccionado")
        except Exception as e:
            logger.warning(f"Error al configurar modo de venta: {e}")
        
        # 3. Verificar que está seleccionado el tipo de balance correcto
        try:
            balance_type = self.config.get('balance_type.type')
            logger.info(f"Verificando opción '{balance_type}'...")
            balance_tab = page.locator(f'.tabs-item:has-text("{balance_type}")')
            if await balance_tab.count() > 0:
                tab_class = await balance_tab.first.get_attribute('class')
                if 'active' not in tab_class:
                    await balance_tab.first.click()
                    await page.wait_for_timeout(1000)
                    logger.info(f"✅ '{balance_type}' seleccionado")
                else:
                    logger.info(f"✅ '{balance_type}' ya estaba seleccionado")
        except Exception as e:
            logger.warning(f"Error al configurar tipo de balance: {e}")
        
        # 4. Establecer filtros de precio y volumen según config
        try:
            min_price = self.config.get('filters.min_price')
            max_price = self.config.get('filters.max_price')
            min_volume = self.config.get('filters.min_volume')
            
            # Esperar un momento para que los elementos estén listos
            await page.wait_for_timeout(1000)
            
            # Buscar los inputs de filtros (excluyendo el de búsqueda general)
            # Los inputs de filtros están dentro de un contenedor específico
            filter_inputs = await page.locator('.el-input__inner:not(#searchInput)').all()
            
            logger.info(f"Encontrados {len(filter_inputs)} campos de filtro")
            
            # Establecer precio mínimo (generalmente el primer input de filtros)
            if min_price is not None and len(filter_inputs) >= 1:
                try:
                    logger.info(f"Estableciendo precio mínimo en {min_price}...")
                    await filter_inputs[0].fill(str(min_price), timeout=10000)
                    logger.info(f"✅ Precio mínimo establecido en {min_price}")
                except Exception as e:
                    logger.warning(f"No se pudo establecer precio mínimo: {e}")
            
            # Establecer precio máximo (si está configurado)
            if max_price is not None and len(filter_inputs) >= 2:
                try:
                    logger.info(f"Estableciendo precio máximo en {max_price}...")
                    await filter_inputs[1].fill(str(max_price), timeout=10000)
                    logger.info(f"✅ Precio máximo establecido en {max_price}")
                except Exception as e:
                    logger.warning(f"No se pudo establecer precio máximo: {e}")
            
            # Establecer volumen mínimo
            if min_volume is not None:
                # El índice del volumen depende de si hay precio máximo
                volume_idx = 2 if max_price is not None else 1
                if len(filter_inputs) > volume_idx:
                    try:
                        logger.info(f"Estableciendo volumen mínimo en {min_volume}...")
                        await filter_inputs[volume_idx].fill(str(min_volume), timeout=10000)
                        logger.info(f"✅ Volumen mínimo establecido en {min_volume}")
                    except Exception as e:
                        logger.warning(f"No se pudo establecer volumen mínimo: {e}")
            
            await page.wait_for_timeout(1000)
        except Exception as e:
            logger.warning(f"Error al configurar filtros de precio/volumen: {e}")
        
        # 5. Abrir Platform Settings y configurar plataformas
        try:
            logger.info("Abriendo Platform Settings...")
            platform_settings = page.locator('.text-blue:has-text("Platform Settings")')
            if await platform_settings.count() > 0:
                await platform_settings.first.click()
                await page.wait_for_timeout(1000)
                logger.info("✅ Platform Settings abierto")
            
            # Configurar plataformas según config
            enabled_platforms = self.config.get_enabled_platforms()
            logger.info(f"Configurando plataformas: {', '.join(enabled_platforms)}...")
            
            # Para cada plataforma conocida
            for platform, value in [('C5GAME', 'C5'), ('UU', 'YOUPIN'), ('BUFF', 'BUFF')]:
                checkbox = page.locator(f'.el-checkbox:has-text("{platform}") input[type="checkbox"]')
                if await checkbox.count() > 0:
                    is_checked = await checkbox.first.is_checked()
                    should_be_checked = self.config.get(f'platforms.{platform}', False)
                    
                    if is_checked != should_be_checked:
                        await checkbox.first.click()
                        status = "marcado" if should_be_checked else "desmarcado"
                        logger.info(f"✅ {platform} {status}")
            
            await page.wait_for_timeout(1000)
        except Exception as e:
            logger.warning(f"Error al configurar plataformas: {e}")
        
        # 6. Click en "Confirm and Search"
        try:
            logger.info("Ejecutando búsqueda...")
            confirm_btn = page.locator('.bg-\\[\\#0252D9\\]:has-text("Confirm and Search")')
            if await confirm_btn.count() > 0:
                await confirm_btn.first.click()
                logger.info("✅ Búsqueda iniciada")
                await page.wait_for_timeout(5000)
                logger.info("✅ Esperando resultados...")
        except Exception as e:
            logger.warning(f"Error al ejecutar búsqueda: {e}")
        
        logger.info("✅ Configuración de filtros completada")
    
    async def _change_currency(self, page, currency_code: str = "EUR"):
        """
        Cambia la moneda a la especificada
        
        Args:
            page: Página de Playwright
            currency_code: Código de moneda (CNY, USD, RUB, EUR)
        """
        try:
            logger.info(f"Cambiando moneda a {currency_code}...")
            
            # Símbolos de moneda
            currency_symbols = {
                "CNY": "¥",
                "USD": "$",
                "RUB": "₽",
                "EUR": "€"
            }
            
            # Buscar el selector de moneda (puede tener cualquier moneda)
            currency_selector = page.locator('.el-dropdown-link').first
            
            if await currency_selector.count() > 0:
                # Click en el dropdown de moneda
                await currency_selector.click()
                await page.wait_for_timeout(1000)
                
                # Buscar y hacer click en la moneda deseada
                symbol = currency_symbols.get(currency_code, "")
                currency_option = page.locator(f'li:has-text("{currency_code}")')
                
                if await currency_option.count() > 0:
                    await currency_option.first.click()
                    logger.info(f"✅ Moneda cambiada a {currency_code}")
                    await page.wait_for_timeout(3000)  # Esperar a que recargue los precios
                else:
                    logger.warning(f"No se encontró opción {currency_code} en el menú")
                    # Cerrar el dropdown
                    await page.keyboard.press('Escape')
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
            
            # Obtener configuración de output
            output_dir = self.config.get('output.output_directory', 'data')
            save_screenshot = self.config.get('output.save_screenshot', True)
            save_html = self.config.get('output.save_html', True)
            save_debug = self.config.get('debug.save_debug_info', True)
            
            # Guardar screenshot para depuración (si está habilitado)
            if save_screenshot and save_debug:
                screenshot_path = f"{output_dir}/debug_screenshot.png"
                await page.screenshot(path=screenshot_path)
                logger.info(f"Screenshot guardado en {screenshot_path}")
            
            # Obtener el HTML para análisis
            content = await page.content()
            
            # Guardar HTML para análisis (si está habilitado)
            if save_html and save_debug:
                html_path = f"{output_dir}/page_content.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"HTML de la página guardado en {html_path}")
            
            # Intentar extraer datos de múltiples posibles estructuras
            # Probar diferentes selectores comunes, priorizando Element UI
            selectors = [
                '.el-table__row',  # Element UI - específico para la tabla
                'table tbody tr.el-table__row',  # Más específico
                'table tbody tr',  # Genérico (fallback)
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
            
            # Contador de items válidos procesados
            valid_item_count = 0
            
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

                    # Incrementar contador de items válidos
                    valid_item_count += 1
                    
                    item = {
                        'id': valid_item_count,  # Usar contador de items válidos, no índice de fila
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
        # Obtener configuración de output
        output_dir = self.config.get('output.output_directory', 'data')
        indent = self.config.get('output.json_indent', 2)
        
        # Crear directorio si no existe
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Asegurar que la ruta incluye el directorio
        if not filename.startswith(output_dir):
            filename = os.path.join(output_dir, os.path.basename(filename))
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=indent)
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
