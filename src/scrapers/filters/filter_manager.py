"""
Gestor de filtros para el scraper
Maneja la configuración de todos los filtros de búsqueda
"""

import logging
from playwright.async_api import Page
from typing import Optional

# Import relativo al módulo padre (src/)
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config_manager import ScraperConfig

logger = logging.getLogger(__name__)


class FilterManager:
    """Gestiona la configuración de filtros en la página de scraping"""
    
    def __init__(self, config: ScraperConfig):
        """
        Inicializa el gestor de filtros
        
        Args:
            config: Instancia de ScraperConfig
        """
        self.config = config
        
    async def configure_all_filters(self, page: Page):
        """
        Configura todos los filtros antes de scrapear usando la configuración
        
        Args:
            page: Página de Playwright
        """
        logger.info("Configurando filtros de búsqueda...")
        
        # 1. Configurar moneda
        await self._configure_currency(page)
        
        # 2. Configurar modo de venta
        await self._configure_sell_mode(page)
        
        # 3. Configurar tipo de balance
        await self._configure_balance_type(page)
        
        # 4. Configurar filtros de precio y volumen
        await self._configure_price_volume_filters(page)
        
        # 5. Configurar plataformas
        await self._configure_platforms(page)
        
        # 6. Ejecutar búsqueda
        await self._execute_search(page)
        
        logger.info("✅ Configuración de filtros completada")
        
    async def _configure_currency(self, page: Page):
        """Configura la moneda según el config"""
        try:
            currency = self.config.get('currency.code')
            await self._change_currency(page, currency)
        except Exception as e:
            logger.warning(f"Error al cambiar moneda: {e}")
            
    async def _change_currency(self, page: Page, currency_code: str = "EUR"):
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
            
            # Buscar el selector de moneda
            currency_selector = page.locator('.el-dropdown-link').first
            
            if await currency_selector.count() > 0:
                # Click en el dropdown de moneda
                await currency_selector.click()
                await page.wait_for_timeout(1000)
                
                # Buscar y hacer click en la moneda deseada
                currency_option = page.locator(f'li:has-text("{currency_code}")')
                
                if await currency_option.count() > 0:
                    await currency_option.first.click()
                    logger.info(f"✅ Moneda cambiada a {currency_code}")
                    await page.wait_for_timeout(3000)  # Esperar a que recargue los precios
                else:
                    logger.warning(f"No se encontró opción {currency_code} en el menú")
                    await page.keyboard.press('Escape')
            else:
                logger.info("✅ La moneda ya está configurada o no se encontró el selector")
                
        except Exception as e:
            logger.warning(f"No se pudo cambiar la moneda: {e}")
            
    async def _configure_sell_mode(self, page: Page):
        """Configura el modo de venta (Quick Sell / Auto Sell)"""
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
            
    async def _configure_balance_type(self, page: Page):
        """Configura el tipo de balance (Steam Balance / All)"""
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
            
    async def _configure_price_volume_filters(self, page: Page):
        """Configura los filtros de precio mínimo/máximo y volumen"""
        try:
            min_price = self.config.get('filters.min_price')
            max_price = self.config.get('filters.max_price')
            min_volume = self.config.get('filters.min_volume')
            
            # Esperar un momento para que los elementos estén listos
            await page.wait_for_timeout(1000)
            
            # Buscar los inputs de filtros (excluyendo el de búsqueda general)
            filter_inputs = await page.locator('.el-input__inner:not(#searchInput)').all()
            
            logger.info(f"Encontrados {len(filter_inputs)} campos de filtro")
            
            # Establecer precio mínimo
            if min_price is not None and len(filter_inputs) >= 1:
                try:
                    logger.info(f"Estableciendo precio mínimo en {min_price}...")
                    await filter_inputs[0].fill(str(min_price), timeout=10000)
                    logger.info(f"✅ Precio mínimo establecido en {min_price}")
                except Exception as e:
                    logger.warning(f"No se pudo establecer precio mínimo: {e}")
            
            # Establecer precio máximo
            if max_price is not None and len(filter_inputs) >= 2:
                try:
                    logger.info(f"Estableciendo precio máximo en {max_price}...")
                    await filter_inputs[1].fill(str(max_price), timeout=10000)
                    logger.info(f"✅ Precio máximo establecido en {max_price}")
                except Exception as e:
                    logger.warning(f"No se pudo establecer precio máximo: {e}")
            
            # Establecer volumen mínimo
            if min_volume is not None:
                volume_idx = 2
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
            
    async def _configure_platforms(self, page: Page):
        """Configura las plataformas habilitadas"""
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
            
            # Para cada plataforma conocida, configurar
            for platform, value in [('C5GAME', 'C5'), ('UU', 'YOUPIN'), ('BUFF', 'BUFF')]:
                try:
                    checkbox = page.locator(f'.el-checkbox:has-text("{platform}")').first
                    
                    if await checkbox.count() > 0:
                        input_checkbox = checkbox.locator('input[type="checkbox"]')
                        
                        is_checked = await input_checkbox.is_checked()
                        should_be_checked = self.config.get(f'platforms.{platform}', False)
                        
                        if is_checked != should_be_checked:
                            await checkbox.click(timeout=5000)
                            status = "marcado" if should_be_checked else "desmarcado"
                            logger.info(f"✅ {platform} {status}")
                        else:
                            logger.info(f"✅ {platform} ya estaba {'marcado' if is_checked else 'desmarcado'}")
                except Exception as e:
                    logger.warning(f"Error configurando plataforma {platform}: {e}")
            
            await page.wait_for_timeout(1000)
        except Exception as e:
            logger.warning(f"Error al configurar plataformas: {e}")
            
    async def _execute_search(self, page: Page):
        """Ejecuta la búsqueda con los filtros configurados"""
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
