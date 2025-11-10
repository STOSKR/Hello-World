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
        self.screenshot_counter = 0
        
    async def _save_screenshot(self, page: Page, step_name: str):
        """Guarda una captura de pantalla del paso actual"""
        try:
            import os
            # Asegurar que el directorio existe
            os.makedirs("data/screenshots", exist_ok=True)
            
            self.screenshot_counter += 1
            # Limpiar el nombre del archivo (sin caracteres especiales)
            clean_name = re.sub(r'[<>:"/\\|?*]', '_', step_name)
            filename = f"data/screenshots/step_{self.screenshot_counter:03d}_{clean_name}.png"
            await page.screenshot(path=filename, full_page=False)
            logger.info(f"   📸 Screenshot guardado: {filename}")
        except Exception as e:
            logger.warning(f"   ⚠️ Error guardando screenshot: {e}")
        
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
            await self._save_screenshot(page, f"steamdt_{item_name[:30]}")
            
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
            
            await self._save_screenshot(page, f"buff_{item_name[:30]}")
            
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
            
            await self._save_screenshot(page, f"steam_{item_name[:30]}")
            
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
            
            # Intentar múltiples selectores
            clicked = False
            
            # Selector 1: Por tab_id
            try:
                trade_tab = page.locator('li[tab_id="8"] a').first
                if await trade_tab.count() > 0:
                    await trade_tab.click()
                    clicked = True
                    logger.info(f"      🔄 Pestaña Trade Records activada (tab_id=8)")
            except:
                pass
            
            # Selector 2: Por texto "Trade Records"
            if not clicked:
                try:
                    trade_tab = page.locator('li.history a:has-text("Trade Records")').first
                    if await trade_tab.count() > 0:
                        await trade_tab.click()
                        clicked = True
                        logger.info(f"      🔄 Pestaña Trade Records activada (texto)")
                except:
                    pass
            
            if not clicked:
                logger.warning("      No se pudo hacer clic en Trade Records")
                return []
            
            # Esperar más tiempo a que carguen los datos
            logger.info(f"      ⏳ Esperando carga de trade records...")
            await page.wait_for_timeout(5000)
            
            # Buscar específicamente la tabla dentro del contenido del tab activo
            # El tab activo tiene la clase 'active' en BUFF
            logger.info(f"      🔍 Buscando tabla de trade records...")
            try:
                # Esperar a que aparezca la tabla dentro del contenedor activo
                # Usar un selector más específico que apunte a la tabla visible
                await page.wait_for_selector('.detail-tab-cont.on table tbody tr', timeout=10000)
                logger.info(f"      ✅ Tabla encontrada en tab activo")
            except Exception as e:
                # Intentar selector alternativo
                try:
                    await page.wait_for_selector('#j_list_card table tbody tr', timeout=5000)
                    logger.info(f"      ✅ Tabla encontrada (selector alternativo)")
                except Exception as e2:
                    logger.warning(f"      ⚠️ No se encontró tabla de trade records")
                    logger.debug(f"      Error 1: {e}")
                    logger.debug(f"      Error 2: {e2}")
                    return []
            
            # Obtener filas de la tabla visible (dentro del tab activo)
            all_rows = await page.locator('.detail-tab-cont.on table tbody tr').all()
            
            # Si no hay filas, intentar selector alternativo
            if len(all_rows) == 0:
                all_rows = await page.locator('#j_list_card table tbody tr').all()
            
            logger.info(f"      📊 Encontradas {len(all_rows)} filas totales")
            
            # Filtrar solo filas con datos (que tengan imagen de item)
            data_rows = []
            for row in all_rows:
                img_count = await row.locator('img').count()
                if img_count > 0:
                    data_rows.append(row)
            
            logger.info(f"      📊 Encontradas {len(data_rows)} filas de ventas")
            
            # Procesar las primeras 5 filas con datos
            records_to_process = data_rows[:5]
            
            for idx, row in enumerate(records_to_process):
                try:
                    # Extraer precio de venta en CNY
                    # En trade records la estructura puede ser diferente
                    price_cny = None
                    price_eur = None
                    
                    # Método 1: Intentar con strong.f_Strong (como selling)
                    try:
                        price_strong_elem = row.locator('strong.f_Strong').first
                        if await price_strong_elem.count() > 0:
                            price_full = await price_strong_elem.inner_text(timeout=3000)
                            # "¥ 38.88" o "¥ 38<small>.88</small>" -> extraer solo números
                            price_match = re.search(r'([\d.]+)', price_full)
                            if price_match:
                                price_cny = price_match.group(1)
                    except:
                        pass
                    
                    # Método 2: Buscar cualquier texto con ¥ en la fila
                    if not price_cny:
                        try:
                            row_text = await row.inner_text()
                            # Buscar patrón ¥ XX.XX (solo un punto decimal)
                            price_match = re.search(r'¥\s*([\d]+\.[\d]+)', row_text)
                            if price_match:
                                price_cny = price_match.group(1)
                        except:
                            pass
                    
                    # Extraer precio en EUR si está disponible
                    try:
                        eur_element = row.locator('span.c_Gray.f_12px, span:has-text("€")').first
                        if await eur_element.count() > 0:
                            eur_text = await eur_element.inner_text()
                            eur_match = re.search(r'€\s*([\d.]+)', eur_text)
                            if eur_match:
                                price_eur = eur_match.group(1)
                    except:
                        pass
                    
                    # Extraer fecha
                    date_text = None
                    try:
                        date_element = row.locator('[class*="time"], [class*="date"], td:last-child').first
                        date_text = await date_element.inner_text()
                        # Limpiar si contiene precio
                        if '¥' in date_text or '€' in date_text:
                            date_text = None
                    except:
                        pass
                    
                    if price_cny:
                        trade_records.append({
                            'position': idx + 1,
                            'price_cny': price_cny,
                            'price_eur': price_eur,
                            'date': date_text
                        })
                        logger.info(f"      📊 Record {idx+1}: ¥{price_cny} (€{price_eur or 'N/A'})")
                    else:
                        logger.warning(f"      ⚠️ No se pudo extraer precio de la fila {idx+1}")
                    
                except Exception as e:
                    logger.warning(f"Error extrayendo trade record {idx+1}: {e}")
                    continue
            
            logger.info(f"      ✅ Extraídos {len(trade_records)} trade records")
            
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
            # Los trade records están en la misma tabla que selling items
            # Así que también tienen price_cny
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
        Omite items que muestren "已售出" (vendido)
        """
        selling_items = []
        
        try:
            # Esperar a que cargue la lista de ventas
            await page.wait_for_selector('.market_listing_row', timeout=10000)
            
            # Obtener todas las filas disponibles
            all_rows = await page.locator('.market_listing_row').all()
            
            logger.info(f"      📋 Encontradas {len(all_rows)} filas en Steam")
            
            # Procesar filas hasta encontrar 5 válidas
            for idx, row in enumerate(all_rows):
                if len(selling_items) >= 5:
                    break  # Ya tenemos 5 items válidos
                
                try:
                    # Verificar si el item está vendido
                    row_text = await row.inner_text()
                    
                    if '已售出' in row_text or 'Sold!' in row_text:
                        logger.debug(f"      ⏭️ Fila {idx+1}: Item vendido, omitiendo")
                        continue
                    
                    # Extraer precio
                    price_element = row.locator('.market_listing_price.market_listing_price_with_fee').first
                    
                    if await price_element.count() == 0:
                        logger.debug(f"      ⏭️ Fila {idx+1}: Sin precio, omitiendo")
                        continue
                    
                    price_text = await price_element.inner_text()
                    
                    # Limpiar precio: "¥ 18.48" -> "18.48"
                    price_clean = re.sub(r'[¥€$\s]', '', price_text).strip()
                    
                    if not price_clean or price_clean == '':
                        logger.debug(f"      ⏭️ Fila {idx+1}: Precio vacío, omitiendo")
                        continue
                    
                    selling_items.append({
                        'position': len(selling_items) + 1,
                        'price': price_text.strip(),
                        'price_raw': price_clean
                    })
                    
                    logger.debug(f"      ✅ Item {len(selling_items)}: {price_text.strip()}")
                    
                except Exception as e:
                    logger.debug(f"      ⏭️ Error en fila {idx}: {e}, omitiendo")
                    continue
            
            logger.info(f"      ✅ Extraídos {len(selling_items)} items válidos de Steam")
            
        except PlaywrightTimeout:
            logger.warning("      ⏱️ Timeout esperando items en Steam")
        except Exception as e:
            logger.error(f"      ❌ Error extrayendo selling items de Steam: {e}")
        
        return selling_items
