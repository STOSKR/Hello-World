"""
Módulo de scrapers para CS-Tracker
Contiene toda la lógica de web scraping organizada en submódulos
"""

from .filters.filter_manager import FilterManager
from .extractors.item_extractor import ItemExtractor
from .extractors.detailed_item_extractor import DetailedItemExtractor
from .utils.browser_manager import BrowserManager
from .utils.file_saver import FileSaver

__all__ = [
    'FilterManager',
    'ItemExtractor',
    'DetailedItemExtractor',
    'BrowserManager',
    'FileSaver'
]
