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

**Clean Architecture** con separación de responsabilidades:
- **Domain**: Lógica de negocio pura (sin dependencias externas)
- **Services**: Implementaciones concretas (I/O, APIs, DB)
- **Graph**: Orquestación de flujos (LangGraph nodes)

### Principios de Código Limpio

**1. Tipado Estricto**
```python
# ✅ Correcto: Type hints explícitos
async def get_prices(skin: str) -> MarketData:
    return MarketData(steam_price=10.5, buff_price=9.8)

# ❌ Incorrecto: Sin tipos
async def get_prices(skin):
    return {"steam": 10.5, "buff": 9.8}
```

**2. Asincronía Nativa**
```python
# ✅ Correcto: async/await para I/O
async def fetch_data(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

# ❌ Incorrecto: Operaciones bloqueantes
def fetch_data(url: str) -> dict:
    response = requests.get(url)  # Bloquea el event loop
    time.sleep(1)  # Nunca usar sleep en código async
```

**3. Single Responsibility (Nodos Ligeros)**
```python
# ✅ Correcto: Nodo delega lógica
async def scout_node(state: AgentState) -> AgentState:
    """Nodo responsable solo de orquestar."""
    data = await scraping_service.get_prices(state["target_skin"])
    return {**state, "market_data": data}

# ❌ Incorrecto: Lógica compleja en el nodo
async def scout_node(state: AgentState) -> AgentState:
    async with httpx.AsyncClient() as client:
        # 50 líneas de scraping...
        # Parsing HTML...
        # Cálculos complejos...
```

**4. Inyección de Dependencias**
```python
# ✅ Correcto: Dependencias inyectadas
class ScrapingService:
    def __init__(self, http_client: httpx.AsyncClient, config: Settings):
        self.client = http_client
        self.config = config

# ❌ Incorrecto: Dependencias hardcodeadas
class ScrapingService:
    def __init__(self):
        self.client = httpx.AsyncClient()  # Difícil de testear
        self.api_key = os.getenv("KEY")  # Config dispersa
```

**5. Manejo de Errores Sin Crashes**
```python
# ✅ Correcto: Errores en el estado
async def analyst_node(state: AgentState) -> AgentState:
    try:
        result = await ai_service.analyze(state["data"])
        return {**state, "analysis": result}
    except Exception as e:
        return {**state, "errors": [f"Analysis failed: {str(e)}"]}

# ❌ Incorrecto: Dejar que el grafo crashee
async def analyst_node(state: AgentState) -> AgentState:
    result = await ai_service.analyze(state["data"])  # Puede fallar
    return {**state, "analysis": result}
```

**6. Modelos Pydantic (No Dicts)**
```python
# ✅ Correcto: Pydantic con validación
from pydantic import BaseModel, Field

class MarketData(BaseModel):
    skin_name: str
    steam_price: float = Field(..., gt=0)
    buff_price: float = Field(..., gt=0)
    timestamp: datetime

# ❌ Incorrecto: Dicts sin validar
def process_data(data: dict) -> dict:
    return {
        "price": data["steam"] - data["buff"],  # ¿Qué si no existe?
    }
```

**7. Configuración Centralizada**
```python
# ✅ Correcto: Settings con pydantic-settings
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    supabase_url: str
    gemini_api_key: str
    
    class Config:
        env_file = ".env"

settings = Settings()

# ❌ Incorrecto: os.getenv disperso
api_key = os.getenv("GEMINI_KEY")  # En cada archivo
```

### Ejemplos de Implementación

```python
# Nodo LangGraph (Clean)
async def scout_node(state: AgentState) -> AgentState:
    """Extrae precios de mercados."""
    try:
        data = await scraping_service.get_prices(state["target_skin"])
        return {**state, "market_data": data}
    except Exception as e:
        return {**state, "errors": [f"Scraping: {str(e)}"]}

# Agente Pydantic-AI (Clean)
analyst = Agent(
    'gemini-flash',
    result_type=RiskAnalysis,
    system_prompt="Eres un analista financiero experto..."
)

async def analyst_node(state: AgentState) -> AgentState:
    """Valida riesgo con IA."""
    result = await analyst.run(f"Analiza: {state['spread']}")
    return {**state, "risk_assessment": result.data}
```

## Licencia

MIT License. Proyecto educativo - TFM.

**Disclaimer**: No garantiza rentabilidad. Solo fines educativos.

## Links

**Docs**: [SETUP.md](./SETUP.md) • [MASTER_PLAN.md](./MASTER_PLAN.md) • [Schema SQL](./config/schema.sql)

**Tech**: [Supabase](https://supabase.com/docs) • [Playwright](https://playwright.dev/python/) • [LangGraph](https://langchain-ai.github.io/langgraph/) • [Pydantic-AI](https://ai.pydantic.dev/)

---

**Trabajo Fin de Máster** - Sistema de Arbitraje con IA Agéntica | MIT License
