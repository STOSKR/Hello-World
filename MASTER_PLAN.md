# 🎓 MASTER PLAN - CS2 Agentic Graph System

**Trabajo Fin de Máster**: Sistema de Arbitraje Financiero Automatizado con IA Agéntica

---

## 🎯 ROL Y OBJETIVO

**ROL DE LA IA**: Principal Software Engineer y Arquitecto de IA

**OBJETIVO**: Implementar un sistema de arbitraje financiero automatizado utilizando:
- **LangGraph**: Orquestación y gestión de estado
- **Pydantic-AI**: Inteligencia artificial con output estructurado

**ESTÁNDAR**: Código de producción, Clean Architecture, Asíncrono y Tipado Estricto

---

## 1. 🌟 Visión y Objetivos

Desarrollar un **pipeline inteligente** donde el dato fluye a través de nodos especializados.

### Objetivos Principales

| # | Objetivo | Descripción |
|---|----------|-------------|
| 1 | **Detección en Tiempo Real** | Detectar diferencias de precio (arbitraje) entre Steam y Buff163 |
| 2 | **Filtrado Matemático** | Filtrar oportunidades con ROI > X% |
| 3 | **Validación IA** | Validar riesgo usando LLMs que analizan tendencias y volatilidad |
| 4 | **Ejecución Autónoma** | Ejecutar operación (simulada o real) de forma autónoma |

---

## 2. 🛠️ Stack Tecnológico (Estricto)

| Componente | Tecnología | Versión/Notas |
|------------|-----------|---------------|
| **Lenguaje** | Python | 3.11+ (Async nativo) |
| **Orquestación** | LangGraph | Gestión de Estado y Flujo Cíclico |
| **Agentes IA** | Pydantic-AI | LLMs con output estructurado y Tools |
| **Modelos LLM** | Gemini Flash / GPT-4o-mini | Low latency & Low cost |
| **Cliente HTTP** | httpx | Async, HTTP/2, Soporte de Proxies |
| **Base de Datos** | MongoDB (motor) | Persistencia asíncrona |
| **Configuración** | pydantic-settings | Gestión de .env |
| **Testing** | pytest + pytest-asyncio | Tests unitarios y de integración |

---

## 3. 🏗️ Arquitectura de Software (Clean Architecture)

**Principio**: El código debe estar desacoplado. Los Nodos del Grafo NO contienen lógica de negocio compleja, solo orquestan llamadas a Servicios.

```
app/
├── core/                   # Configuración transversal
│   ├── config.py           # Clases de Configuración (Settings)
│   └── logger.py           # Logger JSON estructurado
├── domain/                 # Lógica Pura (Sin I/O, Sin Librerías externas)
│   ├── models.py           # Pydantic Schemas (Skin, Offer, Analysis)
│   ├── state.py            # Definición del AgentState (LangGraph)
│   └── rules.py            # Fórmulas (Cálculo de Fees, Spread)
├── services/               # La "Carne" del sistema (Lógica dura)
│   ├── scraping.py         # Scrapers de Steam/Buff (HTTPX)
│   ├── market_math.py      # Lógica financiera
│   └── storage.py          # Repositorio MongoDB
├── graph/                  # La "Estructura" (LangGraph)
│   ├── nodes/              # Funciones de nodo (Scout, Math, Analyst)
│   ├── agents/             # Definición de Agentes Pydantic-AI
│   └── workflow.py         # Definición de aristas y compilación del grafo
└── main.py                 # Entrypoint
```

### Flujo de Datos

```
ENTRADA → Scout Node → Math Node → Analyst Node → Trader Node → SALIDA
           (Scraping)   (Filtering)   (AI Risk)      (Execution)
```

---

## 4. 📋 Fases de Implementación (Roadmap)

La IA debe implementar esto en **orden secuencial**. No pasar a la siguiente fase sin completar los requisitos de la actual.

### 🟢 FASE 1: Dominio y Servicios Base (Core)

**Objetivo**: Capacidad de extraer datos y calcular beneficios sin grafos ni IA.

