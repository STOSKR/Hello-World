# 🎮 CS-Tracker - Sistema Inteligente de Arbitraje CS2

**Trabajo Fin de Máster**: Sistema de arbitraje financiero automatizado para skins de CS2 utilizando IA Agéntica.

## 🎯 Visión del Proyecto

Pipeline inteligente de decisión autónoma que detecta, analiza y ejecuta oportunidades de arbitraje entre Steam y Buff163 usando **LangGraph** (orquestación) y **Pydantic-AI** (inteligencia artificial).

### Objetivos del Sistema

1. **🔍 Detección**: Identificar diferencias de precio (arbitraje) entre mercados en tiempo real
2. **📊 Filtrado**: Seleccionar oportunidades matemáticamente rentables (ROI > X%)
3. **🤖 Validación IA**: Analizar riesgo y tendencias usando LLMs (Gemini/GPT)
4. **⚡ Ejecución**: Realizar operaciones de forma autónoma (simulada o real)

## 🏗️ Arquitectura

**Clean Architecture** con separación estricta de responsabilidades:

```
app/
├── core/           # Configuración transversal (Settings, Logger)
├── domain/         # Lógica pura (Models, State, Rules)
├── services/       # Lógica de negocio (Scraping, Math, Storage)
├── graph/          # Orquestación LangGraph
│   ├── nodes/      # Nodos especializados (Scout, Math, Analyst)
│   ├── agents/     # Agentes Pydantic-AI
│   └── workflow.py # Definición del grafo
└── main.py         # Entrypoint
```

## 🚀 Características Principales

### Fase 1: Sistema Base (Implementado)
- ✅ **Scraping Automático**: Extrae datos cada 6 horas usando GitHub Actions
- ✅ **Base de Datos en la Nube**: Almacena historial en Supabase (PostgreSQL)
- ✅ **Sin Costos**: Stack 100% gratuito
- ✅ **Multi-usuario**: Acceso compartido a datos
- ✅ **Historial Completo**: Rastrea cambios de precios a lo largo del tiempo

### Fase 2-4: Sistema Agéntico (Roadmap)
- 🔄 **Orquestación LangGraph**: Flujo de decisión cíclico y resiliente
- 🔄 **Agentes IA**: Validación de riesgo con LLMs estructurados
- 🔄 **Persistencia MongoDB**: Almacenamiento de oportunidades validadas
- 🔄 **Ejecución Autónoma**: Trading automático basado en análisis IA

## 🛠️ Stack Tecnológico

### Core System (Implementado)
| Componente | Tecnología | Propósito |
|------------|-----------|-----------|
| Lenguaje | **Python 3.11+** | Async nativo, tipado estricto |
| Web Scraping | **Playwright** | Navegador real, JavaScript dinámico |
| Base de Datos | **Supabase** | PostgreSQL en la nube (gratis) |
| Automatización | **GitHub Actions** | Scheduling y CI/CD (gratis) |

### AI System (Roadmap - TFM)
| Componente | Tecnología | Propósito |
|------------|-----------|-----------|
| Orquestación | **LangGraph** | Gestión de estado y flujo cíclico |
| Agentes IA | **Pydantic-AI** | LLMs con output estructurado |
| Modelos LLM | **Gemini Flash / GPT-4o-mini** | Baja latencia, bajo costo |
| Cliente HTTP | **httpx** | Async, HTTP/2, proxies |
| Base de Datos | **MongoDB** | Persistencia asíncrona |
| Configuración | **pydantic-settings** | Gestión de .env |
| Testing | **pytest + pytest-asyncio** | Tests unitarios e integración |

## 📋 Requisitos Previos

