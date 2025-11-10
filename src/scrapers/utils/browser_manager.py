"""
Gestor de navegador para Playwright
Maneja la inicialización y configuración del navegador
"""

import logging
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from typing import Optional

logger = logging.getLogger(__name__)


class BrowserManager:
    """Gestiona la creación y configuración del navegador Playwright"""
    
    def __init__(self, headless: bool = True):
        """
        Inicializa el gestor de navegador
        
        Args:
            headless: Si True, el navegador se ejecuta sin interfaz gráfica
        """
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
    async def __aenter__(self):
        """Contexto async: Inicializa el navegador"""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Contexto async: Cierra el navegador"""
        await self.close()
        
    async def start(self):
        """Inicia el navegador y crea una nueva página"""
        logger.info("Iniciando navegador...")
        
        self.playwright = await async_playwright().start()
        
        # Usar perfil persistente en directorio temporal del usuario
        # La primera vez, inicia sesión manualmente en BUFF y Steam
        # Las siguientes veces, las sesiones se mantendrán
        import os
        profile_path = os.path.join(os.path.expanduser('~'), '.cs_tracker_profile')
        
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=profile_path,  # Perfil en directorio del usuario
            headless=self.headless,
            channel='chrome',  # Usa el Chrome instalado
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage'
            ],
            ignore_default_args=['--enable-automation']
        )
        
        # El contexto persistente ya viene con páginas, usar la primera o crear una nueva
        if len(self.context.pages) > 0:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()
            
        # Ocultar webdriver property
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
            
        self.browser = None
        logger.info(f"✅ Navegador iniciado con perfil en: {profile_path}")
        
    async def close(self):
        """Cierra el navegador y libera recursos"""
        if self.context:
            await self.context.close()
            logger.info("✅ Navegador cerrado")
        if self.playwright:
            await self.playwright.stop()
            
    async def navigate(self, url: str, timeout: int = 60000):
        """
        Navega a una URL
        
        Args:
            url: URL a navegar
            timeout: Tiempo máximo de espera en milisegundos
        """
        if not self.page:
            raise RuntimeError("El navegador no ha sido iniciado. Llama a start() primero.")
            
        logger.info(f"Navegando a {url}...")
        await self.page.goto(url, wait_until='networkidle', timeout=timeout)
        logger.info("✅ Página cargada")
        
    async def wait(self, milliseconds: int):
        """
        Espera un tiempo específico
        
        Args:
            milliseconds: Milisegundos a esperar
        """
        if not self.page:
            raise RuntimeError("El navegador no ha sido iniciado.")
            
        await self.page.wait_for_timeout(milliseconds)
        
    async def close_modal(self):
        """Intenta cerrar modales comunes que puedan aparecer"""
        if not self.page:
            return
            
        try:
            # Buscar botón de cerrar modal (texto en chino)
            close_button = self.page.locator('button:has-text("我已知晓")')
            if await close_button.count() > 0:
                await close_button.first.click()
                logger.info("✅ Modal cerrado")
                await self.wait(1000)
        except Exception as e:
            logger.debug(f"No se encontró modal o ya estaba cerrado: {e}")
            
    def get_page(self) -> Page:
        """
        Obtiene la página actual
        
        Returns:
            Página de Playwright
        """
        if not self.page:
            raise RuntimeError("El navegador no ha sido iniciado.")
        return self.page