#### Tareas
- [ ] Definir `Settings` en `core/config.py` (cargar API Keys)
- [ ] Crear modelos en `domain/models.py` (`Skin`, `MarketData`)
- [ ] Implementar `services/scraping.py` con manejo de errores y httpx
- [ ] Implementar `domain/rules.py` con las fórmulas de comisiones de Steam/Buff

#### Definition of Done
Un script `test_phase1.py` que:
- Imprime el precio actual de la "AK-47 | Redline"
- Calcula el spread entre mercados
- No genera errores

---

### 🟢 FASE 2: Esqueleto del Grafo (LangGraph)

**Objetivo**: Conectar el flujo lógico básico (Scout → Math).

#### Tareas
- [ ] Definir `AgentState` en `domain/state.py`
- [ ] Crear `graph/nodes/scout_node.py` (Llama al servicio de scraping)
- [ ] Crear `graph/nodes/math_node.py` (Filtra por rentabilidad)
- [ ] Montar el grafo en `graph/workflow.py` y compilarlo

#### Definition of Done
Al ejecutar el grafo con una skin:
- El estado final contiene los precios
- El estado final contiene el cálculo de profit
- O contiene un error controlado (no crash)

---

### 🟢 FASE 3: Inteligencia Artificial (Pydantic-AI)

**Objetivo**: Integrar el cerebro (LLM) para validación de riesgo.

#### Tareas
- [ ] Configurar cliente de Gemini/OpenAI
- [ ] Crear el Agente en `graph/agents/analyst_agent.py` usando pydantic-ai
- [ ] Definir el System Prompt ("Actúa como un trader experto...")
- [ ] Conectar el `analyst_node` al grafo después del nodo matemático

#### Definition of Done
El sistema devuelve un objeto JSON con:
```json
{
  "risk_level": "LOW|MEDIUM|HIGH",
  "confidence": 0.85,
  "reasoning": "Justificación generada por el LLM..."
}
```

---

### 🟢 FASE 4: Persistencia y Producción

**Objetivo**: Guardar resultados y robustez.

#### Tareas
- [ ] Levantar MongoDB con Docker Compose
- [ ] Implementar `services/storage.py` para guardar oportunidades
- [ ] Añadir el `trader_node` (Simulado) que guarda en BD si el riesgo es bajo
- [ ] Configurar logging estructurado (JSON)

#### Definition of Done
Ejecución completa donde:
- Una oportunidad rentable y segura queda registrada en MongoDB
- Los logs están estructurados en JSON
- El sistema puede reiniciarse sin pérdida de datos

---

## 5. 📐 Guía de Estilos y Buenas Prácticas

Sigue estas reglas **estrictamente** al generar código.

### 5.1. Tipado y Datos

✅ **Hacer**:
```python
from pydantic import BaseModel

class MarketData(BaseModel):
    steam_price: float
    buff_price: float
    spread: float

def calculate_spread(data: MarketData) -> float:
    return data.steam_price - data.buff_price
```

❌ **NO Hacer**:
```python
def calculate_spread(data):  # Sin tipos
    return data['steam_price'] - data['buff_price']  # Dict sin modelo
```

**Reglas**:
- No `Dict` sin tipar: Usa siempre **Pydantic Models** o **TypedDict**
- **Return Types**: Todas las funciones deben tener type hinting explícito

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

class Skin(BaseModel):
    """Representa un skin de CS2."""
    name: str = Field(..., description="Nombre completo del skin")
    wear: Optional[str] = Field(None, description="Desgaste (FN, MW, FT, etc)")
    float_value: Optional[float] = Field(None, ge=0.0, le=1.0)

class MarketData(BaseModel):
    """Datos de mercado de un skin."""
    skin_name: str
    steam_price: float = Field(..., gt=0)
    buff_price: float = Field(..., gt=0)
    timestamp: datetime
    volume_24h: Optional[int] = Field(None, ge=0)

class RiskAnalysis(BaseModel):
    """Resultado del análisis de riesgo por IA."""
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    recommended_action: Literal["BUY", "WAIT", "SKIP"]

class AgentState(BaseModel):
    """Estado compartido del grafo LangGraph."""
    target_skin: str
    market_data: Optional[MarketData] = None
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
- [ ] No hay `Dict` sin tipar
- [ ] No hay `time.sleep()` en código async

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

Última actualización: Noviembre 2025
