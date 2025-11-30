# CS-Tracker

Sistema de arbitraje automatizado para skins de CS2 con IA. **Trabajo Fin de Máster**.

## Objetivos

Sistema inteligente que **detecta**, **analiza** y **ejecuta** oportunidades de arbitraje entre Steam y Buff163 usando **LangGraph** + **Pydantic-AI**.

1. Detectar diferencias de precio en tiempo real
2. Filtrar oportunidades rentables (ROI > X%)
3. Validar riesgo con LLMs (Gemini/GPT)
4. Ejecutar operaciones autónomamente

## Estado Actual

**Fase 1** (Implementado):
- Scraping automático cada 6 horas (GitHub Actions)
- Base de datos Supabase (PostgreSQL)
- Historial completo de precios
- 100% gratuito

**Fases 2-4** (Roadmap):
- Orquestación con LangGraph
- Validación IA con Pydantic-AI
- Trading autónomo

## Stack

**Implementado**: Python 3.11+ • Playwright • Supabase • GitHub Actions

**Roadmap**: LangGraph • Pydantic-AI • Gemini/GPT • MongoDB

## Quick Start

```bash
# 1. Clonar
git clone https://github.com/STOSKR/Cs-Tracker.git
cd Cs-Tracker

# 2. Instalar
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

# 3. Configurar Supabase
# - Crea cuenta en supabase.com
# - Ejecuta config/schema.sql en SQL Editor
# - Copia URL y API key

# 4. Variables de entorno
cp .env.example .env
# Edita .env con tus credenciales

# 5. Probar
python src/main.py
```

### GitHub Actions

Añade secrets en tu repo (Settings → Secrets):
- `SUPABASE_URL`
- `SUPABASE_KEY`

El scraper se ejecutará automáticamente cada 6 horas.

**Guía detallada**: [SETUP.md](./SETUP.md)

## Estructura

```
src/          # Fase 1 (scraping base)
app/          # Fases 2-4 (sistema agéntico)
  ├── core/       # Config, logging
  ├── domain/     # Models, state, rules
  ├── services/   # Scraping, cálculos, storage
  └── graph/      # LangGraph nodes + agents
config/       # SQL schema
.github/      # CI/CD workflows
```

## Uso

```python
from src.database import SupabaseDB

db = SupabaseDB()
items = db.get_latest_items(limit=100)
history = db.get_item_history("AK-47 | Redline")
```

```sql
-- SQL Editor en Supabase
SELECT * FROM latest_items;
SELECT * FROM get_price_changes(24);
```

## Roadmap

| Fase | Estado | Objetivo |
|------|--------|----------|
| **1. Base** | Completado | Scraping + Supabase + GitHub Actions |
| **2. Grafo** | En Progreso | LangGraph (Scout → Math nodes) |
| **3. IA** | Pendiente | Pydantic-AI (Analyst agent) |
| **4. Producción** | Pendiente | MongoDB + Trading autónomo |

Detalles: [MASTER_PLAN.md](./MASTER_PLAN.md)

## Arquitectura (TFM)

**Clean Architecture** con:
- Tipado estricto (`async/await`)
- Nodos ligeros (lógica en `services/`)
- Inyección de dependencias
- Tests con pytest

```python
# Ejemplo: Nodo LangGraph
async def scout_node(state: AgentState) -> AgentState:
    data = await scraping_service.get_prices(state["target_skin"])
    return {**state, "market_data": data}
```

```python
# Ejemplo: Agente Pydantic-AI
analyst = Agent('gemini-flash', result_type=RiskAnalysis)
result = await analyst.run(f"Analiza: {state['spread']}")
```

## Licencia

MIT License. Proyecto educativo - TFM.

**Disclaimer**: No garantiza rentabilidad. Solo fines educativos.

## Links

**Docs**: [SETUP.md](./SETUP.md) • [MASTER_PLAN.md](./MASTER_PLAN.md) • [Schema SQL](./config/schema.sql)

**Tech**: [Supabase](https://supabase.com/docs) • [Playwright](https://playwright.dev/python/) • [LangGraph](https://langchain-ai.github.io/langgraph/) • [Pydantic-AI](https://ai.pydantic.dev/)

---

**Trabajo Fin de Máster** - Sistema de Arbitraje con IA Agéntica | MIT License
