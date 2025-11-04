"""
Script para extraer todas las opciones de configuración disponibles en SteamDT
"""
import asyncio
import json
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def extract_all_config_options():
    """Extrae todas las opciones de configuración de la página"""
    
    config_options = {
        "tabs": [],
        "balance_types": [],
        "input_fields": [],
        "platforms": [],
        "currencies": [],
        "other_options": []
    }
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        try:
            logger.info("Navegando a SteamDT...")
            await page.goto("https://steamdt.com/en/hanging", wait_until='networkidle', timeout=60000)
            await page.wait_for_timeout(5000)
            
            # Cerrar modal si aparece
            try:
                close_button = page.locator('button:has-text("我已知晓")')
                if await close_button.count() > 0:
                    await close_button.first.click()
                    await page.wait_for_timeout(1000)
            except:
                pass
            
            # 1. Extraer tabs de precio (Sell at STEAM...)
            logger.info("Extrayendo tabs de precio...")
            tabs = await page.locator('.tabs-item').all()
            for tab in tabs:
                text = await tab.inner_text()
                classes = await tab.get_attribute('class')
                is_active = 'active' in classes
                config_options["tabs"].append({
                    "text": text.strip(),
                    "default_active": is_active
                })
            
            # 2. Extraer tipos de balance
            logger.info("Extrayendo tipos de balance...")
            balance_tabs = await page.locator('.tabs-item').all()
            for tab in balance_tabs:
                text = await tab.inner_text()
                if 'Balance' in text or 'balance' in text.lower():
                    classes = await tab.get_attribute('class')
                    is_active = 'active' in classes
                    if not any(b['text'] == text.strip() for b in config_options["balance_types"]):
                        config_options["balance_types"].append({
                            "text": text.strip(),
                            "default_active": is_active
                        })
            
            # 3. Extraer campos de entrada (precio, volumen, etc.)
            logger.info("Extrayendo campos de entrada...")
            inputs = await page.locator('.el-input__inner').all()
            for idx, input_elem in enumerate(inputs[:10]):  # Primeros 10
                placeholder = await input_elem.get_attribute('placeholder')
                value = await input_elem.get_attribute('value')
                input_id = await input_elem.get_attribute('id')
                
                # Intentar obtener el label asociado
                label = None
                try:
                    parent = page.locator(f'#{ input_id}').locator('..')
                    label_elem = parent.locator('label, .el-form-item__label').first
                    if await label_elem.count() > 0:
                        label = await label_elem.inner_text()
                except:
                    pass
                
                config_options["input_fields"].append({
                    "index": idx,
                    "id": input_id,
                    "label": label,
                    "placeholder": placeholder,
                    "default_value": value,
                    "description": f"Input field #{idx}"
                })
            
            # 4. Abrir Platform Settings y extraer plataformas
            logger.info("Abriendo Platform Settings...")
            platform_settings = page.locator('.text-blue:has-text("Platform Settings")')
            if await platform_settings.count() > 0:
                await platform_settings.first.click()
                await page.wait_for_timeout(1500)
                
                logger.info("Extrayendo plataformas disponibles...")
                checkboxes = await page.locator('.el-checkbox').all()
                for checkbox in checkboxes:
                    label = await checkbox.locator('.el-checkbox__label').inner_text()
                    input_elem = checkbox.locator('input[type="checkbox"]')
                    is_checked = await input_elem.is_checked()
                    value = await input_elem.get_attribute('value')
                    
                    config_options["platforms"].append({
                        "name": label.strip(),
                        "value": value,
                        "default_checked": is_checked
                    })
            
            # 5. Extraer monedas disponibles
            logger.info("Extrayendo monedas disponibles...")
            try:
                currency_selector = page.locator('.el-dropdown-link')
                if await currency_selector.count() > 0:
                    current_currency = await currency_selector.first.inner_text()
                    config_options["currencies"].append({
                        "code": current_currency.strip(),
                        "is_current": True
                    })
                    
                    # Abrir dropdown para ver todas las opciones
                    await currency_selector.first.click()
                    await page.wait_for_timeout(1000)
                    
                    currency_options = await page.locator('.el-dropdown-menu li').all()
                    for option in currency_options:
                        currency = await option.inner_text()
                        config_options["currencies"].append({
                            "code": currency.strip(),
                            "is_current": False
                        })
                    
                    # Cerrar dropdown
                    await page.keyboard.press('Escape')
                    await page.wait_for_timeout(500)
            except Exception as e:
                logger.warning(f"No se pudieron extraer monedas: {e}")
            
            # 6. Buscar otros elementos de configuración
            logger.info("Buscando otros elementos de configuración...")
            
            # Buscar selects/dropdowns
            selects = await page.locator('.el-select').all()
            for idx, select in enumerate(selects[:5]):
                try:
                    text = await select.inner_text()
                    config_options["other_options"].append({
                        "type": "select",
                        "index": idx,
                        "text": text.strip()
                    })
                except:
                    pass
            
            # Buscar switches
            switches = await page.locator('.el-switch').all()
            for idx, switch in enumerate(switches[:5]):
                try:
                    is_checked = await switch.locator('input').is_checked()
                    config_options["other_options"].append({
                        "type": "switch",
                        "index": idx,
                        "checked": is_checked
                    })
                except:
                    pass
            
            # Guardar screenshot
            await page.screenshot(path="data/config_screenshot.png")
            logger.info("Screenshot guardado en data/config_screenshot.png")
            
        finally:
            await browser.close()
    
    return config_options


async def main():
    logger.info("🔍 Extrayendo configuraciones de SteamDT...")
    
    config = await extract_all_config_options()
    
    # Guardar en JSON
    with open('data/extracted_config_options.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    logger.info("✅ Configuraciones extraídas y guardadas en data/extracted_config_options.json")
    
    # Mostrar resumen
    print("\n📊 Resumen de opciones encontradas:")
    print(f"  • Tabs de precio: {len(config['tabs'])}")
    print(f"  • Tipos de balance: {len(config['balance_types'])}")
    print(f"  • Campos de entrada: {len(config['input_fields'])}")
    print(f"  • Plataformas: {len(config['platforms'])}")
    print(f"  • Monedas: {len(config['currencies'])}")
    print(f"  • Otras opciones: {len(config['other_options'])}")
    
    print("\n📋 Preview de configuraciones:")
    print(json.dumps(config, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
