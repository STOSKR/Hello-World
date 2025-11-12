"""
Extractor de items desde la tabla HTML
Parsea y estructura los datos de los items
"""

import logging
import re
from datetime import datetime
from playwright.async_api import Page
from typing import List, Dict

logger = logging.getLogger(__name__)


class ItemExtractor:
    """Extrae y parsea items de la tabla de resultados"""
    
    def __init__(self):
        """Inicializa el extractor de items"""
        pass
        
    async def extract_items(self, page: Page, url: str) -> List[Dict]:
        """
        Extrae todos los items de la página
        
        Args:
            page: Página de Playwright
            url: URL de la página (para referencia)
            
        Returns:
            Lista de items extraídos
        """
        items = []
        timestamp = datetime.utcnow().isoformat()
        
        try:
            # Esperar un poco más para asegurar que la tabla cargó
            await page.wait_for_timeout(3000)
            
            logger.info("Analizando estructura de la página...")
            
            # Obtener el HTML para análisis
            content = await page.content()
            
            # Intentar extraer datos de múltiples posibles estructuras
            rows = await self._find_table_rows(page)
            
            logger.info(f"Se encontraron {len(rows)} filas/items para procesar")
            
            # Contador de items válidos procesados
            valid_item_count = 0
            
            for idx, row in enumerate(rows):
                try:
                    item = await self._extract_single_item(row, idx, timestamp)
                    
                    if item:
                        valid_item_count += 1
                        item['id'] = valid_item_count
                        items.append(item)
                        
                except Exception as e:
                    logger.warning(f"Error extrayendo item {idx}: {e}")
                    continue
            
            # Si no se encontraron items, guardar snapshot para debugging
            if len(items) == 0:
                logger.warning("No se encontraron items con los selectores actuales")
                items.append({
                    'type': 'html_snapshot',
                    'scraped_at': timestamp,
                    'content': content[:5000],  # Primeros 5000 caracteres
                    'url': url,
                    'note': 'Los selectores necesitan ajuste. Analiza este HTML.'
                })
                
        except Exception as e:
            logger.error(f"Error al extraer items: {e}")
            raise
        
        return items
        
    async def _find_table_rows(self, page: Page):
        """
        Encuentra las filas de la tabla usando múltiples selectores
        
        Args:
            page: Página de Playwright
            
        Returns:
            Lista de elementos de filas visibles únicamente
        """
        # Selector más específico para steamdt.com - solo filas visibles
        selector = '.el-table__body .el-table__row'
        
        try:
            # Obtener SOLO las filas que están visibles en el viewport
            rows = await page.locator(selector).all()
            
            # Filtrar solo las que tienen contenido válido (al menos 6 celdas)
            valid_rows = []
            for row in rows:
                cells = await row.locator('td').all()
                if len(cells) >= 6:
                    valid_rows.append(row)
            
            logger.info(f"Encontrados {len(rows)} elementos con selector: {selector}")
            logger.info(f"De los cuales {len(valid_rows)} tienen estructura válida")
            
            return valid_rows
            
        except Exception as e:
            logger.error(f"Error buscando filas: {e}")
            return []
        
    async def _extract_single_item(self, row, idx: int, timestamp: str) -> Dict:
        """
        Extrae un solo item de una fila
        
        Args:
            row: Elemento de la fila
            idx: Índice de la fila
            timestamp: Timestamp del scraping
            
        Returns:
            Diccionario con datos del item o None si debe omitirse
        """
        try:
            # Extraer todas las celdas (td) de la fila
            cells = await row.locator('td').all()
            
            if len(cells) < 6:
                return None

            # Estructura de columnas:
            # 0: Ranking
            # 1: Nombre del item + URL
            # 2: BUFF - Precio de compra + tiempo + LINK
            # 3: STEAM - Precio de venta + tiempo + LINK
            # 4: Precio neto de venta
            # 5: Volumen/Ventas
            # 6: Ratio compra/venta
            # 7: Segundo ratio
            # 8: Acciones
            
            # Extraer nombre y URL del item
            item_data = await self._extract_item_name_and_url(cells, idx)
            if not item_data:
                return None
                
            item_name, item_url, item_quality, is_stattrak = item_data
            
            # FILTROS DE VALIDACIÓN
            
            # 1. IGNORAR STICKERS
            if item_name.lower().startswith('sticker'):
                return None
            
            # 2. DEBE CONTENER | (pipes) para ser arma/skin válida
            # Esto excluye: pins, cajas, llaves, parches, etc.
            if '|' not in item_name:
                logger.debug(f"Item sin '|' omitido: {item_name}")
                return None
            
            # Extraer URLs de BUFF y Steam desde la fila
            buff_url = await self._extract_platform_url(cells, 2, "buff.163.com")
            steam_url = await self._extract_platform_url(cells, 3, "steamcommunity.com/market/listings")
            
            # Crear objeto item con URLs incluidas
            item = {
                'scraped_at': timestamp,
                'url': item_url,
                'item_name': item_name,
                'quality': item_quality,
                'stattrak': is_stattrak,
                'buff_url': buff_url,
                'steam_url': steam_url
            }
            
            return item
        except Exception as e:
            logger.debug(f"Error procesando fila {idx}: {e}")
            return None
        
    async def _extract_item_name_and_url(self, cells, idx: int):
        """
        Extrae el nombre, URL, calidad y StatTrak del item
        
        Returns:
            Tupla (nombre, url, calidad, is_stattrak) o None si falla
        """
        try:
            name_cell = cells[1] if len(cells) > 1 else None
            if not name_cell:
                return None
                
            # Buscar el enlace <a> que contiene el nombre completo
            name_link_element = name_cell.locator('a').first
            item_name = await name_link_element.inner_text()
            item_name = item_name.strip()
            
            # Extraer la URL del item
            item_url = await name_link_element.get_attribute('href')
            if item_url and not item_url.startswith('http'):
                item_url = f"https://steamdt.com{item_url}"
            
            # Detectar StatTrak™
            is_stattrak = 'StatTrak™' in item_name or 'stattrak' in item_name.lower()
            
            # Extraer calidad (todo entre paréntesis al final)
            item_quality = None
            quality_match = re.search(r'\(([^)]+)\)$', item_name)
            if quality_match:
                item_quality = quality_match.group(1)
                # Remover la calidad del nombre del item
                item_name = re.sub(r'\s*\([^)]+\)$', '', item_name).strip()
            
            return (item_name, item_url, item_quality, is_stattrak)
            
        except Exception as e:
            logger.debug(f"No se pudo extraer nombre en fila {idx}: {e}")
            return None
            
    async def _extract_platform_url(self, cells, cell_idx: int, url_pattern: str):
        """
        Extrae la URL de una plataforma (BUFF o Steam) desde una celda
        
        Args:
            cells: Lista de celdas de la fila
            cell_idx: Índice de la celda
            url_pattern: Patrón de URL a buscar (ej: "buff.163.com")
            
        Returns:
            URL de la plataforma o None si no se encuentra
        """
        try:
            cell = cells[cell_idx] if len(cells) > cell_idx else None
            if not cell:
                return None
            
            # Buscar enlace <a> que contenga el patrón de URL
            link = cell.locator(f'a[href*="{url_pattern}"]').first
            url = await link.get_attribute('href')
            return url
            
        except Exception as e:
            logger.debug(f"No se pudo extraer URL {url_pattern} de celda {cell_idx}: {e}")
            return None
            
    async def _extract_price_data(self, cells, cell_idx: int, row_idx: int, platform: str):
        """
        Extrae precio y tiempo de una celda
        
        Returns:
            Tupla (precio, tiempo)
        """
        try:
            cell = cells[cell_idx] if len(cells) > cell_idx else None
            if not cell:
                return (None, None)
                
            # Extraer el precio
            price = await cell.locator('span').first.inner_text()
            price = price.strip()
            
            # Extraer el tiempo
            time_text = None
            try:
                time_text = await cell.locator('.text-12').first.inner_text()
                time_text = time_text.strip()
            except:
                pass
                
            return (price, time_text)
            
        except Exception as e:
            logger.debug(f"No se pudo extraer precio {platform} en fila {row_idx}: {e}")
            return (None, None)
            
    async def _extract_text_from_cell(self, cells, cell_idx: int, row_idx: int):
        """
        Extrae texto simple de una celda
        
        Returns:
            Texto de la celda o None
        """
        try:
            cell = cells[cell_idx] if len(cells) > cell_idx else None
            if cell:
                text = await cell.inner_text()
                return text.strip()
        except Exception as e:
            logger.debug(f"No se pudo extraer texto de celda {cell_idx} en fila {row_idx}: {e}")
        
        return None
