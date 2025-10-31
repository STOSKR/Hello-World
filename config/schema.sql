-- Schema SQL para Supabase
-- Ejecuta esto en el SQL Editor de tu proyecto Supabase
-- Dashboard -> SQL Editor -> New Query

-- Tabla principal para almacenar items scrapeados
CREATE TABLE IF NOT EXISTS scraped_items (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL DEFAULT 'steamdt_hanging',
    scraped_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Campos específicos del item
    item_name TEXT,
    buy_price TEXT,
    sell_price TEXT,
    profit TEXT,
    
    -- Datos raw completos en formato JSON
    raw_data JSONB,
    
    -- Índices para búsquedas rápidas
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_scraped_items_scraped_at ON scraped_items(scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_scraped_items_item_name ON scraped_items(item_name);
CREATE INDEX IF NOT EXISTS idx_scraped_items_source ON scraped_items(source);
CREATE INDEX IF NOT EXISTS idx_scraped_items_raw_data ON scraped_items USING GIN(raw_data);

-- Comentarios para documentación
COMMENT ON TABLE scraped_items IS 'Tabla principal para almacenar datos scrapeados de SteamDT';
COMMENT ON COLUMN scraped_items.raw_data IS 'Datos completos del item en formato JSON';

-- Vista para obtener el último precio de cada item
CREATE OR REPLACE VIEW latest_items AS
SELECT DISTINCT ON (item_name)
    id,
    item_name,
    buy_price,
    sell_price,
    profit,
    scraped_at,
    raw_data
FROM scraped_items
WHERE item_name IS NOT NULL
ORDER BY item_name, scraped_at DESC;

-- Función para obtener cambios de precio
CREATE OR REPLACE FUNCTION get_price_changes(hours_ago INTEGER DEFAULT 24)
RETURNS TABLE (
    item_name TEXT,
    old_price TEXT,
    new_price TEXT,
    price_diff TEXT,
    time_diff INTERVAL
) AS $$
BEGIN
    RETURN QUERY
    WITH recent AS (
        SELECT DISTINCT ON (s.item_name)
            s.item_name as name,
            s.buy_price,
            s.scraped_at
        FROM scraped_items s
        WHERE s.scraped_at >= NOW() - INTERVAL '1 hour' * hours_ago
            AND s.item_name IS NOT NULL
        ORDER BY s.item_name, s.scraped_at DESC
    ),
    older AS (
        SELECT DISTINCT ON (s.item_name)
            s.item_name as name,
            s.buy_price,
            s.scraped_at
        FROM scraped_items s
        WHERE s.scraped_at < NOW() - INTERVAL '1 hour' * hours_ago
            AND s.item_name IS NOT NULL
        ORDER BY s.item_name, s.scraped_at DESC
    )
    SELECT
        recent.name,
        older.buy_price,
        recent.buy_price,
        (recent.buy_price::TEXT),  -- Aquí puedes añadir lógica de cálculo
        recent.scraped_at - older.scraped_at
    FROM recent
    LEFT JOIN older ON recent.name = older.name
    WHERE older.buy_price IS NOT NULL
        AND recent.buy_price != older.buy_price;
END;
$$ LANGUAGE plpgsql;

-- Habilitar Row Level Security (RLS) - Opcional pero recomendado
ALTER TABLE scraped_items ENABLE ROW LEVEL SECURITY;

-- Política para permitir lectura pública (ajusta según tus necesidades)
CREATE POLICY "Allow public read access"
    ON scraped_items
    FOR SELECT
    USING (true);

-- Política para permitir inserción solo con service_role
CREATE POLICY "Allow insert with service role"
    ON scraped_items
    FOR INSERT
    WITH CHECK (true);

-- Nota: Para desarrollo, puedes desactivar RLS temporalmente:
-- ALTER TABLE scraped_items DISABLE ROW LEVEL SECURITY;
