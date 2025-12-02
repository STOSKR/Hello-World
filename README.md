# CS-Tracker

Sistema de arbitraje automatizado para skins de CS2. Detecta oportunidades de compra en BUFF163 y venta en Steam.

## Características

- ✅ **Scraping paralelo** con 2 workers concurrentes por defecto
- ✅ **Almacenamiento asíncrono** - guarda items en BD mientras scrapea
- ✅ **Cálculo automático de ROI**: `((steam_price * 0.87) / buff_price) - 1`
- ✅ **Conversión CNY → EUR** (tasa: 1 EUR = 8.2 CNY)
- ✅ **Filtros de liquidez** (mínimo 20 listings en ambas plataformas)
- ✅ **Registro de items descartados** con motivo específico
- ✅ **Exportación a JSON** ordenado por rentabilidad
- ✅ **Almacenamiento en Supabase** (solo items válidos, incremental)

## Stack Tecnológico

**Core**: Python 3.13+ • Playwright (scraping) • Pydantic 2.x (validación)

**Storage**: Supabase (PostgreSQL) • JSON local

**Arquitectura**: Clean Architecture • Dict-based intermediate data

## Quick Start

```bash
# 1. Clonar repositorio
git clone https://github.com/STOSKR/Cs-Tracker.git
cd Cs-Tracker

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt
playwright install chromium

# 4. Configurar Supabase (opcional)
# - Crea cuenta en supabase.com
# - Ejecuta config/schema.sql en SQL Editor
# - Copia .env.example a .env y añade credenciales

# 5. Ejecutar scraper (por defecto: 200 items, 2 workers, async storage)
python -m app scrape
```

## Uso

### Comandos Básicos

```bash
# Scrapear items (por defecto: 50 items, 2 workers, async storage)
python -m app scrape

# Límite personalizado
python -m app scrape --limit 20

# Modo headless (sin ventana)
python -m app scrape --headless

# Cambiar número de workers concurrentes (1-5)
python -m app scrape --concurrent 3

# Desactivar almacenamiento asíncrono (guarda todo al final)
python -m app scrape --no-async-storage

# Sin guardar en Supabase
python -m app scrape --no-db

# Archivo de salida personalizado
python -m app scrape --limit 10 --output results/my_data.json

# Añadir exclusiones personalizadas
python -m app scrape --exclude "Graffiti |" --exclude "Souvenir"

# Verificar conexión a base de datos
python -m app health
```

### Exclusiones por Defecto

El scraper **automáticamente descarta**:
- Stickers
- Music Kits  
- Items sin `|` (cases, keys, pins)
- Charms (`Charm |`)
- Patches (`Patch |`)

### Validaciones de Liquidez

Items **descartados** si:
- Menos de 20 listings en BUFF
- Menos de 20 listings en Steam
- Falla extracción de datos
- Falla cálculo de rentabilidad

**Items descartados se registran en JSON local con motivo**, pero **NO se guardan en Supabase**.

## Estructura del Proyecto

```
Cs-Tracker/
├── app/                    # Aplicación principal (Clean Architecture)
│   ├── core/              # Configuración y logging
│   │   ├── config.py      # Settings con pydantic-settings
│   │   └── logger.py      # structlog con colores
│   ├── domain/            # Lógica de negocio
│   │   ├── models.py      # ScrapedItem (Pydantic) - SOLO validación final
│   │   └── rules.py       # Cálculos: ROI, profit, fees, conversión CNY→EUR
│   ├── services/          # Servicios e infraestructura
│   │   ├── scraping.py    # Orquestación producer-consumer
│   │   ├── storage.py     # Supabase async
│   │   ├── filters/       # FilterManager (web UI filters)
│   │   ├── extractors/    # Extractores especializados
│   │   │   ├── item_extractor.py         # Tabla de SteamDT
│   │   │   ├── detailed_item_extractor.py # Orquestador BUFF+Steam
│   │   │   ├── buff_extractor.py          # Scraping BUFF (CNY)
│   │   │   └── steam_extractor.py         # Scraping Steam (EUR/CNY)
│   │   └── utils/         # BrowserManager, FileSaver
│   └── main.py            # CLI con Click
├── config/
│   ├── schema.sql         # Schema PostgreSQL para Supabase
│   └── scraper_config.json # Configuración de delays anti-ban
├── data/                  # JSONs de salida y screenshots
├── logs/                  # scraper.log (rotating 10MB)
├── src/                   # ⚠️ LEGACY - Implementación antigua (BORRAR)
├── examples/              # ⚠️ Scripts de prueba obsoletos (BORRAR)
├── .github/               # ⚠️ GitHub Actions obsoleto (BORRAR)
├── requirements.txt       # Dependencias Python
├── README.md             # Esta guía
├── MASTER_PLAN.md        # ⚠️ Roadmap antiguo (REVISAR/ACTUALIZAR)
└── .env.example          # Template variables de entorno
```

## Arquitectura de Datos

### Flujo de Información

