# CS-Tracker - Clean Architecture Version

Nueva implementación siguiendo principios SOLID y Clean Architecture.

## Estructura

```
app/
├── core/           # Configuración y logging centralizado
├── domain/         # Modelos Pydantic y reglas de negocio puras
├── services/       # Implementaciones (scraping, storage)
├── graph/          # LangGraph nodes y agents (Fases 3-4)
└── main.py         # CLI con comandos
```

## Instalación

```bash
# Instalar dependencias nuevas
pip install -r requirements.txt

# Instalar Playwright browsers
playwright install chromium
```

## Uso

### 1. Solo Scraper (Sin Agentes)

```bash
# Scraping básico (headless, 1 item a la vez, excluye "Charm |" por defecto)
python -m app.main scrape

# Scraping limitado a 10 items
python -m app.main scrape --limit 10

# Visible + 2 items concurrentes + límite de 5
python -m app.main scrape --visible --concurrent 2 --limit 5

# Excluir múltiples prefijos
python -m app.main scrape --exclude "Charm |" --exclude "Graffiti |" --exclude "Sticker |"

# Guardar a base de datos
python -m app.main scrape --save-db

# Guardar a archivo JSON
python -m app.main scrape --output data/results.json

# Todo junto: visible, 2 concurrentes, 10 items, excluir Charms, guardar
python -m app.main scrape --visible --concurrent 2 --limit 10 --save-db --output data/latest.json
```

### 2. Otros Comandos

```bash
# Verificar configuración
python -m app.main test-config

# Ver historial de un item
python -m app.main history --item "AK-47 | Redline"

# Verificar conexión BD
python -m app.main health
```

## Ventajas vs `src/`

### ✅ Código Legacy (`src/`)
- Funcional y probado en producción
- GitHub Actions configurado
- Scraping robusto con anti-ban

### ✅ Nueva Arquitectura (`app/`)
- **Tipado estricto**: Pydantic models con validación
- **Logging estructurado**: JSON sin emojis
- **Inyección de dependencias**: Testeable y desacoplado
- **Async real**: Scraping paralelo de Buff + Steam por item
- **Configuración centralizada**: pydantic-settings
- **CLI moderna**: Click con comandos claros
- **Patrón Productor-Consumidor**: Lectura de tabla y scraping en paralelo
- **Filtrado automático**: Excluye "Charm |" y otros prefijos
- **Límite configurable**: Scrapea solo N items (testing rápido)

## Diferencias Clave

### Scraping Paralelo Multinivel

**Legacy** (`src/scraper.py`):
```python
# 1. Lee TODA la tabla secuencialmente
items = scrape_table()  # Espera a cargar todo

# 2. Procesa items secuencialmente
for item in items:
    buff_price = await scrape_buff(url)    # Espera
    steam_price = await scrape_steam(url)  # Espera
```

**Clean** (`app/services/scraping.py`):
```python
# PRODUCTOR: Lee tabla y filtra en background
async def producer():
    for item in scrape_table():
        if not item.startswith("Charm |"):  # Filtro
            await queue.put(item)

# CONSUMIDOR: Scrapea en paralelo mientras se lee la tabla
async def consumer():
    item = await queue.get()
    # Buff y Steam en paralelo por item
    buff, steam = await asyncio.gather(
        scrape_buff(url),
        scrape_steam(url)
    )

# 3x más rápido: tabla + buff + steam simultáneos
```

### Logging

**Legacy**:
```python
logger.info("🚀 Iniciando scraping...")
logger.error("❌ Error en BUFF")
```

**Clean**:
```json
{"timestamp": "2024-12-01T20:10:12Z", "level": "info", "event": "scraping_started", "url": "...", "max_concurrent": 2}
{"timestamp": "2024-12-01T20:10:15Z", "level": "error", "event": "buff_scrape_failed", "error": "timeout"}
```

### Configuración

**Legacy**: Mezcla de JSON + .env + argparse

**Clean**: Centralizado con pydantic-settings
```python
from app.core.config import settings

print(settings.max_concurrent)  # Type-safe
print(settings.supabase_url)    # Validado automáticamente
```

## Migración Gradual

Ambos sistemas coexisten:
- `src/` sigue funcional para GitHub Actions
- `app/` es la base para Fases 2-4 (LangGraph, IA)

## Próximos Pasos (Roadmap)

- [ ] Fase 2: Completar extractores específicos (adaptar selectores reales)
- [ ] Fase 3: Implementar LangGraph (Scout → Math nodes)
- [ ] Fase 4: Integrar Pydantic-AI (validación de riesgo con LLMs)

## Testing

```bash
# Instalar pytest
pip install pytest pytest-asyncio

# Crear tests/test_domain.py
pytest tests/ -v
```

## Notas

- **Scraping paralelo**: Buff + Steam se scrapean simultáneamente por item
- **Anti-ban**: Configuración heredada de `config/scraper_config.json`
- **Type safety**: `mypy app/` debería pasar sin errores
- **Logs**: Se guardan en `logs/scraper_YYYYMMDD_HHMMSS.log` en formato JSON

---

**Compatibilidad**: Python 3.11+ requerido
