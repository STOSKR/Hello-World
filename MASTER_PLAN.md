# 🎓 MASTER PLAN - CS2 Agentic Graph System

**Trabajo Fin de Máster**: Sistema de Arbitraje Financiero Automatizado con IA Agéntica

---

## 📌 Estado del Proyecto

**✅ Fase 1 COMPLETADA** - Sistema de scraping funcional en producción:
- Scraping automático con Playwright (headless/visible)
- Base de datos Supabase (PostgreSQL) con timestamps timezone-aware
- GitHub Actions (cada hora en :30 UTC) - repo público con minutos ilimitados
- Sistema anti-ban configurable (2 workers concurrentes por defecto)
- Sesiones persistentes para BUFF/Steam (cookies guardadas como GitHub Secrets)
- ROI corregido: `((steam_price * 0.87) / buff_price) - 1`
- Async storage con worker dedicado para guardar items incrementalmente
- Producer-consumer pattern con Queue para procesamiento concurrente

**✅ Fase 2 COMPLETADA** - Clean Architecture implementada:
- Migración completa de `src/` a `app/` con separación de capas
- Tipado estricto con Pydantic (solo para resultado final)
- Configuración centralizada (JSON como source of truth)
- Logging estructurado con structlog
- Código deduplicado (~400 líneas eliminadas)
- Performance optimizado (delays 1-2.5s vs 5-10s antes)

**⏳ Fases 3-4 PENDIENTES** - IA Agéntica:
- LangGraph para orquestación
- Pydantic-AI para validación con LLMs
- Trading autónomo

---

## 🎯 OBJETIVO

**ROL DE LA IA**: Principal Software Engineer y Arquitecto de IA

**MISIÓN**: Refactorizar el sistema existente (`src/`) a Clean Architecture (`app/`) y extenderlo con:
- **LangGraph**: Orquestación y gestión de estado
- **Pydantic-AI**: Inteligencia artificial con output estructurado

**ESTÁNDAR**: Código de producción, Clean Architecture, Asíncrono y Tipado Estricto

---

## 1. 🌟 Visión y Objetivos

Desarrollar un **pipeline inteligente** donde el dato fluye a través de nodos especializados.

### Objetivos Principales

| # | Objetivo | Estado | Descripción |
|---|----------|--------|-------------|
| 1 | **Detección en Tiempo Real** | ✅ Completado | Scraping de Steam/Buff163 con Playwright cada hora (GitHub Actions) |
| 2 | **Filtrado Matemático** | ✅ Completado | Cálculo de ROI, fees, spread con filtros configurables + async storage |
| 3 | **Validación IA** | ⏳ Pendiente | Validar riesgo usando LLMs (Gemini/GPT) analizando tendencias |
| 4 | **Ejecución Autónoma** | ⏳ Pendiente | Ejecutar operaciones de trading de forma autónoma |

---

## 2. 🛠️ Stack Tecnológico

### ✅ Implementado (Fase 1-2 - `app/`)

| Componente | Tecnología | Uso Actual |
|------------|-----------|------------|
| **Lenguaje** | Python 3.11+ | Async/await nativo, type hints everywhere |
| **Scraping** | Playwright | Navegación headless/visible, anti-detección, session persistence |
| **Base de Datos** | Supabase (PostgreSQL) | Almacenamiento histórico con timestamps timezone-aware (TEXT) |
| **CI/CD** | GitHub Actions | Ejecución automática cada hora (:30 UTC) |
| **Configuración** | pydantic-settings + JSON | Single source of truth (scraper_config.json) |
| **Logging** | structlog | JSON logging sin emojis |
| **CLI** | Click | Comandos: scrape, test-config, history, health |
| **Modelos** | Pydantic | Validación estricta solo para ScrapedItem final |
| **Concurrency** | asyncio.Queue | Producer-consumer con 2 workers + storage worker |

### ⏳ Por Implementar (Fases 3-4)

