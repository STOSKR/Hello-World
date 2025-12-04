"""
Filter manager for web scraping configuration.
Manages all search filter configuration on the web interface.
"""

from playwright.async_api import Page
from typing import Optional

from app.core.logger import get_logger
from app.core.config import Settings

logger = get_logger(__name__)


class FilterManager:
    """Manages search filter configuration on scraping page."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def configure_all_filters(self, page: Page):
        """Configure all search filters."""
        logger.info("configuring_search_filters")

        # La página /en/hanging tiene TODOS los filtros disponibles
        # Configurar en el orden correcto:

        # 1. Cerrar modal si aparece
        await self._close_modal(page)

        # 2. Configure currency
        await self._configure_currency(page)

        # 3. Configure sell mode
        await self._configure_sell_mode(page)

        # 4. Configure buy mode (if applicable)
        await self._configure_buy_mode(page)

        # 5. Configure balance type
        await self._configure_balance_type(page)

        # 6. Configure price and volume filters
        await self._configure_price_volume_filters(page)

        # 7. Configure platforms
        await self._configure_platforms(page)

        # 8. Execute search
        await self._execute_search(page)

        logger.info("filter_configuration_completed")

    async def _close_modal(self, page: Page):
        """Close initial modal if it appears."""
        try:
            logger.info("checking_for_modal")
            # Buscar botón de cerrar modal (puede ser en chino o inglés)
            close_selectors = [
                'button:has-text("我已知晓")',  # Chino
                'button:has-text("I understand")',  # Inglés
                ".el-dialog__close",  # Botón X
                'button.el-button:has-text("OK")',
            ]

            for selector in close_selectors:
                close_button = page.locator(selector).first
                if await close_button.count() > 0:
                    await close_button.click()
                    await page.wait_for_timeout(500)  # Reduced from 1000ms
                    logger.info("modal_closed", selector=selector)
                    return

            logger.info("no_modal_found")
        except Exception as e:
            logger.warning("modal_close_failed", error=str(e))

    async def _configure_currency(self, page: Page):
        """Configure currency filter."""
        try:
            currency = self.settings.currency_code
            await self._change_currency(page, currency)
        except Exception as e:
            logger.warning("currency_configuration_error", error=str(e))

    async def _change_currency(self, page: Page, currency_code: str = "EUR"):
        """Change currency on the page."""
        try:
            logger.info("changing_currency", target=currency_code)

            # Wait for page to load completely
            await page.wait_for_timeout(500)

            # Find currency selector (puede ser .el-dropdown-link o similar)
            # Probar múltiples selectores
            selectors = [
                ".el-dropdown-link",
                "[class*='currency']",
                "[class*='dropdown']",
            ]

            currency_selector = None
            for selector in selectors:
                locator = page.locator(selector).first
                if await locator.count() > 0:
                    currency_selector = locator
                    logger.info("currency_selector_found", selector=selector)
                    break

            if currency_selector:
                # Click on currency dropdown
                await currency_selector.click()
                await page.wait_for_timeout(300)

                # Find and click desired currency
                currency_option = page.locator(f'li:has-text("{currency_code}")')

                if await currency_option.count() > 0:
                    await currency_option.first.click()
                    logger.info("currency_changed", currency=currency_code)
                    await page.wait_for_timeout(1000)  # Wait for prices to reload
                else:
                    logger.warning("currency_option_not_found", currency=currency_code)
                    await page.keyboard.press("Escape")
            else:
                logger.warning("currency_selector_not_found", tried_selectors=selectors)

        except Exception as e:
            logger.warning("currency_change_failed", error=str(e))

    async def _configure_sell_mode(self, page: Page):
        """Configure sell mode filter."""
        try:
            # Get sell mode from settings (e.g., "Lowest Price")
            # Assuming settings has this, adapt as needed
            sell_mode = getattr(self.settings, "sell_mode", "Lowest Price")
            logger.info("checking_sell_mode", mode=sell_mode)

            sell_tab = page.locator(f'.tabs-item:has-text("{sell_mode}")')
            if await sell_tab.count() > 0:
                tab_class = await sell_tab.first.get_attribute("class")
                if "active" not in tab_class:
                    await sell_tab.first.click()
                    await page.wait_for_timeout(300)
                    logger.info("sell_mode_selected", mode=sell_mode)
                else:
                    logger.info("sell_mode_already_selected", mode=sell_mode)
        except Exception as e:
            logger.warning("sell_mode_configuration_error", error=str(e))

    async def _configure_buy_mode(self, page: Page):
        """Configure buy mode filter."""
        try:
            # Get buy mode from settings if exists
            buy_mode = getattr(self.settings, "buy_mode", None)
            if not buy_mode:
                logger.info("no_buy_mode_configured_skipping")
                return

            logger.info("checking_buy_mode", mode=buy_mode)

            buy_tab = page.locator(f'.tabs-item:has-text("{buy_mode}")')
            if await buy_tab.count() > 0:
                tab_class = await buy_tab.first.get_attribute("class")
                if "active" not in tab_class:
                    await buy_tab.first.click()
                    await page.wait_for_timeout(300)
                    logger.info("buy_mode_selected", mode=buy_mode)
                else:
                    logger.info("buy_mode_already_selected", mode=buy_mode)
        except Exception as e:
            logger.warning("buy_mode_configuration_error", error=str(e))

    async def _configure_balance_type(self, page: Page):
        """Configure balance type filter."""
        try:
            # Get balance type from settings
            balance_type = getattr(self.settings, "balance_type", "BUFF-STEAM")
            logger.info("checking_balance_type", type=balance_type)

            balance_tab = page.locator(f'.tabs-item:has-text("{balance_type}")')
            if await balance_tab.count() > 0:
                tab_class = await balance_tab.first.get_attribute("class")
                if "active" not in tab_class:
                    await balance_tab.first.click()
                    await page.wait_for_timeout(300)
                    logger.info("balance_type_selected", type=balance_type)
                else:
                    logger.info("balance_type_already_selected", type=balance_type)
        except Exception as e:
            logger.warning("balance_type_configuration_error", error=str(e))

    async def _configure_price_volume_filters(self, page: Page):
        """Configure price and volume filters."""
        try:
            min_price = self.settings.min_price
            max_price = self.settings.max_price
            min_volume = self.settings.min_volume

            # Wait for elements to be ready
            await page.wait_for_timeout(300)

            # Find filter inputs (excluding general search input)
            filter_inputs = await page.locator(
                ".el-input__inner:not(#searchInput)"
            ).all()

            logger.info("filter_inputs_found", count=len(filter_inputs))

            # Set minimum price
            if min_price is not None and len(filter_inputs) >= 1:
                try:
                    logger.info("setting_min_price", value=min_price)
                    await filter_inputs[0].fill(str(min_price), timeout=10000)
                    logger.info("min_price_set", value=min_price)
                except Exception as e:
                    logger.warning("min_price_set_failed", error=str(e))

            # Set maximum price
            if max_price is not None and len(filter_inputs) >= 2:
                try:
                    logger.info("setting_max_price", value=max_price)
                    await filter_inputs[1].fill(str(max_price), timeout=10000)
                    logger.info("max_price_set", value=max_price)
                except Exception as e:
                    logger.warning("max_price_set_failed", error=str(e))

            # Set minimum volume
            if min_volume is not None:
                volume_idx = 2
                if len(filter_inputs) > volume_idx:
                    try:
                        logger.info("setting_min_volume", value=min_volume)
                        await filter_inputs[volume_idx].fill(
                            str(min_volume), timeout=10000
                        )
                        logger.info("min_volume_set", value=min_volume)
                    except Exception as e:
                        logger.warning("min_volume_set_failed", error=str(e))

            await page.wait_for_timeout(300)
        except Exception as e:
            logger.warning("price_volume_filters_configuration_error", error=str(e))

    async def _configure_platforms(self, page: Page):
        """Configure platform filters."""
        try:
            logger.info("opening_platform_settings")
            platform_settings = page.locator('.text-blue:has-text("Platform Settings")')

            if await platform_settings.count() > 0:
                await platform_settings.first.click()
                await page.wait_for_timeout(500)
                logger.info("platform_settings_opened")

            # Configure platforms according to settings
            logger.info("configuring_platforms")

            # For each known platform, configure
            for platform, attr_name in [
                ("C5GAME", "platform_c5game"),
                ("UU", "platform_uu"),
                ("BUFF", "platform_buff"),
            ]:
                try:
                    checkbox = page.locator(
                        f'.el-checkbox:has-text("{platform}")'
                    ).first

                    if await checkbox.count() > 0:
                        input_checkbox = checkbox.locator('input[type="checkbox"]')

                        is_checked = await input_checkbox.is_checked()
                        should_be_checked = getattr(self.settings, attr_name, False)

                        if is_checked != should_be_checked:
                            await checkbox.click(timeout=5000)
                            status = "checked" if should_be_checked else "unchecked"
                            logger.info(
                                "platform_configured", platform=platform, status=status
                            )
                        else:
                            logger.info(
                                "platform_already_configured",
                                platform=platform,
                                status="checked" if is_checked else "unchecked",
                            )
                except Exception as e:
                    logger.warning(
                        "platform_configuration_error", platform=platform, error=str(e)
                    )

            await page.wait_for_timeout(300)
        except Exception as e:
            logger.warning("platforms_configuration_error", error=str(e))

    async def _execute_search(self, page: Page):
        """Execute search with configured filters."""
        try:
            logger.info("executing_search")
            confirm_btn = page.locator(
                '.bg-\\[\\#0252D9\\]:has-text("Confirm and Search")'
            )

            if await confirm_btn.count() > 0:
                await confirm_btn.first.click()
                logger.info("search_initiated")
                await page.wait_for_timeout(2000)
                logger.info("waiting_for_results")
        except Exception as e:
            logger.warning("search_execution_error", error=str(e))
