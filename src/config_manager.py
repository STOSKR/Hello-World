"""
Gestor de configuración para el scraper de SteamDT
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ScraperConfig:
    """Clase para gestionar la configuración del scraper"""

    # Valores por defecto
    DEFAULT_CONFIG = {
        "scraper": {
            "headless": False,
            "timeout": 60000,
            "wait_time": 10000,
            "delay_between_items": 3000,
        },
        "currency": {"code": "EUR", "symbol": "€"},
        "price_mode": {"sell_mode": "Sell at STEAM Lowest Price", "buy_mode": None},
        "balance_type": {"type": "STEAM Balance"},
        "filters": {"min_price": 20, "max_price": None, "min_volume": 40},
        "platforms": {"C5GAME": False, "UU": False, "BUFF": True},
        "output": {
            "save_screenshot": True,
            "save_html": True,
            "json_indent": 2,
            "output_directory": "data",
        },
        "debug": {"log_level": "INFO", "save_debug_info": True},
    }

    # Opciones válidas
    VALID_CURRENCIES = ["CNY", "USD", "RUB", "EUR"]
    VALID_SELL_MODES = [
        "Sell at STEAM Lowest Price",
        "Sell to STEAM Highest Buy Order",
        "Sell at Platform Lowest Price",
        "Sell to Platform Highest Buy Order",
    ]
    VALID_BUY_MODES = ["Buy at Platform Lowest Price", "Buy via Platform Buy Order"]
    VALID_BALANCE_TYPES = ["STEAM Balance", "Platform Balance"]
    VALID_PLATFORMS = ["C5GAME", "UU", "BUFF"]
    VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]

    def __init__(self, config_path: Optional[str] = None, preset: Optional[str] = None):
        """
        Inicializa el gestor de configuración

        Args:
            config_path: Ruta al archivo de configuración JSON
            preset: Número de preset a cargar (1-6)
        """
        self.config_path = config_path or "config/scraper_config.json"
        self.preset_path = "config/preset_configs.json"

        if preset:
            self.config = self._load_preset(preset)
        else:
            self.config = self._load_config()

        self._validate_config()

    def _load_preset(self, preset_id: str) -> Dict[str, Any]:
        """Carga una configuración predefinida"""
        try:
            preset_file = Path(self.preset_path)

            if not preset_file.exists():
                logger.error(f"Archivo de presets no encontrado: {self.preset_path}")
                return self._load_config()

            with open(preset_file, "r", encoding="utf-8") as f:
                presets_data = json.load(f)

            if preset_id not in presets_data["presets"]:
                logger.error(
                    f"Preset '{preset_id}' no encontrado. Opciones: {list(presets_data['presets'].keys())}"
                )
                return self._load_config()

            preset = presets_data["presets"][preset_id]
            common = presets_data["common_settings"]

            # Construir configuración desde preset
            config = self.DEFAULT_CONFIG.copy()
            config["balance_type"]["type"] = preset["balance_type"]
            config["price_mode"]["sell_mode"] = preset["price_mode"]["sell_mode"]
            config["price_mode"]["buy_mode"] = preset["price_mode"]["buy_mode"]
            config["currency"]["code"] = common["currency"]
            config["filters"] = common["filters"].copy()
            config["platforms"] = common["platforms"].copy()

            logger.info(f"Preset cargado: {preset['name']}")
            logger.info(f"  {preset['description']}")

            return config

        except Exception as e:
            logger.error(f"Error al cargar preset: {e}")
            return self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Carga la configuración desde el archivo JSON"""
        try:
            config_file = Path(self.config_path)

            if not config_file.exists():
                logger.warning(
                    f"Archivo de configuración no encontrado: {self.config_path}"
                )
                logger.info("Usando configuración por defecto")
                return self.DEFAULT_CONFIG.copy()

            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Mezclar con valores por defecto para campos faltantes
            merged_config = self._merge_configs(self.DEFAULT_CONFIG, config)

            logger.info(f"Configuración cargada desde {self.config_path}")
            return merged_config

        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear JSON: {e}")
            logger.info("Usando configuración por defecto")
            return self.DEFAULT_CONFIG.copy()
        except Exception as e:
            logger.error(f"Error al cargar configuración: {e}")
            logger.info("Usando configuración por defecto")
            return self.DEFAULT_CONFIG.copy()

    def _merge_configs(self, default: Dict, custom: Dict) -> Dict:
        """Mezcla configuración personalizada con valores por defecto"""
        result = default.copy()

        for key, value in custom.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def _validate_config(self):
        """Valida que la configuración tenga valores válidos"""
        warnings = []

        # Validar moneda
        currency = self.config["currency"]["code"]
        if currency not in self.VALID_CURRENCIES:
            warnings.append(
                f"Moneda '{currency}' no válida. Opciones: {self.VALID_CURRENCIES}"
            )

        # Validar modo de venta
        sell_mode = self.config["price_mode"]["sell_mode"]
        if sell_mode not in self.VALID_SELL_MODES:
            warnings.append(
                f"Modo de venta '{sell_mode}' no válido. Opciones: {self.VALID_SELL_MODES}"
            )

        # Validar tipo de balance
        balance_type = self.config["balance_type"]["type"]
        if balance_type not in self.VALID_BALANCE_TYPES:
            warnings.append(
                f"Tipo de balance '{balance_type}' no válido. Opciones: {self.VALID_BALANCE_TYPES}"
            )

        # Validar plataformas
        for platform in self.config["platforms"]:
            if platform not in self.VALID_PLATFORMS and platform != "description":
                warnings.append(
                    f"Plataforma '{platform}' no reconocida. Opciones válidas: {self.VALID_PLATFORMS}"
                )

        # Validar nivel de log
        log_level = self.config["debug"]["log_level"]
        if log_level not in self.VALID_LOG_LEVELS:
            warnings.append(
                f"Nivel de log '{log_level}' no válido. Opciones: {self.VALID_LOG_LEVELS}"
            )

        # Validar filtros numéricos
        if (
            self.config["filters"]["min_price"] is not None
            and self.config["filters"]["min_price"] < 0
        ):
            warnings.append("min_price no puede ser negativo")

        if (
            self.config["filters"]["min_volume"] is not None
            and self.config["filters"]["min_volume"] < 0
        ):
            warnings.append("min_volume no puede ser negativo")

        # Mostrar advertencias
        if warnings:
            logger.warning("⚠️ Advertencias de configuración:")
            for warning in warnings:
                logger.warning(f"  • {warning}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Obtiene un valor de configuración usando notación de punto

        Args:
            key_path: Ruta del valor (ej: "currency.code")
            default: Valor por defecto si no existe

        Returns:
            Valor de configuración

        Example:
            config.get("currency.code")  # "EUR"
            config.get("filters.min_price")  # 20
        """
        keys = key_path.split(".")
        value = self.config

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key_path: str, value: Any):
        """
        Establece un valor de configuración

        Args:
            key_path: Ruta del valor (ej: "currency.code")
            value: Nuevo valor
        """
        keys = key_path.split(".")
        config = self.config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value

    def save(self, path: Optional[str] = None):
        """
        Guarda la configuración actual en un archivo

        Args:
            path: Ruta del archivo (usa self.config_path si no se especifica)
        """
        save_path = path or self.config_path

        try:
            # Crear directorio si no existe
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)

            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ Configuración guardada en {save_path}")

        except Exception as e:
            logger.error(f"Error al guardar configuración: {e}")
            raise

    def get_enabled_platforms(self) -> list:
        """Retorna lista de plataformas habilitadas"""
        return [
            platform
            for platform, enabled in self.config["platforms"].items()
            if enabled and platform != "description"
        ]

    def print_summary(self):
        print("\nConfiguracion actual del scraper:")
        print(f"  • Modo headless: {self.get('scraper.headless')}")
        print(
            f"  • Moneda: {self.get('currency.code')} ({self.get('currency.symbol')})"
        )
        print(f"  • Balance Type: {self.get('balance_type.type')}")
        print(f"  • Sell Mode: {self.get('price_mode.sell_mode')}")

        buy_mode = self.get("price_mode.buy_mode")
        if buy_mode:
            print(f"  • Buy Mode: {buy_mode}")

        print(f"  • Precio minimo: {self.get('filters.min_price')}")
        print(f"  • Precio maximo: {self.get('filters.max_price') or 'Sin limite'}")
        print(f"  • Volumen minimo: {self.get('filters.min_volume')}")

        enabled_platforms = self.get_enabled_platforms()
        print(
            f"  • Plataformas habilitadas: {', '.join(enabled_platforms) if enabled_platforms else 'Ninguna'}"
        )

        print(f"  • Guardar screenshot: {self.get('output.save_screenshot')}")
        print(f"  • Nivel de log: {self.get('debug.log_level')}")
        print()


def load_config(
    config_path: Optional[str] = None, preset: Optional[str] = None
) -> ScraperConfig:
    """
    Función de conveniencia para cargar configuración

    Args:
        config_path: Ruta al archivo de configuración
        preset: Número de preset a cargar (1-6)

    Returns:
        Instancia de ScraperConfig
    """
    return ScraperConfig(config_path, preset)


if __name__ == "__main__":
    # Test de la clase de configuración
    logging.basicConfig(level=logging.INFO)

    print("\nPresets disponibles:")
    print("  1: STEAM Balance - Lowest Price")
    print("  2: STEAM Balance - Highest Buy Order")
    print("  3: Platform Balance - Lowest Buy/Lowest Sell")
    print("  4: Platform Balance - Lowest Buy/Highest Sell Order")
    print("  5: Platform Balance - Buy Order/Lowest Sell")
    print("  6: Platform Balance - Buy Order/Highest Sell Order")
    print("\nCargando configuración por defecto...")

    config = load_config()
    config.print_summary()

    print("\nPrueba de validación:")
    print(f"Monedas válidas: {ScraperConfig.VALID_CURRENCIES}")
    print(f"Plataformas habilitadas: {config.get_enabled_platforms()}")