| Componente | Tecnología | Propósito |
|------------|-----------|----------|
| **Orquestación** | LangGraph | Gestión de estado y flujo cíclico |
| **Agentes IA** | Pydantic-AI | LLMs con output estructurado |
| **Modelos LLM** | Gemini Flash / GPT-4o-mini | Low latency & cost |
| **Cliente HTTP** | httpx (opcional) | Async HTTP/2 para APIs REST |

---

## 3. 🏗️ Arquitectura de Software (Clean Architecture)

**Principio**: El código debe estar desacoplado. Los Nodos del Grafo NO contienen lógica de negocio compleja, solo orquestan llamadas a Servicios.

### Estructura Actual (Fase 1-2 - Clean Architecture Implementada)

```
app/                        # Clean Architecture (COMPLETADA)
├── core/                   # Configuración transversal
│   ├── config.py           # Settings con pydantic-settings (JSON como source of truth)
│   └── logger.py           # Logger JSON estructurado con structlog
├── domain/                 # Lógica Pura (sin I/O)
│   ├── models.py           # ScrapedItem, FilterConfig, AntibanConfig
│   └── rules.py            # Fórmulas (ROI corregido, fees, conversión CNY)
├── services/               # Implementaciones concretas
│   ├── scraping.py         # Producer-consumer con async storage worker
│   ├── storage.py          # Repositorio Supabase async (run_in_executor)
│   ├── extractors/         # Buff, Steam, Item, Detailed extractors
│   ├── filters/            # FilterManager
│   └── utils/              # BrowserManager (con session persistence)
├── graph/                  # LangGraph (Fases 3-4 - PENDIENTE)
│   ├── nodes/              # Scout, Math, Analyst, Trader
│   ├── agents/             # Pydantic-AI agents
│   └── workflow.py         # Compilación del grafo
└── main.py                 # CLI con Click (scrape, test-config, history, health)

config/
├── scraper_config.json     # Single source of truth (headless, workers, delays)
├── sessions/               # Sesiones BUFF/Steam (gitignored, GitHub Secrets en CI)
│   ├── buff_session.json
│   └── steam_session.json
└── schema.sql              # Schema Supabase actualizado

scripts/
└── save_session.py         # Script para guardar cookies localmente

.github/workflows/
└── scraper.yml             # Workflow horario con session loading

### Flujo de Datos

```
ENTRADA → Scout Node → Math Node → Analyst Node → Trader Node → SALIDA
           (Scraping)   (Filtering)   (AI Risk)      (Execution)
