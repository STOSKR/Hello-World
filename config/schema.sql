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
