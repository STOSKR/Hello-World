"""
Extractor detallado de items
Navega a cada item individualmente y extrae datos de BUFF y Steam
"""

import logging
import re
from datetime import datetime
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class DetailedItemExtractor:
    """Extrae datos detallados navegando a cada item individual"""
    
    def __init__(self):
        """Inicializa el extractor detallado"""
        self.BUFF_TIMEOUT = 30000  # 30 segundos
        self.STEAM_TIMEOUT = 30000  # 30 segundos
        
    async def extract_detailed_item(self, page: Page, item_url: str, item_name: str) -> Optional[Dict]:
        """
        Extrae datos detallados de un item navegando a su página
        
        Args:
            page: Página de Playwright
            item_url: URL del item en steamdt.com
            item_name: Nombre del item
            
        Returns:
            Diccionario con datos detallados o None si el item debe descartarse
        """
        logger.info(f"📍 Procesando item: {item_name}")
        logger.info(f"   URL: {item_url}")
        
        try:
            # 1. Navegar a la página del item en steamdt.com
            await page.goto(item_url, wait_until='networkidle', timeout=self.BUFF_TIMEOUT)
            await page.wait_for_timeout(3000)
            
            # 2. Extraer URL de BUFF
            buff_url = await self._extract_buff_url(page)
            if not buff_url:
                logger.warning(f"⚠️ No se encontró URL de BUFF para {item_name}")
                return None
            
            logger.info(f"   🔗 BUFF URL: {buff_url}")
            
            # 3. Navegar a BUFF y extraer datos
            buff_data = await self._extract_buff_data(page, buff_url, item_name)
            if not buff_data:
                logger.info(f"   ❌ Item descartado por validación de BUFF")
                return None
            
            # 4. Volver a steamdt.com y extraer URL de Steam
            await page.goto(item_url, wait_until='networkidle', timeout=self.BUFF_TIMEOUT)
            await page.wait_for_timeout(2000)
            
            steam_url = await self._extract_steam_url(page)
            if not steam_url:
                logger.warning(f"⚠️ No se encontró URL de Steam para {item_name}")
                return None
            
            logger.info(f"   🔗 Steam URL: {steam_url}")
            
            # 5. Navegar a Steam y extraer datos
            steam_data = await self._extract_steam_data(page, steam_url, item_name)
            
            # 6. Calcular promedios y rentabilidad
            analysis = self._calculate_profitability(buff_data, steam_data)
            
            if not analysis:
                logger.warning(f"   ⚠️ No se pudo calcular rentabilidad")
                return None
            
            # 7. Combinar todos los datos (sin datos innecesarios de steamdt)
            detailed_data = {
                'item_name': item_name,
                'buff_url': buff_url,
                'steam_url': steam_url,
                'buff_avg_price_cny': analysis['buff_avg_price_cny'],
                'buff_avg_price_eur': analysis['buff_avg_price_eur'],
                'steam_avg_price_cny': analysis['steam_avg_price_cny'],
                'steam_avg_price_eur': analysis['steam_avg_price_eur'],
                'profitability_ratio': analysis['profitability_ratio'],
                'profit_eur': analysis['profit_eur'],
                'buff_selling_items': buff_data['selling_items'],
                'buff_trade_records': buff_data['trade_records'],
                'steam_selling_items': steam_data['selling_items'],
                'extracted_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"   💰 Rentabilidad: {analysis['profitability_ratio']:.2%} | Profit: €{analysis['profit_eur']:.2f}")
            logger.info(f"   ✅ Item procesado exitosamente")
            return detailed_data
            
        except Exception as e:
            logger.error(f"❌ Error procesando {item_name}: {e}")
            return None
    
    def _calculate_profitability(self, buff_data: Dict, steam_data: Dict) -> Optional[Dict]:
        """
        Calcula la rentabilidad comparando precios de BUFF y Steam
        
        Args:
            buff_data: Datos extraídos de BUFF
            steam_data: Datos extraídos de Steam
            
        Returns:
            Diccionario con análisis de rentabilidad
        """
        CNY_TO_EUR = 8.2  # Tasa de conversión CNY a EUR
        
        try:
            # Calcular precio promedio de BUFF en CNY
            buff_prices_cny = [
                float(item['price_cny']) 
                for item in buff_data.get('selling_items', []) 
                if item.get('price_cny')
            ]
            
            if not buff_prices_cny:
                logger.warning("   ⚠️ No hay precios válidos en BUFF")
                return None
            
            buff_avg_cny = sum(buff_prices_cny) / len(buff_prices_cny)
            buff_avg_eur = buff_avg_cny / CNY_TO_EUR
            
            # Calcular precio promedio de Steam en CNY (después de fee 0.87)
            steam_prices_raw = [
                float(item['price_raw']) 
                for item in steam_data.get('selling_items', []) 
                if item.get('price_raw')
            ]
            
            if not steam_prices_raw:
                logger.warning("   ⚠️ No hay precios válidos en Steam")
                return None
            
            # Precio promedio en Steam (antes de fee)
            steam_avg_cny_before_fee = sum(steam_prices_raw) / len(steam_prices_raw)
            
            # Aplicar fee de Steam (0.87 = vendedor recibe 87%)
            steam_avg_cny = steam_avg_cny_before_fee * 0.87
            steam_avg_eur = steam_avg_cny / CNY_TO_EUR
            
            # Calcular rentabilidad
            # Rentabilidad = (Precio venta Steam - Precio compra BUFF) / Precio compra BUFF
            profitability_ratio = (steam_avg_eur - buff_avg_eur) / buff_avg_eur if buff_avg_eur > 0 else 0
            profit_eur = steam_avg_eur - buff_avg_eur
            
            return {
                'buff_avg_price_cny': round(buff_avg_cny, 2),
                'buff_avg_price_eur': round(buff_avg_eur, 2),
                'steam_avg_price_cny': round(steam_avg_cny, 2),
                'steam_avg_price_eur': round(steam_avg_eur, 2),
                'profitability_ratio': profitability_ratio,
                'profit_eur': round(profit_eur, 2)
            }
            
        except Exception as e:
            logger.error(f"   ❌ Error calculando rentabilidad: {e}")
            return None
    
    async def _extract_buff_url(self, page: Page) -> Optional[str]:
        """
        Extrae la URL de BUFF desde la página del item en steamdt.com
        
        Busca: <a data-v-47aa98be="" href="https://buff.163.com/goods/35491?from=market#tab=selling" ...>
        """
        try:
            # Buscar el enlace de BUFF
            buff_link = page.locator('a[href*="buff.163.com"]').first
            buff_url = await buff_link.get_attribute('href')
            return buff_url
        except Exception as e:
            logger.debug(f"Error extrayendo URL de BUFF: {e}")
            return None
    
    async def _extract_steam_url(self, page: Page) -> Optional[str]:
        """
        Extrae la URL de Steam desde la página del item en steamdt.com
        
        Busca: <a data-v-47aa98be="" href="https://steamcommunity.com/market/listings/730/..." ...>
        """
        try:
            # Buscar el enlace de Steam
            steam_link = page.locator('a[href*="steamcommunity.com/market/listings"]').first
            steam_url = await steam_link.get_attribute('href')
            return steam_url
        except Exception as e:
            logger.debug(f"Error extrayendo URL de Steam: {e}")
            return None
    
    async def _extract_buff_data(self, page: Page, buff_url: str, item_name: str) -> Optional[Dict]:
        """
        Navega a BUFF y extrae:
        - Top 5 items en venta (más baratos)
        - Top 5 ventas recientes (trade records)
        - Valida que las ventas recientes no sean 10% mayores
        
        Returns:
            Dict con datos de BUFF o None si el item debe descartarse
        """
        try:
            logger.info(f"   🌐 Navegando a BUFF...")
            await page.goto(buff_url, wait_until='domcontentloaded', timeout=self.BUFF_TIMEOUT)
            await page.wait_for_timeout(5000)  # Esperar a que cargue el contenido dinámico
            
            # Extraer los 5 items más baratos en venta
            selling_items = await self._extract_buff_selling_items(page)
            
            if not selling_items:
                logger.warning(f"   ⚠️ No se encontraron items en venta en BUFF")
                return None
            
            logger.info(f"   📊 Encontrados {len(selling_items)} items en venta")
            
            # Navegar a Trade Records
            logger.info(f"   📈 Accediendo a Trade Records...")
            trade_records = await self._extract_buff_trade_records(page)
            
            if not trade_records:
                logger.warning(f"   ⚠️ No se encontraron trade records")
                # Continuar sin trade records
                trade_records = []
            else:
                logger.info(f"   📊 Encontrados {len(trade_records)} trade records")
            
            # Validar: Si las últimas 5 ventas son 10% mayores que los precios actuales, descartar
            should_discard = self._validate_price_difference(selling_items, trade_records)
            
            if should_discard:
                logger.info(f"   ❌ Item descartado: ventas recientes 10% mayores que precios actuales")
                return None
            
            return {
                'selling_items': selling_items,
                'trade_records': trade_records
            }
            
        except PlaywrightTimeout:
            logger.error(f"   ⏱️ Timeout navegando a BUFF")
            return None
        except Exception as e:
            logger.error(f"   ❌ Error extrayendo datos de BUFF: {e}")
            return None
    
    async def _extract_buff_selling_items(self, page: Page) -> List[Dict]:
        """
        Extrae los primeros 5 items en venta de BUFF
        
        Busca elementos <tr> con clase "selling"
        """
        selling_items = []
        
        try:
            # Esperar a que la tabla cargue
            await page.wait_for_selector('tr.selling', timeout=10000)
            
            # Obtener las primeras 5 filas
            rows = await page.locator('tr.selling').all()
            rows_to_process = rows[:5]  # Solo los primeros 5
            
            for idx, row in enumerate(rows_to_process):
                try:
                    # Extraer precio (buscar el precio en CNY con símbolo ¥)
                    price_element = row.locator('strong.f_Strong')
                    price_text = await price_element.inner_text()
                    
                    # Limpiar precio: "¥ 10.8" -> "10.8"
                    price_clean = re.sub(r'[¥\s]', '', price_text).strip()
                    
                    # Extraer precio en EUR (si está disponible)
                    eur_price = None
                    try:
                        eur_element = row.locator('span.c_Gray.f_12px')
                        eur_text = await eur_element.inner_text()
                        # "(€ 1.31)" -> "1.31"
                        eur_match = re.search(r'€\s*([\d.]+)', eur_text)
                        if eur_match:
                            eur_price = eur_match.group(1)
                    except:
                        pass
                    
                    # Extraer desgaste (wear/paintwear)
                    wear = None
                    try:
                        wear_element = row.locator('div.wear-value')
                        wear_text = await wear_element.inner_text()
                        # "Desgaste: 0.11015310883522034" -> "0.11015310883522034"
                        wear_match = re.search(r'([\d.]+)', wear_text)
                        if wear_match:
                            wear = wear_match.group(1)
                    except:
                        pass
                    
                    # Extraer vendedor
                    seller = None
                    try:
                        seller_element = row.locator('span.user-name')
                        seller = await seller_element.inner_text()
                    except:
                        pass
                    
                    selling_items.append({
                        'position': idx + 1,
                        'price_cny': price_clean,
                        'price_eur': eur_price,
                        'wear': wear,
                        'seller': seller
                    })
                    
                except Exception as e:
                    logger.debug(f"Error extrayendo item en venta {idx}: {e}")
                    continue
            
        except PlaywrightTimeout:
            logger.warning("Timeout esperando items en venta en BUFF")
        except Exception as e:
            logger.error(f"Error extrayendo selling items: {e}")
        
        return selling_items
    
    async def _extract_buff_trade_records(self, page: Page) -> List[Dict]:
        """
        Extrae las últimas 5 ventas de Trade Records en BUFF
        
        Primero hace clic en la pestaña "Trade Records"
        """
        trade_records = []
        
        try:
            # Buscar y hacer clic en la pestaña de Trade Records
            # <li class="history on" tab_id="8"><a href="javascript:;">Trade Records<i class="icon icon_top_cur"></i></a></li>
            trade_tab = page.locator('li.history a:has-text("Trade Records")').first
            
            # Verificar si existe
            if await trade_tab.count() == 0:
                # Intentar con selector alternativo
                trade_tab = page.locator('a:has-text("Trade Records")').first
            
            await trade_tab.click()
            logger.info(f"      🔄 Pestaña Trade Records activada")
            await page.wait_for_timeout(3000)  # Esperar a que carguen los datos
            
            # Buscar la tabla de trade records
            # Puede estar en una tabla o lista
            # Intentar múltiples selectores
            record_rows = []
            
            # Selector 1: Tabla con clase específica
            try:
                await page.wait_for_selector('table tbody tr', timeout=5000)
                record_rows = await page.locator('table tbody tr').all()
            except:
                # Selector 2: Cualquier elemento de lista
                try:
                    record_rows = await page.locator('ul.trade-list li').all()
                except:
                    logger.warning("No se pudo encontrar trade records")
                    return []
            
            # Procesar las primeras 5
            records_to_process = record_rows[:5]
            
            for idx, row in enumerate(records_to_process):
                try:
                    # Extraer precio de venta
                    price_text = await row.locator('[class*="price"]').first.inner_text()
                    price_clean = re.sub(r'[¥\s]', '', price_text).strip()
                    
                    # Extraer fecha
                    date_text = None
                    try:
                        date_element = row.locator('[class*="time"], [class*="date"]').first
                        date_text = await date_element.inner_text()
                    except:
                        pass
                    
                    trade_records.append({
                        'position': idx + 1,
                        'price_cny': price_clean,
                        'date': date_text
                    })
                    
                except Exception as e:
                    logger.debug(f"Error extrayendo trade record {idx}: {e}")
                    continue
            
        except Exception as e:
            logger.warning(f"Error extrayendo trade records: {e}")
        
        return trade_records
    
    def _validate_price_difference(self, selling_items: List[Dict], trade_records: List[Dict]) -> bool:
        """
        Valida si las ventas recientes son 10% mayores que los precios actuales
        
        Returns:
            True si debe descartarse el item, False si es válido
        """
        if not selling_items or not trade_records:
            return False  # No descartar si no hay datos
        
        try:
            # Calcular precio promedio de venta actual (CNY)
            selling_prices = [float(item['price_cny']) for item in selling_items if item.get('price_cny')]
            if not selling_prices:
                return False
            
            avg_selling_price = sum(selling_prices) / len(selling_prices)
            
            # Calcular precio promedio de ventas recientes (CNY)
            trade_prices = [float(record['price_cny']) for record in trade_records if record.get('price_cny')]
            if not trade_prices:
                return False
            
            avg_trade_price = sum(trade_prices) / len(trade_prices)
            
            # Calcular diferencia porcentual
            # Si las ventas recientes son 10% o más mayores, descartar
            if avg_trade_price >= avg_selling_price * 1.10:
                logger.info(f"      📉 Precio venta reciente ({avg_trade_price:.2f}) es 10%+ mayor que actual ({avg_selling_price:.2f})")
                return True
            
            logger.info(f"      ✅ Validación de precios OK: Venta actual {avg_selling_price:.2f}, Reciente {avg_trade_price:.2f}")
            return False
            
        except Exception as e:
            logger.warning(f"Error validando precios: {e}")
            return False  # En caso de error, no descartar
    
    async def _extract_steam_data(self, page: Page, steam_url: str, item_name: str) -> Optional[Dict]:
        """
        Navega a Steam y extrae:
        - Gráfica de ventas semanal (si es posible)
        - Primeros items en venta
        - Precio multiplicado por 0.87
        """
        try:
            logger.info(f"   🌐 Navegando a Steam...")
            await page.goto(steam_url, wait_until='domcontentloaded', timeout=self.STEAM_TIMEOUT)
            await page.wait_for_timeout(5000)
            
            # Extraer primeros items en venta
            selling_items = await self._extract_steam_selling_items(page)
            
            if not selling_items:
                logger.warning(f"   ⚠️ No se encontraron items en venta en Steam")
                return None
            
            logger.info(f"   📊 Encontrados {len(selling_items)} items en venta en Steam")
            
            return {
                'selling_items': selling_items
            }
            
        except PlaywrightTimeout:
            logger.error(f"   ⏱️ Timeout navegando a Steam")
            return None
        except Exception as e:
            logger.error(f"   ❌ Error extrayendo datos de Steam: {e}")
            return None
    
    async def _extract_steam_selling_items(self, page: Page) -> List[Dict]:
        """
        Extrae los primeros items en venta de Steam
        
        Busca: <span class="market_listing_price market_listing_price_with_fee">¥ 18.48</span>
        """
        selling_items = []
        
        try:
            # Esperar a que cargue la lista de ventas
            await page.wait_for_selector('.market_listing_row', timeout=10000)
            
            # Obtener las primeras filas (máximo 5)
            rows = await page.locator('.market_listing_row').all()
            rows_to_process = rows[:5]
            
            for idx, row in enumerate(rows_to_process):
                try:
                    # Extraer precio
                    price_element = row.locator('.market_listing_price.market_listing_price_with_fee').first
                    price_text = await price_element.inner_text()
                    
                    # Limpiar precio: "¥ 18.48" -> "18.48"
                    price_clean = re.sub(r'[¥€$\s]', '', price_text).strip()
                    
                    selling_items.append({
                        'position': idx + 1,
                        'price': price_text.strip(),
                        'price_raw': price_clean
                    })
                    
                except Exception as e:
                    logger.debug(f"Error extrayendo item de Steam {idx}: {e}")
                    continue
            
        except PlaywrightTimeout:
            logger.warning("Timeout esperando items en Steam")
        except Exception as e:
            logger.error(f"Error extrayendo selling items de Steam: {e}")
        
        return selling_items