```

---

## 4. 📋 Fases de Implementación (Roadmap)

### ✅ FASE 1: Scraping Base y Almacenamiento (COMPLETADA)

**Objetivo**: Sistema funcional de scraping con almacenamiento persistente.

#### ✅ Logros Completados
- ✅ Scraper con Playwright (headless/visible configurable)
- ✅ Integración Supabase para historial de precios
- ✅ Sistema de 6 presets de trading configurables
- ✅ GitHub Actions (ejecución automática cada 6 horas)
- ✅ Anti-ban: concurrencia configurable (1-3 items paralelos)
- ✅ Anti-ban: delays aleatorios entre requests
- ✅ Anti-ban: 4 modos (safe/balanced/fast/stealth)
- ✅ Guardado de progreso parcial en interrupciones
- ✅ Cálculo de fees Steam/Buff, spread, ROI, rentabilidad
- ✅ Extracción de datos detallados (precios, volúmenes, listings)
- ✅ Manejo robusto de errores con logging

#### Artefactos Existentes
- `src/scraper.py`: Scraper principal (330 líneas)
- `src/database.py`: Cliente Supabase
- `src/main.py`: CLI con presets
- `config/scraper_config.json`: Config anti-ban
- `config/preset_configs.json`: Presets trading + anti-ban
- `set_anti_ban_mode.py`: CLI para cambiar modos
- `.github/workflows/`: GitHub Actions configurado

---

### ✅ FASE 2: Migración a Clean Architecture (COMPLETADA Diciembre 2025)

**Objetivo**: Refactorizar código a `app/` siguiendo principios SOLID y optimizar performance.

#### ✅ Logros Completados
- ✅ Arquitectura limpia con separación domain/services/core
- ✅ Configuración centralizada (JSON como source of truth, CLI solo overrides)
- ✅ Logging estructurado con structlog (JSON sin emojis)
- ✅ ROI corregido: `((steam_price * 0.87) / buff_price) - 1`
- ✅ Performance optimizada:
  - Delays: 5-10s → 1-2.5s
  - Timeouts: BUFF 30s→15s, Steam 10s
  - Default workers: 1 → 2 concurrentes
- ✅ Producer-consumer pattern con asyncio.Queue
- ✅ Async storage worker implementado (código existe, no habilitado por defecto)
- ✅ Code deduplication: ~400 líneas eliminadas
  - Unified `scrape_items()` method con `async_storage` parameter
  - Helper `_format_item_display()` para eliminar repetición
- ✅ GitHub Actions optimizado:
  - Schedule: cada hora en :30 UTC (`cron: '30 * * * *'`)
  - Repo público → minutos ilimitados
  - Artifacts subidos siempre (logs + data)
- ✅ DB Schema fix: `scraped_at` cambiado a TEXT para soportar ISO timestamps
- ✅ CLI mejorado con Click:
  - `scrape`: scraping principal
  - `test-config`: validar configuración
  - `history`: ver historial de items
  - `health`: health check de Supabase
- ✅ Browser con persistent profile local (cookies automáticas en `.cs_tracker_profile/`)

#### ⚠️ Pendientes/No Implementados
- ⏳ Session persistence para GitHub Actions (storage_state en BrowserManager)
  - **Razón**: Persistent profile funciona localmente, pero CI necesita approach diferente
  - **Solución futura**: Implementar `storage_state` parameter cuando sea necesario acceder a sell history en CI
- ⏳ Script `save_session.py` completamente funcional
  - **Razón**: Problemas de red con BUFF163 (ERR_NETWORK_CHANGED)
  - **Workaround**: Usar persistent profile local por ahora

#### Artefactos Creados
- `app/core/config.py`: Settings con pydantic-settings
- `app/core/logger.py`: structlog JSON logging
- `app/domain/models.py`: ScrapedItem, FilterConfig, AntibanConfig
- `app/domain/rules.py`: calculate_roi(), convert_cny_to_eur()
- `app/services/scraping.py`: Producer-consumer con async storage worker
- `app/services/storage.py`: Async Supabase con run_in_executor
- `app/services/utils/browser_manager.py`: Persistent profile (local sessions automáticas)
- `scripts/save_session.py`: Script para guardar cookies (WIP - problemas de red con BUFF)
- `.github/workflows/scraper.yml`: Workflow horario (sin session loading por ahora)

#### Definition of Done
- [x] ItemExtractor devuelve `List[Dict]` en lugar de objetos Pydantic
- [x] DetailedItemExtractor trabaja con `Dict` en lugar de `Skin`
- [x] ScrapingService valida con Pydantic solo al final (ScrapedItem)
- [x] Eliminados modelos innecesarios (Skin, MarketData, PriceData)
- [x] Logging estructurado sin emojis implementado
- [x] ROI formula corregida con Steam fee 13%
- [x] Async storage worker para guardar items durante scraping (código implementado, usar `--no-async-storage` para deshabilitar)
- [x] Code deduplication completado (~400 líneas)
- [x] GitHub Actions schedule optimizado (horario)
- [x] DB schema actualizado (scraped_at → TEXT)
- [x] Persistent profile para sesiones locales automáticas

---

### ⏳ FASE 3: Orquestación con LangGraph (PENDIENTE)

**Objetivo**: Implementar grafo de nodos para flujo de decisión.

#### Tareas
- [ ] Definir `AgentState` en `app/domain/state.py`
- [ ] Crear `app/graph/nodes/scout_node.py` (orquesta scraping)
  - Delega a `services/scraping.py`
  - < 15 líneas, solo orquestación
- [ ] Crear `app/graph/nodes/math_node.py` (filtra por rentabilidad)
  - Usa `domain/rules.py` para cálculos
- [ ] Crear `app/graph/workflow.py` (compila grafo)
  - Define aristas Scout → Math
- [ ] Integrar con servicios existentes de Fase 2

#### Definition of Done
- Ejecutar grafo con un skin devuelve estado con precios y profit
- Manejo de errores sin crashes (errores en `state['errors']`)
- Logging estructurado de cada transición de nodo
- Tests de integración del flujo completo

---

### ⏳ FASE 4: Inteligencia Artificial con Pydantic-AI (PENDIENTE)

**Objetivo**: Validación de riesgo usando LLMs.

#### Tareas
- [ ] Configurar cliente Gemini Flash / GPT-4o-mini
- [ ] Crear `app/graph/agents/analyst_agent.py` con Pydantic-AI
- [ ] Definir System Prompt ("Trader experto en CS2...")
- [ ] Crear `analyst_node` que consume el agente
  - Input: `state['market_data']` y `state['spread_analysis']`
  - Output: `state['risk_assessment']`
- [ ] Integrar análisis de volatilidad histórica
- [ ] Integrar análisis de volumen de mercado
- [ ] Añadir `trader_node` (simulado) que ejecuta si riesgo LOW

#### Definition of Done
Sistema devuelve análisis estructurado:
```json
{
  "risk_level": "LOW|MEDIUM|HIGH",
  "confidence": 0.85,
  "reasoning": "Volatilidad baja (3%), volumen alto (200/día)...",
  "recommended_action": "BUY|WAIT|SKIP"
}
```
- Operaciones simuladas se guardan en Supabase
- Logs de todas las decisiones del LLM
- Rate limiting para evitar costos excesivos

---

## 5. 📐 Guía de Estilos y Buenas Prácticas

Sigue estas reglas **estrictamente** al generar código.

### 5.1. Tipado y Datos

✅ **Hacer**:
```python
from typing import Dict, List