1. **Cuenta de Supabase** (gratis)
   - Regístrate en [supabase.com](https://supabase.com)
   - Crea un nuevo proyecto
   
2. **Python 3.11+**
3. **Git**

## ⚙️ Instalación y Configuración

### 1. Clonar el Repositorio

```bash
git clone https://github.com/STOSKR/Cs-Tracker.git
cd Cs-Tracker
```

### 2. Configurar Entorno Virtual (Recomendado)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Configurar Supabase

#### A. Crear la Base de Datos

1. Ve a tu proyecto en [Supabase Dashboard](https://app.supabase.com)
2. Navega a **SQL Editor**
3. Copia y pega el contenido de `config/schema.sql`
4. Ejecuta la query

#### B. Obtener Credenciales

1. En tu proyecto Supabase, ve a **Settings → API**
2. Copia:
   - **Project URL** (ejemplo: `https://xyzproject.supabase.co`)
   - **anon public key** (el token largo que empieza con `eyJ...`)

#### C. Configurar Variables de Entorno

```bash
# Copiar el template
cp .env.example .env

# Editar .env y añadir tus credenciales
# SUPABASE_URL=tu_url_aqui
# SUPABASE_KEY=tu_key_aqui
```

### 5. Configurar GitHub Actions (Automatización)

Para que el scraper se ejecute automáticamente cada 6 horas:

1. Ve a tu repositorio en GitHub
2. **Settings → Secrets and variables → Actions**
3. Añade estos **Repository Secrets**:
   - `SUPABASE_URL`: Tu URL de Supabase
   - `SUPABASE_KEY`: Tu anon key de Supabase

**¡Listo!** El scraper se ejecutará automáticamente:
- ⏰ Cada 6 horas (00:00, 06:00, 12:00, 18:00 UTC)
- 🔧 También puedes ejecutarlo manualmente desde la pestaña "Actions"

## 🧪 Prueba Local

Antes de dejar que GitHub Actions lo ejecute automáticamente, pruébalo localmente:

```bash
# Asegúrate de tener el .env configurado
python src/main.py
```

Si todo funciona, deberías ver:
- Logs del navegador abriendo steamdt.com
- Datos extraídos
- Confirmación de guardado en Supabase

## 📁 Estructura del Proyecto

```
Cs-Tracker/
├── .github/
│   └── workflows/
│       └── scraper.yml          # GitHub Actions (ejecución automática)
├── config/
│   └── schema.sql               # Schema Supabase (PostgreSQL)
├── src/                         # Sistema base (Fase 1)
│   ├── scraper.py               # Web scraping con Playwright
│   ├── database.py              # Conexión Supabase
│   └── main.py                  # Script principal
├── app/                         # Sistema agéntico (Fases 2-4)
│   ├── core/                    # Configuración transversal
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   └── logger.py            # Logger JSON estructurado
│   ├── domain/                  # Lógica pura (sin I/O)
│   │   ├── models.py            # Pydantic Schemas (Skin, Offer, Analysis)
│   │   ├── state.py             # AgentState (LangGraph)
│   │   └── rules.py             # Fórmulas de fees y spread
│   ├── services/                # Lógica de negocio
│   │   ├── scraping.py          # Scrapers Steam/Buff (httpx)
│   │   ├── market_math.py       # Cálculos financieros
│   │   └── storage.py           # Repositorio MongoDB
│   ├── graph/                   # Orquestación LangGraph
│   │   ├── nodes/               # Scout, Math, Analyst, Trader
│   │   ├── agents/              # Agentes Pydantic-AI
│   │   └── workflow.py          # Definición del grafo
│   └── main.py                  # Entrypoint agéntico
├── .env.example                 # Template variables de entorno
├── requirements.txt             # Dependencias Python
└── README.md                    # Este archivo
```

## 🔍 Uso de la Base de Datos

### Consultas Básicas (SQL)

Puedes ejecutar estas queries en el **SQL Editor** de Supabase:

```sql
-- Ver últimos 10 items scrapeados
SELECT * FROM scraped_items 
ORDER BY scraped_at DESC 
LIMIT 10;

-- Ver historial de un item específico
SELECT item_name, buy_price, sell_price, scraped_at
FROM scraped_items 
WHERE item_name LIKE '%AK-47%'
ORDER BY scraped_at DESC;

-- Ver últimos precios únicos de cada item
SELECT * FROM latest_items;

-- Detectar cambios de precio en las últimas 24h
SELECT * FROM get_price_changes(24);
```

### Desde Python

```python
from src.database import SupabaseDB

db = SupabaseDB()

# Obtener últimos 100 items
items = db.get_latest_items(limit=100)

# Historial de un item específico
history = db.get_item_history("AK-47 | Redline", limit=50)

# Items en un rango de fechas
items = db.get_items_by_date_range(
    start_date="2025-10-01T00:00:00",
    end_date="2025-10-31T23:59:59"
)
```

## 📊 Monitoreo

### GitHub Actions

1. Ve a la pestaña **Actions** en tu repositorio
2. Verás el historial de ejecuciones
3. Click en cualquier ejecución para ver logs detallados

### Logs

Si ejecutas localmente, los logs se guardan en:
- `scraper.log` - Archivo de log
- `data/latest_scrape.json` - Último scraping en JSON

## 🐛 Troubleshooting

### Error: "supabase module not found"
```bash
pip install supabase
```

### Error: "playwright not installed"
```bash
playwright install chromium
```

### Error: "SUPABASE_URL not set"
- Verifica que el archivo `.env` existe
- Verifica que las variables están correctamente configuradas
- Para GitHub Actions, verifica los Secrets

### El scraper no encuentra datos
- La estructura del sitio web puede haber cambiado
- Abre un issue con los logs
- Revisa `data/latest_scrape.json` para ver qué se extrajo

## 🗺️ Roadmap de Implementación

El desarrollo sigue un enfoque incremental en 4 fases:

### 🟢 Fase 1: Sistema Base (✅ Completado)
- ✅ Scraping de SteamDT con Playwright
- ✅ Almacenamiento en Supabase
- ✅ Automatización con GitHub Actions
- ✅ Historial de precios
- **DoD**: Sistema funcional extrayendo y almacenando datos cada 6 horas

### 🟡 Fase 2: Esqueleto del Grafo (En desarrollo)
- [ ] Definir `AgentState` en `domain/state.py`
- [ ] Crear nodo `scout_node` (extracción de precios)
- [ ] Crear nodo `math_node` (filtrado por rentabilidad)
- [ ] Compilar grafo básico en `graph/workflow.py`
- **DoD**: Grafo funcional que calcula spreads y filtra oportunidades

### 🟡 Fase 3: Inteligencia Artificial
- [ ] Configurar clientes Gemini/OpenAI
- [ ] Crear `analyst_agent` con Pydantic-AI
- [ ] Implementar validación de riesgo con LLM
- [ ] Integrar nodo `analyst_node` al grafo
- **DoD**: Sistema que genera análisis de riesgo estructurado por IA

### 🔴 Fase 4: Persistencia y Producción
- [ ] Configurar MongoDB con Docker Compose
- [ ] Implementar `services/storage.py`
- [ ] Crear nodo `trader_node` (ejecución simulada)
- [ ] Logging y monitoreo completo
- **DoD**: Oportunidades validadas guardadas en BD, listas para ejecución

## 🎓 Principios de Desarrollo (TFM)

### Clean Code & Architecture
- **Tipado Estricto**: Type hints en todas las funciones
- **Asincronía**: Todo I/O es `async/await`
- **Nodos Ligeros**: LangGraph delega lógica a `services/`
- **Inyección de Dependencias**: No instanciar clientes en funciones
- **Configuración Centralizada**: Todo en `core/config.py`

### Ejemplo de Nodo (LangGraph)
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

### Ejemplo de Agente (Pydantic-AI)
```python
from pydantic_ai import Agent
from app.domain.models import RiskAnalysis

analyst = Agent(
    'google-gla:gemini-flash',
    result_type=RiskAnalysis,
    system_prompt="Analiza volatilidad y decide si es seguro comprar."
)

async def analyst_node(state: AgentState) -> AgentState:
    result = await analyst.run(f"Analiza: {state['spread_analysis']}")
    return {**state, "risk_assessment": result.data}
```

## 🔄 Personalización

### Cambiar Frecuencia de Scraping

Edita `.github/workflows/scraper.yml`:

```yaml
schedule:
  # Cada 3 horas
  - cron: '0 */3 * * *'
  
  # Cada día a las 9 AM UTC
  - cron: '0 9 * * *'
  
  # Cada hora
  - cron: '0 * * * *'
```

### Ajustar Selectores CSS

Si el sitio cambia su estructura, edita `src/scraper.py` en el método `_extract_items()`.

## 📊 Flujo del Sistema Completo

```
┌─────────────────────────────────────────────────────────┐
│                   ENTRADA: Skin Target                   │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  🔍 Scout Node  │  ← Extrae precios Steam/Buff
              │  (Scraping)     │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  📊 Math Node   │  ← Calcula spread, ROI, fees
              │  (Filtering)    │
              └────────┬────────┘
                       │
              ┌────────┴────────┐
              │ ROI > threshold? │
              └────────┬────────┘
                   YES │    NO → END
                       ▼
              ┌─────────────────┐
              │ 🤖 Analyst Node │  ← LLM analiza riesgo/tendencias
              │  (Pydantic-AI)  │
              └────────┬────────┘
                       │
              ┌────────┴────────┐
              │  Riesgo BAJO?   │
              └────────┬────────┘
                   YES │    NO → END
                       ▼
              ┌─────────────────┐
              │ ⚡ Trader Node  │  ← Ejecuta operación
              │   (Simulated)   │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  💾 MongoDB     │  ← Guarda oportunidad
              └─────────────────┘
```

## 📝 Notas Importantes

### Límites y Consideraciones
- ⚠️ **Respeta los términos de servicio** del sitio que scrapeeas
- 🔒 **Nunca commitees** el archivo `.env` con tus credenciales
- 💾 **Supabase gratuito**: 500MB de espacio
- ⏱️ **GitHub Actions**: 2000 minutos/mes gratis
- 🤖 **Gemini Flash**: 15 RPM gratis, 1500 RPD
- 🧠 **GPT-4o-mini**: $0.15/1M tokens input

### Testing del Sistema
```powershell
# Fase 1: Test del scraper base
python src/main.py

# Fase 2: Test del grafo (cuando esté implementado)
python -m pytest tests/test_graph.py

# Fase 3: Test del agente IA
python -m pytest tests/test_analyst_agent.py

# Fase 4: Test end-to-end
python app/main.py --skin "AK-47 | Redline"
```

## 🤝 Contribuciones

Este proyecto es un **Trabajo Fin de Máster** en desarrollo activo.

**Áreas de contribución:**
- 🐛 Reportar bugs en el scraper base
- 💡 Sugerir mejoras en el sistema agéntico
- 🧪 Añadir tests y casos edge
- 📖 Mejorar documentación

**Proceso:**
1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/nueva-funcionalidad`)
3. Commit con mensajes descriptivos
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto es de código abierto bajo licencia MIT.

**Disclaimer**: Este sistema es educativo. No se garantiza la rentabilidad ni se recomienda usar en producción sin análisis de riesgo profesional.

## 🔗 Links Útiles

### Documentación del Proyecto
- [Setup Guide](./SETUP.md) - Guía paso a paso de configuración
- [Schema SQL](./config/schema.sql) - Estructura de la base de datos
- [Examples](./examples/) - Scripts de ejemplo

### Tecnologías Core
- [Supabase Docs](https://supabase.com/docs) - Base de datos PostgreSQL
- [Playwright Python](https://playwright.dev/python/) - Web scraping
- [GitHub Actions](https://docs.github.com/actions) - CI/CD

### Tecnologías AI (TFM)
- [LangGraph](https://langchain-ai.github.io/langgraph/) - Orquestación de agentes
- [Pydantic-AI](https://ai.pydantic.dev/) - Agentes con output estructurado
- [Gemini API](https://ai.google.dev/gemini-api/docs) - LLM de Google
- [OpenAI API](https://platform.openai.com/docs) - GPT models

### Fuentes de Datos
- [SteamDT Hanging](https://steamdt.com/hanging) - Arbitraje Steam
- [Buff163](https://buff.163.com/) - Mercado secundario CS2

---

## 👨‍💻 Autor

**Trabajo Fin de Máster** - Sistema de Arbitraje Inteligente con IA Agéntica

Desarrollado con ❤️ para la comunidad de CS2 y entusiastas de IA
