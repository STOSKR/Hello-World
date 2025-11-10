"""
Utilidades para guardar archivos del scraper
Maneja JSON, HTML, screenshots y datos de debug
"""

import json
import os
import logging
from typing import List, Dict
from playwright.async_api import Page

# Import relativo al módulo padre (src/)
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config_manager import ScraperConfig

logger = logging.getLogger(__name__)


class FileSaver:
    """Gestiona el guardado de archivos del scraper"""
    
    def __init__(self, config: ScraperConfig):
        """
        Inicializa el gestor de archivos
        
        Args:
            config: Instancia de ScraperConfig
        """
        self.config = config
        self.output_dir = config.get('output.output_directory', 'data')
        
        # Crear directorio si no existe
        os.makedirs(self.output_dir, exist_ok=True)
        
    def save_json(self, data: List[Dict], filename: str = "scraped_data.json"):
        """
        Guarda los datos en un archivo JSON
        
        Args:
            data: Datos a guardar
            filename: Nombre del archivo de salida
        """
        indent = self.config.get('output.json_indent', 2)
        
        # Asegurar que la ruta incluye el directorio
        if not filename.startswith(self.output_dir):
            filename = os.path.join(self.output_dir, os.path.basename(filename))
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        
        logger.info(f"✅ Datos guardados en {filename}")
        
    async def save_debug_files(self, page: Page):
        """
        Guarda archivos de debug (screenshot y HTML) si está habilitado
        
        Args:
            page: Página de Playwright
        """
        save_screenshot = self.config.get('output.save_screenshot', True)
        save_html = self.config.get('output.save_html', True)
        save_debug = self.config.get('debug.save_debug_info', True)
        
        if not save_debug:
            return
            
        # Guardar screenshot
        if save_screenshot:
            await self.save_screenshot(page, "debug_screenshot.png")
            
        # Guardar HTML
        if save_html:
            await self.save_html(page, "page_content.html")
            
    async def save_screenshot(self, page: Page, filename: str = "screenshot.png"):
        """
        Guarda un screenshot de la página
        
        Args:
            page: Página de Playwright
            filename: Nombre del archivo
        """
        try:
            screenshot_path = os.path.join(self.output_dir, filename)
            await page.screenshot(path=screenshot_path)
            logger.info(f"✅ Screenshot guardado en {screenshot_path}")
        except Exception as e:
            logger.warning(f"Error al guardar screenshot: {e}")
            
    async def save_html(self, page: Page, filename: str = "page_content.html"):
        """
        Guarda el HTML de la página
        
        Args:
            page: Página de Playwright
            filename: Nombre del archivo
        """
        try:
            html_path = os.path.join(self.output_dir, filename)
            content = await page.content()
            
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            logger.info(f"✅ HTML guardado en {html_path}")
        except Exception as e:
            logger.warning(f"Error al guardar HTML: {e}")
            
    def ensure_output_directory_exists(self):
        """Asegura que el directorio de salida existe"""
        os.makedirs(self.output_dir, exist_ok=True)
