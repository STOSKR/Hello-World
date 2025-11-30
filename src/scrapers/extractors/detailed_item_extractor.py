"""
Extractor detallado de items
Navega a cada item individualmente y extrae datos de BUFF y Steam
"""

import re
from datetime import datetime
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from typing import List, Dict, Optional, Tuple
from utils.logger_config import setup_logger

logger = setup_logger(name="cs_tracker.detailed_item_extractor")


class DetailedItemExtractor:
    """Extrae datos detallados navegando a cada item individual"""

    def __init__(self):
        self.BUFF_TIMEOUT = 10000  # 3 segundos
        self.STEAM_TIMEOUT = 10000  # 3 segundos
        self.screenshot_counter = 0

    async def _save_screenshot(self, page: Page, step_name: str):
        try:
            import os

            # Asegurar que el directorio existe
            os.makedirs("data/screenshots", exist_ok=True)

            self.screenshot_counter += 1
            # Limpiar el nombre del archivo (sin caracteres especiales)
            clean_name = re.sub(r'[<>:"/\\|?*]', "_", step_name)
            filename = (
                f"data/screenshots/step_{self.screenshot_counter:03d}_{clean_name}.png"
            )
            await page.screenshot(path=filename, full_page=False)
            logger.info(f"   📸 Screenshot guardado: {filename}")
        except Exception as e:
            logger.warning(f"   ⚠️ Error guardando screenshot: {e}")

    async def extract_detailed_item(
        self,
        page: Page,
        item_url: str,
        item_name: str,
        buff_url: str = None,
        steam_url: str = None,
    ) -> Optional[Dict]:
        logger.info(f"Procesando item: {item_name}")
        logger.info(f"   URL: {item_url}")

        try:
            # Si no se proporcionaron las URLs, extraerlas de steamdt.com
            if not buff_url or not steam_url:
                logger.info(f"   Extrayendo URLs desde steamdt.com...")
                await page.goto(
                    item_url, wait_until="networkidle", timeout=self.BUFF_TIMEOUT
                )
                await page.wait_for_timeout(3000)
                await self._save_screenshot(page, f"steamdt_{item_name[:30]}")

                if not buff_url:
                    buff_url = await self._extract_buff_url(page)
                    if not buff_url:
                        logger.warning(f"No se encontró URL de BUFF para {item_name}")
                        return None

                if not steam_url:
                    steam_url = await self._extract_steam_url(page)
                    if not steam_url:
                        logger.warning(f"No se encontró URL de Steam para {item_name}")
                        return None

            logger.info(f"   BUFF URL: {buff_url}")
            logger.info(f"   Steam URL: {steam_url}")

            # Navegar a BUFF y extraer datos
            buff_data = await self._extract_buff_data(page, buff_url, item_name)
            if not buff_data:
                logger.info(f"   Item descartado por validación de BUFF")
                return None

            await self._save_screenshot(page, f"buff_{item_name[:30]}")

            # Navegar a Steam y extraer datos
            logger.info(f"   Navegando a Steam...")
            steam_data = await self._extract_steam_data(page, steam_url, item_name)

            if not steam_data:
                logger.warning(f"   No se pudieron extraer datos de Steam")
                return None

            logger.info(f"   Datos de Steam extraídos")
            await self._save_screenshot(page, f"steam_{item_name[:30]}")

            # 6. Calcular promedios y rentabilidad
            analysis = self._calculate_profitability(buff_data, steam_data)

            if not analysis:
                logger.warning(f"   ⚠️ No se pudo calcular rentabilidad")
                return None

            # 7. Combinar todos los datos (sin datos innecesarios de steamdt)
            detailed_data = {
                "item_name": item_name,
                "buff_url": buff_url,
                "steam_url": steam_url,
                "buff_avg_price_cny": analysis["buff_avg_price_cny"],
                "buff_avg_price_eur": analysis["buff_avg_price_eur"],
                "steam_avg_price_cny": analysis["steam_avg_price_cny"],
                "steam_avg_price_eur": analysis["steam_avg_price_eur"],
                "profitability_ratio": analysis["profitability_ratio"],
                "profit_eur": analysis["profit_eur"],
                "buff_selling_items": buff_data["selling_items"],
                "buff_trade_records": buff_data["trade_records"],
                "steam_selling_items": steam_data["selling_items"],
                "extracted_at": datetime.utcnow().isoformat(),
            }

            logger.info(
                f"   Rentabilidad: {analysis['profitability_ratio']:.2%} | Profit: €{analysis['profit_eur']:.2f}"
            )
            logger.info(f"   Item procesado exitosamente")
            return detailed_data

        except Exception as e:
            logger.error(f"Error procesando {item_name}: {e}")
            return None

    def _calculate_profitability(
        self, buff_data: Dict, steam_data: Dict
    ) -> Optional[Dict]:
        CNY_TO_EUR = 8.2  # Tasa de conversión CNY a EUR

        try:
            # Calcular precio promedio de BUFF en CNY
            buff_prices_cny = [
                float(item["price_cny"])
                for item in buff_data.get("selling_items", [])
                if item.get("price_cny")
            ]

            if not buff_prices_cny:
                logger.warning("   ⚠️ No hay precios válidos en BUFF")
                return None

            buff_avg_cny = sum(buff_prices_cny) / len(buff_prices_cny)
            buff_avg_eur = buff_avg_cny / CNY_TO_EUR

            # Calcular precio promedio de Steam en CNY (después de fee 0.87)
            steam_prices_raw = [
                float(item["price_raw"])
                for item in steam_data.get("selling_items", [])
                if item.get("price_raw")
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
            profitability_ratio = (
                (steam_avg_eur - buff_avg_eur) / buff_avg_eur if buff_avg_eur > 0 else 0
            )
            profit_eur = steam_avg_eur - buff_avg_eur

            return {
                "buff_avg_price_cny": round(buff_avg_cny, 2),
                "buff_avg_price_eur": round(buff_avg_eur, 2),
                "steam_avg_price_cny": round(steam_avg_cny, 2),
                "steam_avg_price_eur": round(steam_avg_eur, 2),
                "profitability_ratio": profitability_ratio,
                "profit_eur": round(profit_eur, 2),
            }

        except Exception as e:
            logger.error(f"   ❌ Error calculando rentabilidad: {e}")
            return None

    async def _extract_buff_url(self, page: Page) -> Optional[str]:
        try:
            # Buscar el enlace de BUFF
            buff_link = page.locator('a[href*="buff.163.com"]').first
            buff_url = await buff_link.get_attribute("href")
            return buff_url
        except Exception as e:
            logger.debug(f"Error extrayendo URL de BUFF: {e}")
            return None

    async def _extract_steam_url(self, page: Page) -> Optional[str]:
        try:
            # Buscar el enlace de Steam
            steam_link = page.locator(
                'a[href*="steamcommunity.com/market/listings"]'
            ).first
            steam_url = await steam_link.get_attribute("href")
            return steam_url
        except Exception as e:
            logger.debug(f"Error extrayendo URL de Steam: {e}")
            return None

    async def _extract_buff_data(
        self, page: Page, buff_url: str, item_name: str
    ) -> Optional[Dict]:
        try:
            # 1. Navegar a BUFF tab=selling (items en venta)
            logger.info(f"   Navegando a BUFF (Selling)...")
            # Asegurar que la URL tenga el formato correcto
            base_url = buff_url.split("#")[0].split("?")[
                0
            ]  # Limpiar fragmentos y query params
            selling_url = f"{base_url}?from=market#tab=selling"

            try:
                await page.goto(
                    selling_url, wait_until="domcontentloaded", timeout=30000
                )  # 30s timeout
                await page.wait_for_timeout(
                    5000
                )  # Esperar a que cargue el contenido dinámico
            except PlaywrightTimeout:
                logger.error(f"   ⏱️ Timeout navegando a BUFF selling")
                return None

            # Extraer los 5 items más baratos en venta
            selling_items = await self._extract_buff_selling_items(page)

            if not selling_items:
                logger.warning(f"   ⚠️ No se encontraron items en venta en BUFF")
                return None

            logger.info(f"   📊 Encontrados {len(selling_items)} items en venta")

            # 2. Navegar a BUFF tab=history (trade records)
            logger.info(f"   📈 Navegando a Trade Records...")
            history_url = f"{base_url}?from=market#tab=history"

            logger.info(f"   🔗 URL Trade Records: {history_url}")
            try:
                await page.goto(
                    history_url, wait_until="domcontentloaded", timeout=30000
                )  # 30s timeout
                await page.wait_for_timeout(5000)  # Esperar a que cargue
            except PlaywrightTimeout:
                logger.warning(
                    f"   ⏱️ Timeout navegando a Trade Records, continuando sin ellos"
                )
                trade_records = []
                return {"selling_items": selling_items, "trade_records": trade_records}

            trade_records = await self._extract_buff_trade_records(page)

            if not trade_records:
                logger.warning(f"   ⚠️ No se encontraron trade records")
                # Continuar sin trade records
                trade_records = []
            else:
                logger.info(f"   📊 Encontrados {len(trade_records)} trade records")

            # Validar: Si las últimas 5 ventas son 10% mayores que los precios actuales, descartar
            should_discard = self._validate_price_difference(
                selling_items, trade_records
            )

            if should_discard:
                logger.info(
                    f"   ❌ Item descartado: ventas recientes 10% mayores que precios actuales"
                )
                return None

            return {"selling_items": selling_items, "trade_records": trade_records}

        except PlaywrightTimeout:
            logger.error(f"   ⏱️ Timeout navegando a BUFF")
            return None
        except Exception as e:
            logger.error(f"   ❌ Error extrayendo datos de BUFF: {e}")
            return None

    async def _extract_buff_selling_items(self, page: Page) -> List[Dict]:
        selling_items = []

        try:
            # Esperar a que la tabla cargue con timeout
            logger.info(f"   🔍 Esperando tabla de items en venta...")
            try:
                await page.wait_for_selector("tr.selling", timeout=15000)
            except Exception as e:
                logger.warning(
                    f"   ⚠️ No se encontró tabla con selector 'tr.selling': {e}"
                )
                # Intentar selector alternativo para pins/stickers
                try:
                    await page.wait_for_selector("table tbody tr", timeout=10000)
                    logger.info(f"   ✅ Usando selector genérico de tabla")
                except Exception as e2:
                    logger.error(f"   ❌ No se pudo encontrar ninguna tabla: {e2}")
                    return []

            # Obtener las primeras 5 filas
            rows = await page.locator("tr.selling").all()

            if len(rows) == 0:
                logger.warning(
                    f"   ⚠️ No se encontraron filas con 'tr.selling', intentando selector genérico"
                )
                rows = await page.locator("table tbody tr").all()

            logger.info(f"   📊 Encontradas {len(rows)} filas totales")
            rows_to_process = rows[:5]  # Solo los primeros 5

            for idx, row in enumerate(rows_to_process):
                try:
                    # Extraer precio (buscar el precio en CNY con símbolo ¥)
                    price_element = row.locator("strong.f_Strong")
                    price_text = await price_element.inner_text()

                    # Limpiar precio: "¥ 10.8" -> "10.8"
                    price_clean = re.sub(r"[¥\s]", "", price_text).strip()

                    # Extraer precio en EUR (si está disponible)
                    eur_price = None
                    try:
                        eur_element = row.locator("span.c_Gray.f_12px")
                        eur_text = await eur_element.inner_text()
                        # "(€ 1.31)" -> "1.31"
                        eur_match = re.search(r"€\s*([\d.]+)", eur_text)
                        if eur_match:
                            eur_price = eur_match.group(1)
                    except:
                        pass

                    # Extraer desgaste (wear/paintwear)
                    wear = None
                    try:
                        wear_element = row.locator("div.wear-value")
                        wear_text = await wear_element.inner_text()
                        # "Desgaste: 0.11015310883522034" -> "0.11015310883522034"
                        wear_match = re.search(r"([\d.]+)", wear_text)
                        if wear_match:
                            wear = wear_match.group(1)
                    except:
                        pass

                    # Extraer vendedor
                    seller = None
                    try:
                        seller_element = row.locator("span.user-name")
                        seller = await seller_element.inner_text()
                    except:
                        pass

                    selling_items.append(
                        {
                            "position": idx + 1,
                            "price_cny": price_clean,
                            "price_eur": eur_price,
                            "wear": wear,
                            "seller": seller,
                        }
                    )

                except Exception as e:
                    logger.debug(f"Error extrayendo item en venta {idx}: {e}")
                    continue

        except PlaywrightTimeout:
            logger.warning("Timeout esperando items en venta en BUFF")
        except Exception as e:
            logger.error(f"Error extrayendo selling items: {e}")

        return selling_items

    async def _extract_buff_trade_records(self, page: Page) -> List[Dict]:
        trade_records = []

        try:
            # El tab ya está activo porque navegamos a #tab=history
            logger.info(f"      ⏳ Esperando carga de tabla de trade records...")
            await page.wait_for_timeout(5000)  # Aumentado de 3s a 5s

            # Buscar la tabla de trade records directamente
            logger.info(f"      🔍 Buscando tabla de trade records...")

            # Selector correcto: tbody.list_tb_csgo tr (excluir header con th)
            try:
                await page.wait_for_selector("tbody.list_tb_csgo tr", timeout=15000)
                all_rows = await page.locator("tbody.list_tb_csgo tr").all()
                logger.info(f"      📊 Encontradas {len(all_rows)} filas totales")

                # Filtrar filas que NO sean el header (tienen td, no th)
                data_rows = []
                for row in all_rows:
                    # Verificar si tiene td (datos) en lugar de th (header)
                    td_count = await row.locator("td").count()
                    th_count = await row.locator("th").count()

                    if td_count > 0 and th_count == 0:
                        data_rows.append(row)

                logger.info(
                    f"      📊 Encontradas {len(data_rows)} filas de datos (sin header)"
                )

                if len(data_rows) == 0:
                    logger.warning(
                        f"      ⚠️ No se encontraron filas de datos en trade records"
                    )
                    return []

                all_rows = data_rows

            except Exception as e:
                logger.warning(f"      ⚠️ No se encontró tabla de trade records: {e}")
                # Guardar screenshot de debug
                try:
                    await page.screenshot(
                        path="data/screenshots/debug_no_trade_table.png"
                    )
                    logger.info(
                        f"      📸 Screenshot debug guardado: debug_no_trade_table.png"
                    )
                    # También guardar el HTML para inspección
                    html_content = await page.content()
                    with open(
                        "data/screenshots/debug_page_content.html",
                        "w",
                        encoding="utf-8",
                    ) as f:
                        f.write(html_content)
                    logger.info(f"      📄 HTML guardado: debug_page_content.html")
                except:
                    pass
                return []

            logger.info(f"      📊 Encontradas {len(all_rows)} filas totales")

            logger.info(
                f"      📊 Encontradas {len(all_rows)} filas de datos (sin header)"
            )

            # Procesar las primeras 5 filas con datos
            records_to_process = all_rows[:5]

            for idx, row in enumerate(records_to_process):
                try:
                    # Estructura del HTML:
                    # <td></td>
                    # <td><img></td>
                    # <td class="t_Left"><h3>Item name</h3></td>
                    # <td class="t_Left"><strong class="f_Strong">¥ 197</strong><p class="hide-cny"><span>(€ 23.88)</span></p></td>
                    # <td class="t_Left">Venta</td>
                    # <td class="t_Left c_Gray">2025-11-11</td>

                    price_cny = None
                    price_eur = None
                    date_text = None

                    # Extraer todas las celdas
                    cells = await row.locator("td").all()

                    if len(cells) < 6:
                        logger.warning(
                            f"      ⚠️ Fila {idx+1} no tiene suficientes celdas ({len(cells)})"
                        )
                        continue

                    # Celda 3 (índice 3): Precio
                    try:
                        price_cell = cells[3]
                        # Extraer precio CNY desde strong.f_Strong
                        price_strong = await price_cell.locator(
                            "strong.f_Strong"
                        ).inner_text()
                        # Puede ser "¥ 197" o "¥ 189<small>.5</small>"
                        # Remover el símbolo ¥ y espacios
                        price_text = price_strong.replace("¥", "").strip()
                        # Usar regex para capturar números con decimales opcionales
                        # Captura tanto "197" como "189.5" (ignorando tags HTML)
                        price_match = re.search(r"([\d]+(?:\.[\d]+)?)", price_text)
                        if price_match:
                            price_cny = price_match.group(1)

                        # Extraer precio EUR desde span dentro de p.hide-cny
                        try:
                            eur_span = await price_cell.locator(
                                "p.hide-cny span"
                            ).inner_text()
                            # "(€ 23.88)" -> extraer 23.88
                            eur_match = re.search(r"€\s*([\d.]+)", eur_span)
                            if eur_match:
                                price_eur = eur_match.group(1)
                        except:
                            pass
                    except Exception as e:
                        logger.warning(
                            f"      ⚠️ Error extrayendo precio fila {idx+1}: {e}"
                        )

                    # Celda 5 (índice 5): Fecha
                    try:
                        date_cell = cells[5]
                        date_text = await date_cell.inner_text()
                        date_text = date_text.strip()
                    except:
                        pass

                    if price_cny:
                        trade_records.append(
                            {
                                "position": idx + 1,
                                "price_cny": price_cny,
                                "price_eur": price_eur,
                                "date": date_text,
                            }
                        )
                        logger.info(
                            f"      📊 Record {idx+1}: ¥{price_cny} (€{price_eur or 'N/A'}) - {date_text or 'Sin fecha'}"
                        )
                    else:
                        logger.warning(
                            f"      ⚠️ No se pudo extraer precio de la fila {idx+1}"
                        )

                except Exception as e:
                    logger.warning(
                        f"      ⚠️ Error extrayendo trade record {idx+1}: {e}"
                    )
                    continue

            logger.info(f"      ✅ Extraídos {len(trade_records)} trade records")

        except Exception as e:
            logger.warning(f"Error extrayendo trade records: {e}")

        return trade_records

    def _validate_price_difference(
        self, selling_items: List[Dict], trade_records: List[Dict]
    ) -> bool:
        if not selling_items or not trade_records:
            return False  # No descartar si no hay datos

        try:
            # Calcular precio promedio de venta actual (CNY)
            selling_prices = [
                float(item["price_cny"])
                for item in selling_items
                if item.get("price_cny")
            ]
            if not selling_prices:
                return False

            avg_selling_price = sum(selling_prices) / len(selling_prices)

            # Calcular precio promedio de ventas recientes (CNY)
            # Los trade records están en la misma tabla que selling items
            # Así que también tienen price_cny
            trade_prices = [
                float(record["price_cny"])
                for record in trade_records
                if record.get("price_cny")
            ]
            if not trade_prices:
                return False

            avg_trade_price = sum(trade_prices) / len(trade_prices)

            # Calcular diferencia porcentual
            # Si las ventas recientes son 10% o más MENORES, descartar (precio en caída)
            if avg_trade_price <= avg_selling_price * 0.90:
                logger.info(
                    f"      📉 Precio venta reciente ({avg_trade_price:.2f}) es 10%+ MENOR que actual ({avg_selling_price:.2f}) - Precio en caída"
                )
                return True

            logger.info(
                f"      ✅ Validación de precios OK: Venta actual {avg_selling_price:.2f}, Reciente {avg_trade_price:.2f}"
            )
            return False

        except Exception as e:
            logger.warning(f"Error validando precios: {e}")
            return False  # En caso de error, no descartar

    async def _extract_steam_data(
        self, page: Page, steam_url: str, item_name: str
    ) -> Optional[Dict]:
        try:
            logger.info(f"   Navegando a Steam...")
            await page.goto(
                steam_url, wait_until="domcontentloaded", timeout=self.STEAM_TIMEOUT
            )
            await page.wait_for_timeout(5000)

            # Extraer primeros items en venta
            selling_items = await self._extract_steam_selling_items(page)

            if not selling_items:
                logger.warning(f"   ⚠️ No se encontraron items en venta en Steam")
                return None

            logger.info(
                f"   📊 Encontrados {len(selling_items)} items en venta en Steam"
            )

            return {"selling_items": selling_items}

        except PlaywrightTimeout:
            logger.error(f"   ⏱️ Timeout navegando a Steam")
            return None
        except Exception as e:
            logger.error(f"   ❌ Error extrayendo datos de Steam: {e}")
            return None

    async def _extract_steam_selling_items(self, page: Page) -> List[Dict]:
        selling_items = []

        try:
            # Esperar a que cargue la lista de ventas
            await page.wait_for_selector(".market_listing_row", timeout=10000)

            # Obtener todas las filas disponibles
            all_rows = await page.locator(".market_listing_row").all()

            logger.info(f"      📋 Encontradas {len(all_rows)} filas en Steam")

            # Procesar filas hasta encontrar 5 válidas
            for idx, row in enumerate(all_rows):
                if len(selling_items) >= 5:
                    break  # Ya tenemos 5 items válidos

                try:
                    # Verificar si el item está vendido
                    row_text = await row.inner_text()

                    if "已售出" in row_text or "Sold!" in row_text:
                        logger.debug(f"      ⏭️ Fila {idx+1}: Item vendido, omitiendo")
                        continue

                    # Extraer precio
                    price_element = row.locator(
                        ".market_listing_price.market_listing_price_with_fee"
                    ).first

                    if await price_element.count() == 0:
                        logger.debug(f"      ⏭️ Fila {idx+1}: Sin precio, omitiendo")
                        continue

                    price_text = await price_element.inner_text()

                    # Limpiar precio: "¥ 18.48" -> "18.48"
                    price_clean = re.sub(r"[¥€$\s]", "", price_text).strip()

                    if not price_clean or price_clean == "":
                        logger.debug(f"      ⏭️ Fila {idx+1}: Precio vacío, omitiendo")
                        continue

                    selling_items.append(
                        {
                            "position": len(selling_items) + 1,
                            "price": price_text.strip(),
                            "price_raw": price_clean,
                        }
                    )

                    logger.debug(
                        f"      ✅ Item {len(selling_items)}: {price_text.strip()}"
                    )

                except Exception as e:
                    logger.debug(f"      ⏭️ Error en fila {idx}: {e}, omitiendo")
                    continue

            logger.info(
                f"      ✅ Extraídos {len(selling_items)} items válidos de Steam"
            )

        except PlaywrightTimeout:
            logger.warning("      ⏱️ Timeout esperando items en Steam")
        except Exception as e:
            logger.error(f"      ❌ Error extrayendo selling items de Steam: {e}")

        return selling_items