```
1. ItemExtractor (tabla SteamDT)
   └─> Dict: {item_name, quality, stattrak, urls}

2. DetailedItemExtractor (orquestador)
   ├─> BuffExtractor (precios BUFF en CNY)
   │   └─> Dict: {avg_price, selling_items, ...}
   └─> SteamExtractor (precios Steam en EUR/CNY)
       └─> Dict: {avg_price, selling_items, ...}

3. Cálculos (domain/rules.py)
   ├─> convert_cny_to_eur(price_cny) → EUR
   ├─> calculate_profit(buff_eur, steam_eur) → profit con fees
   └─> calculate_roi(buff_eur, steam_eur) → ROI %

4. Validación Final (SOLO aquí se usa Pydantic)
   └─> ScrapedItem(**dict_data) → Objeto validado

5. Salida
   ├─> JSON local: items válidos + descartados (con motivo)
   └─> Supabase: SOLO items válidos
```

### Filosofía: Dict-Based Intermediate Data

**❓ Por qué usamos Dicts en lugar de Pydantic en cada paso?**

```python
# ✅ CORRECTO: Flexibilidad para scraping
def extract_buff_data(page) -> Dict:
    # La web puede cambiar, dicts se adaptan fácilmente
    return {
        "avg_price": 184.0,  # CNY
        "selling_items": [...],
        "extra_field": "nuevo"  # Fácil añadir sin romper nada
    }

# ❌ INCORRECTO: Rigidez con Pydantic
class BuffData(BaseModel):
    avg_price: float
    selling_items: List[Dict]
    # Si la web añade un campo, hay que actualizar el modelo
    # Si falta un campo, rompe todo el flujo
```

**Ventajas:**
- **Flexibilidad**: Agregar/quitar campos sin tocar modelos
- **Performance**: Sin overhead de validación en cada paso
- **Mantenibilidad**: Menos código, menos bugs
- **Scraping-friendly**: La estructura web cambia constantemente

**Pydantic solo al final** asegura que los datos guardados son correctos sin romper el flujo intermedio.

## Formato de Salida

### JSON Local (`data/scraper_results_*.json`)

```json
[
  {
    "item_name": "AWP | Chrome Cannon",
    "quality": "Field-Tested",
    "stattrak": false,
    "profitability": 40.99,
    "profit_eur": 10.54,
    "buff_url": "https://buff.163.com/goods/956557",
    "buff_price_eur": 25.09,
    "steam_url": "https://steamcommunity.com/...",
    "steam_price_eur": 40.95,
    "scraped_at": "2025/12/02-10:21",
    "source": "steamdt_hanging"
  },
  {
    "item_name": "P250 | Visions",
    "quality": "Factory New",
    "stattrak": false,
    "discarded": true,
    "discard_reason": "Low BUFF volume (12/20)"
  }
]
```

**Orden**: Items válidos por rentabilidad (mejor→peor), luego descartados al final.

### Supabase (Tabla `scraped_items`)

**Campos guardados** (SOLO items válidos):
- `item_name`, `quality`, `stattrak`
- `profitability` (ROI en %)
- `profit_eur` (beneficio neto con comisiones)
- `buff_url`, `buff_price_eur`
- `steam_url`, `steam_price_eur`
- `scraped_at` (formato: `YYYY/MM/DD-HH:MM`)
- `source` (siempre `"steamdt_hanging"`)

**Items descartados NO se guardan en Supabase**, solo en JSON local.

## Cálculos de Rentabilidad

### Comisiones Aplicadas

- **BUFF**: 2.5% al comprar
- **Steam**: 13% al vender (5% Steam + 8% publisher)

### Fórmula de ROI

```python
# Fórmula simplificada de ROI
# ((steam_price * 0.87) / buff_price) - 1

# 1. Conversión de moneda
buff_price_eur = buff_price_cny / 8.2  # CNY → EUR

# 2. Aplicar fee de Steam (13%)
steam_net = steam_price_eur * 0.87  # 87% después de comisión

# 3. Calcular ROI
roi = (steam_net / buff_price_eur) - 1
roi_percent = roi * 100
```

### Ejemplo Real

```
Item: AWP | Chrome Cannon (Field-Tested)
BUFF: ¥206.00 CNY → €25.12 EUR
Steam: €40.95 EUR

Cálculo:
- Steam neto: €40.95 × 0.87 = €35.63 (después de 13% fee)
- ROI: (€35.63 / €25.12) - 1 = 0.4185
- ROI %: 41.85%
```

## Archivos y Carpetas a Borrar

### ⚠️ OBSOLETOS - Pueden Borrarse

```
├── src/                   # Implementación antigua completa
├── examples/              # Scripts de prueba viejos
├── .github/workflows/     # CI/CD obsoleto
├── pasos.md              # Documentación vieja
├── SETUP.md              # Guía antigua (info duplicada en README)
├── set_anti_ban_mode.py  # Script standalone obsoleto
└── data/screenshots/     # Screenshots de debug (opcional limpiar)
```