# Para datos intermedios: Dict con type hints
async def extract_items(page) -> List[Dict]:
    return [{"name": "AK-47", "price": 10.5}]

# Para datos finales: Pydantic validation
from pydantic import BaseModel

class ScrapedItem(BaseModel):
    item_name: str
    profit_eur: float

def finalize(data: Dict) -> ScrapedItem:
    return ScrapedItem(**data)  # Validación SOLO aquí
```

❌ **NO Hacer**:
```python
def extract_items(page):  # Sin tipos
    return ["AK-47", 10.5]  # Sin estructura

class Skin(BaseModel):  # NO para datos intermedios
    name: str

def extract(row) -> Skin:  # Validación prematura
    return Skin(name=row.text)  # Rompe con cambios web
```

**Reglas**:
- **Datos intermedios**: `Dict` con type hints (`Dict`, `List[Dict]`)
- **Datos finales**: `Pydantic` para validación (ScrapedItem)
- **Return Types**: Todas las funciones deben tener type hinting explícito
- **Razón**: Web scraping requiere flexibilidad, validar solo al final

---

### 5.2. LangGraph Patterns

✅ **Nodos Ligeros** (< 15 líneas):
```python
async def scout_node(state: AgentState) -> AgentState:
    """Nodo responsable de buscar precios."""
    skin_name = state["target_skin"]
    try:
        market_data = await scraping_service.get_prices(skin_name)
        return {**state, "market_data": market_data}
    except Exception as e:
        return {**state, "errors": [f"Scraping error: {str(e)}"]}
```

**Reglas**:
- Un nodo NO debe tener más de 15 líneas
- Debe delegar la lógica a `services/`
- **Manejo de Errores**: No lances excepciones, escribe en `state['errors']`

---

### 5.3. Asincronía (Asyncio)

✅ **Correcto**:
```python
async def fetch_prices(skin: str) -> MarketData:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"/api/prices/{skin}")
        return MarketData(**response.json())
```

❌ **Incorrecto**:
```python
def fetch_prices(skin: str):  # Sin async
    response = requests.get(f"/api/prices/{skin}")  # Bloqueante
    time.sleep(1)  # ❌ Nunca usar time.sleep()
