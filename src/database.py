"""
Módulo para interactuar con Supabase (PostgreSQL)
Gestiona el almacenamiento y recuperación de datos históricos
"""
import os
from datetime import datetime
from typing import List, Dict, Optional
from supabase import create_client, Client
import logging

logger = logging.getLogger(__name__)


class SupabaseDB:
    """Cliente para interactuar con Supabase"""
    
    def __init__(self):
        """Inicializa la conexión con Supabase"""
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        
        if not self.url or not self.key:
            raise ValueError(
                "Las variables de entorno SUPABASE_URL y SUPABASE_KEY son requeridas. "
                "Crea un archivo .env basado en .env.example"
            )
        
        self.client: Client = create_client(self.url, self.key)
        logger.info("Conexión a Supabase establecida")
    
    async def save_scraped_items(self, items: List[Dict], source: str = "steamdt_hanging") -> bool:
        """
        Guarda items scrapeados en la base de datos
        
        Args:
            items: Lista de items extraídos del scraping
            source: Fuente de los datos
            
        Returns:
            True si se guardó exitosamente
        """
        try:
            # Preparar datos para inserción
            records = []
            for item in items:
                record = {
                    'source': source,
                    'scraped_at': item.get('scraped_at', datetime.utcnow().isoformat()),
                    'item_name': item.get('item_name'),
                    'buy_price': item.get('buy_price'),
                    'sell_price': item.get('sell_price'),
                    'profit': item.get('profit'),
                    'raw_data': item,  # Guardar todo el objeto como JSONB
                }
                records.append(record)
            
            # Insertar en la tabla 'scraped_items'
            response = self.client.table('scraped_items').insert(records).execute()
            
            logger.info(f"✅ {len(records)} items guardados en Supabase")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error guardando datos en Supabase: {e}")
            raise
    
    def get_latest_items(self, limit: int = 100) -> List[Dict]:
        """
        Obtiene los últimos items scrapeados
        
        Args:
            limit: Número máximo de items a recuperar
            
        Returns:
            Lista de items
        """
        try:
            response = self.client.table('scraped_items')\
                .select('*')\
                .order('scraped_at', desc=True)\
                .limit(limit)\
                .execute()
            
            logger.info(f"📥 {len(response.data)} items recuperados")
            return response.data
            
        except Exception as e:
            logger.error(f"❌ Error recuperando datos: {e}")
            raise
    
    def get_items_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Obtiene items en un rango de fechas
        
        Args:
            start_date: Fecha inicio (ISO format)
            end_date: Fecha fin (ISO format)
            
        Returns:
            Lista de items en el rango
        """
        try:
            response = self.client.table('scraped_items')\
                .select('*')\
                .gte('scraped_at', start_date)\
                .lte('scraped_at', end_date)\
                .order('scraped_at', desc=False)\
                .execute()
            
            logger.info(f"📥 {len(response.data)} items en rango {start_date} - {end_date}")
            return response.data
            
        except Exception as e:
            logger.error(f"❌ Error recuperando datos por rango: {e}")
            raise
    
    def get_item_history(self, item_name: str, limit: int = 50) -> List[Dict]:
        """
        Obtiene el historial de un item específico
        
        Args:
            item_name: Nombre del item
            limit: Número de registros
            
        Returns:
            Historial del item
        """
        try:
            response = self.client.table('scraped_items')\
                .select('*')\
                .eq('item_name', item_name)\
                .order('scraped_at', desc=True)\
                .limit(limit)\
                .execute()
            
            logger.info(f"📥 {len(response.data)} registros históricos de '{item_name}'")
            return response.data
            
        except Exception as e:
            logger.error(f"❌ Error recuperando historial: {e}")
            raise
    
    def get_price_changes(self, hours: int = 24) -> List[Dict]:
        """
        Analiza cambios de precio en las últimas X horas
        
        Args:
            hours: Horas hacia atrás para analizar
            
        Returns:
            Lista de items con cambios de precio
        """
        try:
            # Esta query necesita ser ajustada según tu lógica de negocio
            # Ejemplo básico:
            response = self.client.rpc(
                'get_price_changes',
                {'hours_ago': hours}
            ).execute()
            
            return response.data
            
        except Exception as e:
            logger.warning(f"⚠️ get_price_changes requiere función SQL personalizada: {e}")
            return []
    
    def create_tables_if_not_exist(self):
        """
        Crea las tablas necesarias si no existen
        Nota: Preferiblemente ejecuta esto manualmente en el dashboard de Supabase
        """
        logger.info("⚠️ Las tablas deben crearse en el dashboard de Supabase")
        logger.info("📋 Script SQL necesario guardado en: config/schema.sql")


def get_db() -> SupabaseDB:
    """Factory function para obtener instancia de la base de datos"""
    return SupabaseDB()