### ✅ MANTENER

```
├── app/                  # Implementación actual (Clean Architecture)
├── config/               # Schema SQL y configuración
├── data/*.json          # Resultados del scraper
├── logs/scraper.log     # Logs rotatorios
├── requirements.txt     # Dependencias
├── README.md           # Esta guía
├── MASTER_PLAN.md      # Roadmap (revisar y actualizar)
└── .env.example        # Template de configuración
```

### Comandos para Limpiar

```bash
# Windows PowerShell
Remove-Item -Recurse -Force src, examples, .github, pasos.md, SETUP.md, set_anti_ban_mode.py

# Linux/Mac
rm -rf src examples .github pasos.md SETUP.md set_anti_ban_mode.py
```

## Logs y Debugging

### Ver Logs

```bash
# Logs en consola con colores
python -m app scrape --limit 5

# Logs guardados (sin colores ANSI)
cat logs/scraper.log
```

### Formato de Logs

```
2025-12-02 10:21:15 [info] processing_item name="AWP | Chrome Cannon"
2025-12-02 10:21:18 [info] prices_scraped buff_cny="¥206.00" buff_eur="€25.12" steam_eur="€40.95"
2025-12-02 10:21:18 [info] item_scraped worker_id=0 name="AWP | Chrome Cannon" quality="Field-Tested" summary="€25.12 → €40.95 (€9.88 - 38.37%)"
2025-12-02 10:21:25 [info] item_discarded worker_id=0 name="P250 | Visions" quality="Factory New" reason="Low BUFF volume (12/20)"
```

### Rotación de Logs

- Archivo: `logs/scraper.log`
- Tamaño máximo: 10 MB
- Backups: 30 archivos (`scraper.log.1`, `scraper.log.2`, ...)

## Configuración Avanzada

### Variables de Entorno (`.env`)

```bash
# Supabase (opcional)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxx...

# Scraper (config/scraper_config.json tiene prioridad)
SCRAPER_HEADLESS=false        # true para modo invisible
MAX_CONCURRENT=2              # Workers paralelos (default: 2)
DELAY_BETWEEN_ITEMS=1000      # ms entre items (optimizado)
RANDOM_DELAY_MIN=500          # ms delay aleatorio mínimo
RANDOM_DELAY_MAX=1500         # ms delay aleatorio máximo
```

### Parámetros CLI (sobrescriben configuración)

```bash
# Límite de items (default: 50)
--limit 100

# Workers concurrentes (default: 2, rango: 1-5)
--concurrent 3

# Modo de almacenamiento
--no-async-storage  # Desactiva async storage (guarda al final)
                    # Por defecto: async storage ACTIVADO

# Modo de browser
--headless          # Sin ventana visible
--visible           # Con ventana (default)
```

### Ajustar Volumen Mínimo

Editar `app/services/extractors/detailed_item_extractor.py`:

```python
# Línea ~77
if buff_volume < 20:  # Cambiar 20 por tu valor
    ...

# Línea ~89  
if steam_volume < 20:  # Cambiar 20 por tu valor
    ...
```

### Cambiar Tasa de Conversión CNY→EUR

Editar `app/domain/rules.py`:

```python
# Línea 11
CNY_TO_EUR = 8.2  # Actualizar según tasa actual
```

## Troubleshooting

### Error: `ERR_ABORTED` en BUFF

**Causa**: BUFF detecta actividad de bot o requests demasiado rápidos.

**Solución**: 
- Reducir workers: `--concurrent 1`
- Aumentar delays en `config/scraper_config.json`
- El sistema tiene retry automático con delays aleatorios 8-15s

### Items Descartados: "Low volume"

**Normal**: Items con poca liquidez se descartan automáticamente.

**Ver motivos**: Revisa el JSON local en la sección de items descartados al final.

### No se guardan datos en Supabase

1. Verificar credenciales en `.env`
2. Ejecutar `python -m app health` para testear conexión
3. Verificar schema ejecutado en Supabase SQL Editor

### Logs no tienen colores

**En consola**: Los colores deberían aparecer automáticamente.

**En archivos**: Por diseño, `logs/scraper.log` no tiene colores ANSI para facilitar lectura.

## Contribuir

Este es un proyecto educativo. Pull requests bienvenidos para:
- Mejoras en extractores (BUFF/Steam cambian estructura)
- Nuevos filtros de validación
- Optimizaciones de performance
- Correcciones de bugs

## Licencia

MIT License

**Disclaimer**: Este proyecto es solo para fines educativos. No garantiza rentabilidad. El trading de skins conlleva riesgos.

## Links Útiles

- [Supabase Dashboard](https://app.supabase.com)
- [SteamDT Hanging Page](https://steamdt.com/en/hanging)
- [BUFF163 Marketplace](https://buff.163.com)
- [Playwright Docs](https://playwright.dev/python/)
- [Pydantic Docs](https://docs.pydantic.dev/)

---

**Proyecto Educativo** | Clean Architecture + Web Scraping | MIT License
