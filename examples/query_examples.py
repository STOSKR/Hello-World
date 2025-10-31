"""
Script de ejemplo para consultar y analizar datos de Supabase
"""
from dotenv import load_dotenv
from src.database import SupabaseDB
import json

def main():
    # Cargar variables de entorno
    load_dotenv()
    
    # Conectar a la base de datos
    db = SupabaseDB()
    
    print("=" * 60)
    print("📊 Ejemplos de Consultas a Supabase")
    print("=" * 60)
    
    # Ejemplo 1: Obtener últimos items
    print("\n1️⃣ Últimos 5 items scrapeados:")
    print("-" * 60)
    latest = db.get_latest_items(limit=5)
    for item in latest:
        print(f"  • {item.get('item_name', 'N/A')} - {item.get('scraped_at', 'N/A')}")
    
    # Ejemplo 2: Historial de un item
    if latest and latest[0].get('item_name'):
        item_name = latest[0]['item_name']
        print(f"\n2️⃣ Historial de '{item_name}':")
        print("-" * 60)
        history = db.get_item_history(item_name, limit=3)
        for h in history:
            print(f"  • {h.get('scraped_at', 'N/A')} - Precio: {h.get('buy_price', 'N/A')}")
    
    # Ejemplo 3: Estadísticas generales
    print("\n3️⃣ Estadísticas:")
    print("-" * 60)
    all_items = db.get_latest_items(limit=1000)
    print(f"  • Total de registros recientes: {len(all_items)}")
    
    unique_items = set(item.get('item_name') for item in all_items if item.get('item_name'))
    print(f"  • Items únicos: {len(unique_items)}")
    
    print("\n" + "=" * 60)
    print("✅ Ejemplos completados")
    print("=" * 60)

if __name__ == "__main__":
    main()
