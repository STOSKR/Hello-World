-- Schema SQL para Supabase
-- Ejecuta esto en el SQL Editor de tu proyecto Supabase
-- Dashboard -> SQL Editor -> New Query

-- Tabla principal para almacenar items scrapeados
CREATE TABLE IF NOT EXISTS scraped_items (
    id BIGSERIAL PRIMARY KEY,
    
    -- Campos específicos del item
    item_name TEXT NOT NULL,
    quality VARCHAR(50),
    stattrak BOOLEAN DEFAULT FALSE,
    profitability NUMERIC(10, 2),
    profit_eur NUMERIC(10, 2),
    buff_url TEXT,
    buff_price_eur NUMERIC(10, 2),
    steam_url TEXT,
    steam_price_eur NUMERIC(10, 2),
    scraped_at VARCHAR(20) NOT NULL,
    source VARCHAR(100) NOT NULL DEFAULT 'steamdt_hanging',
    
    -- Timestamp de creación
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_scraped_items_item_name ON scraped_items(item_name);
CREATE INDEX IF NOT EXISTS idx_scraped_items_profitability ON scraped_items(profitability DESC);
CREATE INDEX IF NOT EXISTS idx_scraped_items_source ON scraped_items(source);
CREATE INDEX IF NOT EXISTS idx_scraped_items_created_at ON scraped_items(created_at DESC);

-- Comentarios para documentación
COMMENT ON TABLE scraped_items IS 'Tabla principal para almacenar datos scrapeados de SteamDT';
COMMENT ON COLUMN scraped_items.profitability IS 'ROI en porcentaje';
COMMENT ON COLUMN scraped_items.profit_eur IS 'Beneficio neto en EUR después de comisiones';

-- Vista para obtener el último precio de cada item
CREATE OR REPLACE VIEW latest_items AS
SELECT DISTINCT ON (item_name, quality)
    id,
    item_name,
    quality,
    stattrak,
    profitability,
    profit_eur,
    buff_url,
    buff_price_eur,
    steam_url,
    steam_price_eur,
    scraped_at,
    source
FROM scraped_items
WHERE item_name IS NOT NULL
ORDER BY item_name, quality, created_at DESC;

-- Vista para obtener mejores oportunidades (ROI > 20%)
CREATE OR REPLACE VIEW best_opportunities AS
SELECT 
    item_name,
    quality,
    stattrak,
    profitability,
    profit_eur,
    buff_price_eur,
    steam_price_eur,
    scraped_at
FROM scraped_items
WHERE profitability > 20
ORDER BY profitability DESC
LIMIT 50;

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

-- ============================================================================
-- HISTORIAL DE PRECIOS
-- ============================================================================

-- Vista: Historial completo de un item específico
CREATE OR REPLACE VIEW price_history AS
SELECT 
    item_name,
    quality,
    stattrak,
    buff_price_eur,
    steam_price_eur,
    profitability,
    profit_eur,
    created_at,
    scraped_at
FROM scraped_items
ORDER BY item_name, quality, created_at DESC;

-- Vista: Evolución de precios por día (promedio diario)
CREATE OR REPLACE VIEW daily_price_trends AS
SELECT 
    item_name,
    quality,
    stattrak,
    DATE(created_at) as date,
    AVG(buff_price_eur) as avg_buff_price,
    AVG(steam_price_eur) as avg_steam_price,
    AVG(profitability) as avg_roi,
    MIN(buff_price_eur) as min_buff_price,
    MAX(buff_price_eur) as max_buff_price,
    COUNT(*) as num_samples
FROM scraped_items
WHERE item_name IS NOT NULL
GROUP BY item_name, quality, stattrak, DATE(created_at)
ORDER BY item_name, quality, date DESC;

-- Vista: Últimos 7 días de un item
CREATE OR REPLACE VIEW price_history_7d AS
SELECT 
    item_name,
    quality,
    stattrak,
    buff_price_eur,
    steam_price_eur,
    profitability,
    created_at
FROM scraped_items
WHERE created_at >= NOW() - INTERVAL '7 days'
ORDER BY item_name, quality, created_at DESC;

-- Vista: Items con mayor volatilidad (cambios de precio)
CREATE OR REPLACE VIEW volatile_items AS
SELECT 
    item_name,
    quality,
    stattrak,
    MAX(buff_price_eur) - MIN(buff_price_eur) as price_range,
    STDDEV(buff_price_eur) as price_stddev,
    AVG(buff_price_eur) as avg_price,
    COUNT(*) as num_records
FROM scraped_items
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY item_name, quality, stattrak
HAVING COUNT(*) >= 5
ORDER BY price_stddev DESC;

-- Vista: Comparación de precio actual vs precio hace 24h
CREATE OR REPLACE VIEW price_changes_24h AS
WITH recent AS (
    SELECT DISTINCT ON (item_name, quality)
        item_name,
        quality,
        stattrak,
        buff_price_eur as current_buff_price,
        steam_price_eur as current_steam_price,
        profitability as current_roi,
        created_at as current_time
    FROM scraped_items
    WHERE created_at >= NOW() - INTERVAL '2 hours'
    ORDER BY item_name, quality, created_at DESC
),
yesterday AS (
    SELECT DISTINCT ON (item_name, quality)
        item_name,
        quality,
        buff_price_eur as old_buff_price,
        steam_price_eur as old_steam_price,
        profitability as old_roi
    FROM scraped_items
    WHERE created_at BETWEEN NOW() - INTERVAL '26 hours' AND NOW() - INTERVAL '22 hours'
    ORDER BY item_name, quality, created_at DESC
)
SELECT 
    r.item_name,
    r.quality,
    r.stattrak,
    r.current_buff_price,
    y.old_buff_price,
    r.current_buff_price - y.old_buff_price as buff_price_change,
    ROUND(((r.current_buff_price - y.old_buff_price) / y.old_buff_price * 100)::numeric, 2) as buff_change_percent,
    r.current_steam_price,
    y.old_steam_price,
    r.current_roi,
    y.old_roi,
    r.current_time
FROM recent r
JOIN yesterday y ON r.item_name = y.item_name AND r.quality = y.quality
WHERE y.old_buff_price > 0
ORDER BY ABS(buff_change_percent) DESC;
