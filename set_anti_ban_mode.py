#!/usr/bin/env python3
"""
Script para configurar el modo anti-ban del scraper

Uso:
    python set_anti_ban_mode.py safe       # Modo seguro (recomendado)
    python set_anti_ban_mode.py balanced   # Modo balanceado
    python set_anti_ban_mode.py fast       # Modo rápido (más riesgo)
    python set_anti_ban_mode.py stealth    # Modo sigiloso (máxima seguridad)
"""

import json
import sys
from pathlib import Path


def load_json(filepath):
    """Cargar archivo JSON"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filepath, data):
    """Guardar archivo JSON con formato"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def apply_anti_ban_preset(mode):
    """Aplicar preset de configuración anti-ban"""
    config_dir = Path(__file__).parent / "config"
    preset_file = config_dir / "preset_configs.json"
    scraper_config_file = config_dir / "scraper_config.json"

    # Cargar archivos
    presets = load_json(preset_file)
    scraper_config = load_json(scraper_config_file)

    # Verificar que el modo existe
    if mode not in presets.get("anti_ban_presets", {}):
        print(f"❌ Error: Modo '{mode}' no encontrado")
        print("\nModos disponibles:")
        for preset_name, preset_data in presets.get("anti_ban_presets", {}).items():
            print(f"  • {preset_name}: {preset_data['name']}")
            print(f"    {preset_data['description']}")
        return False

    # Obtener configuración del preset
    preset = presets["anti_ban_presets"][mode]

    # Actualizar configuración del scraper
    scraper_config["scraper"]["max_concurrent"] = preset["max_concurrent"]
    scraper_config["scraper"]["delay_between_items"] = preset["delay_between_items"]
    scraper_config["scraper"]["random_delay_min"] = preset["random_delay_min"]
    scraper_config["scraper"]["random_delay_max"] = preset["random_delay_max"]
    scraper_config["scraper"]["delay_between_batches"] = preset["delay_between_batches"]

    # Guardar configuración actualizada
    save_json(scraper_config_file, scraper_config)

    # Mostrar resumen
    print(f"✅ Modo anti-ban configurado: {preset['name']}")
    print(f"\n📋 Configuración aplicada:")
    print(f"   • Items concurrentes: {preset['max_concurrent']}")
    print(f"   • Delay entre items: {preset['delay_between_items']}ms")
    print(f"   • Delay aleatorio: {preset['random_delay_min']}-{preset['random_delay_max']}ms")
    print(f"   • Delay entre lotes: {preset['delay_between_batches']}ms")
    print(f"\n💡 {preset['description']}")

    # Calcular tiempo estimado para 100 items
    avg_delay = (preset["random_delay_min"] + preset["random_delay_max"]) / 2
    time_per_item = (preset["delay_between_items"] + avg_delay) / 1000
    items_per_batch = preset["max_concurrent"]
    delay_per_batch = preset["delay_between_batches"] / 1000
    total_time_100 = (100 / items_per_batch) * (
        time_per_item * items_per_batch + delay_per_batch
    )

    print(f"\n⏱️  Tiempo estimado para 100 items: ~{total_time_100/60:.1f} minutos")

    return True


def main():
    if len(sys.argv) < 2:
        print("❌ Error: Debes especificar un modo")
        print("\nUso: python set_anti_ban_mode.py <modo>")
        print("\nModos disponibles:")
        print("  • safe      - Modo seguro (recomendado)")
        print("  • balanced  - Modo balanceado")
        print("  • fast      - Modo rápido (más riesgo)")
        print("  • stealth   - Modo sigiloso (máxima seguridad)")
        sys.exit(1)

    mode = sys.argv[1].lower()
    success = apply_anti_ban_preset(mode)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