```

**Reglas**:
- Todo I/O (Red, Base de Datos, LLM) debe ser `async/await`
- Nunca uses `time.sleep()`, usa `await asyncio.sleep()`

---

### 5.4. Mantenibilidad

#### Inyección de Dependencias

✅ **Hacer**:
```python
async def scout_node(
    state: AgentState,
    scraper: ScrapingService  # Inyectado
) -> AgentState:
    data = await scraper.get_prices(state["target_skin"])
    return {**state, "market_data": data}
```

❌ **NO Hacer**:
```python
async def scout_node(state: AgentState) -> AgentState:
    scraper = ScrapingService()  # ❌ Instanciado dentro
    data = await scraper.get_prices(state["target_skin"])
```

#### Configuración Centralizada

✅ **Hacer**:
```python
from app.core.config import settings

api_key = settings.GEMINI_API_KEY
```

❌ **NO Hacer**:
```python
import os
api_key = os.getenv("GEMINI_API_KEY")  # ❌ En mitad del código
```

---

## 6. 📚 Apéndice: Ejemplos de Código Esperado

### Ejemplo 1: Nodo de LangGraph

```python
from typing import Dict, Any
from app.domain.state import AgentState
from app.services.scraping import ScrapingService

async def scout_node(state: AgentState) -> AgentState:
    """
    Nodo responsable de extraer precios de mercados.
    
    Input: state['target_skin']
    Output: state['market_data'] or state['errors']
    """
    skin_name = state["target_skin"]
    
    try:
        # Delegamos al servicio (Clean Code)
        market_data = await ScrapingService.get_prices(skin_name)
        return {**state, "market_data": market_data}
    
    except Exception as e:
        # No crash, agregamos error al estado
        return {**state, "errors": [f"Scraping error: {str(e)}"]}
```

---

### Ejemplo 2: Agente Pydantic-AI

```python
from pydantic import BaseModel
from pydantic_ai import Agent
from app.domain.models import RiskAnalysis

class SpreadAnalysis(BaseModel):
    skin_name: str
    spread_percent: float
    volume_24h: int
    volatility: float

# Definir el agente con output estructurado
analyst = Agent(
    'google-gla:gemini-flash',
    result_type=RiskAnalysis,  # Fuerza respuesta JSON estructurada
    system_prompt=(
        "Eres un trader experto en CS2 skins. "
        "Analiza la volatilidad histórica y el volumen de mercado. "
        "Decide si es seguro ejecutar la operación de arbitraje."
    )
)

async def analyst_node(state: AgentState) -> AgentState:
    """
    Nodo que valida el riesgo usando IA.
    
    Input: state['spread_analysis']
    Output: state['risk_assessment']
    """
    try:
        # El LLM recibe contexto estructurado
        analysis = state['spread_analysis']
        
        result = await analyst.run(
            f"Analiza esta oportunidad: "
            f"Skin: {analysis.skin_name}, "
            f"Spread: {analysis.spread_percent}%, "
            f"Volumen 24h: {analysis.volume_24h}, "
            f"Volatilidad: {analysis.volatility}"
        )
        
        return {**state, "risk_assessment": result.data}
    
    except Exception as e:
        return {**state, "errors": [f"AI analysis error: {str(e)}"]}
```

---

### Ejemplo 3: Servicio de Scraping

```python
import httpx
from typing import Optional
from app.domain.models import MarketData
from app.core.config import settings
from app.core.logger import logger

class ScrapingService:
    """Servicio asíncrono para extraer precios de mercados."""
    
    @staticmethod
    async def get_prices(skin_name: str) -> MarketData:
        """
        Extrae precios de Steam y Buff163.
        
        Args:
            skin_name: Nombre del skin (ej: "AK-47 | Redline")
            
        Returns:
            MarketData con precios de ambos mercados
            
        Raises:
            httpx.HTTPError: Si la petición falla
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Steam
            steam_response = await client.get(
                f"{settings.STEAM_API_URL}/market/priceoverview",
                params={"market_hash_name": skin_name}
            )
            steam_response.raise_for_status()
            steam_data = steam_response.json()
            
            # Buff163
            buff_response = await client.get(
                f"{settings.BUFF_API_URL}/market/goods",
                params={"game": "csgo", "search": skin_name}
            )
            buff_response.raise_for_status()
            buff_data = buff_response.json()
            
            logger.info(f"Prices fetched for {skin_name}")
            
            return MarketData(
                skin_name=skin_name,
                steam_price=float(steam_data['lowest_price']),
                buff_price=float(buff_data['data']['items'][0]['sell_min_price']),
                timestamp=datetime.utcnow()
            )
```

---

### Ejemplo 4: Modelo de Dominio

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal

# NOTA: Solo modelos para resultado final y configuración
# Datos intermedios usan Dict simple

class ScrapedItem(BaseModel):
    """Resultado final del scraping (ÚNICA validación Pydantic)."""
    item_name: str
    url: Optional[str] = None
    buff_url: Optional[str] = None
    steam_url: Optional[str] = None
    
    buff_avg_price_eur: float = Field(..., gt=0)
    steam_avg_price_eur: float = Field(..., gt=0)
    
    profit_eur: float
    profitability_ratio: float
    
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

class FilterConfig(BaseModel):
    """Configuración de filtros."""
    min_price: float = Field(default=20.0, ge=0)
    max_price: Optional[float] = None
    min_volume: int = Field(default=40, ge=0)
    platforms: dict[str, bool] = Field(default={"BUFF": True})

class RiskAnalysis(BaseModel):
    """Resultado del análisis de riesgo por IA (Fase 4)."""
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    recommended_action: Literal["BUY", "WAIT", "SKIP"]

class AgentState(BaseModel):
    """Estado compartido del grafo LangGraph (Fase 3)."""
    target_skin: str
    market_data: Optional[dict] = None  # Dict, no Pydantic
    spread_analysis: Optional[dict] = None
    risk_assessment: Optional[RiskAnalysis] = None
    errors: list[str] = Field(default_factory=list)
```

---

## 7. ✅ Checklist de Calidad

Antes de considerar una fase completada, verificar:

### Code Quality
- [ ] Todos los archivos tienen docstrings
- [ ] Todas las funciones tienen type hints
- [ ] No hay `print()`, solo logging estructurado
- [ ] No hay `time.sleep()` en código async
- [ ] Validación Pydantic SOLO en datos finales

### Architecture
- [ ] Los nodos de LangGraph son < 15 líneas
- [ ] La lógica de negocio está en `services/`
- [ ] Los modelos están en `domain/`
- [ ] La configuración está centralizada en `core/`

### Testing
- [ ] Existe un test para cada fase
- [ ] Los tests son async (`pytest-asyncio`)
- [ ] Coverage > 70%

### Documentation
- [ ] README actualizado con la fase completada
- [ ] Ejemplos de uso en `examples/`
- [ ] Comentarios en código complejo

---

## 8. 🚀 Comandos de Desarrollo

```bash
# Setup inicial
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Desarrollo
python app/main.py --skin "AK-47 | Redline"

# Testing
pytest tests/ -v
pytest tests/ --cov=app --cov-report=html

# Linting
ruff check app/
mypy app/

# Docker (Fase 4)
docker-compose up -d mongodb
```

---

## 9. 📊 Métricas de Éxito

| Métrica | Objetivo | Fase |
|---------|----------|------|
| **Latencia Scraping** | < 2 segundos | Fase 1 |
| **Precisión Cálculos** | 100% (tests) | Fase 1 |
| **Latencia Grafo** | < 5 segundos | Fase 2 |
| **Latencia LLM** | < 3 segundos | Fase 3 |
| **Disponibilidad** | > 99% | Fase 4 |
| **ROI Real** | > 5% (simulado) | Fase 4 |

---

**🎓 Este documento es la guía maestra para el desarrollo del TFM.**

Última actualización: Diciembre 2025 (Fase 2 completada)
