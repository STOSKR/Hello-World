# Proceso de Scraping de CS2 Arbitrage

## 📋 Flujo de Trabajo Completo

### 1. Navegación Inicial
- **URL**: https://steamdt.com/en/hanging
- **Objetivo**: Acceder a la tabla de arbitraje de CS2 skins
- **Método**: Playwright con contexto persistente (mantiene sesión)

### 2. Configuración de Filtros

El sistema soporta **6 configuraciones predefinidas (presets)** que combinan:

#### 2.1. Balance Type (Tipo de Balance)
- **STEAM Balance**: Fondos de la wallet de Steam
- **Platform Balance**: Fondos en plataformas de terceros (BUFF, C5GAME, UU)

#### 2.2. Sell Mode (Modo de Venta)
Dos modos **mutuamente exclusivos**:
- **"Sell at STEAM Lowest Price"**: Vender al precio más bajo actual en Steam
- **"Sell to STEAM Highest Buy Order"**: Vender a la orden de compra más alta de Steam

#### 2.3. Buy Mode (Modo de Compra) 
Solo aplica para **Platform Balance**. Dos modos **mutuamente exclusivos**:
- **"Buy at Platform Lowest Price"**: Comprar al precio más bajo de la plataforma
- **"Buy via Platform Buy Order"**: Comprar creando una orden de compra

#### 2.4. Configuraciones Comunes
Aplicadas a todas las configuraciones:
- **Currency**: EUR (€)
- **Min Price**: 20€ mínimo
- **Min Volume**: 40 ventas mínimas en 24h
- **Platform**: BUFF (habilitado por defecto)

### 3. Extracción de Items de la Tabla

**Proceso**:
1. Esperar carga dinámica (10 segundos por defecto)
2. Cerrar modales si aparecen
3. Localizar tabla con items (`table-rows`)
4. Extraer todos los items visibles con:
   - Nombre del item
   - URL detallada
   - Precio Steam
   - Precio BUFF
   - Spread (diferencia)
   - Volumen de ventas

**Filtrado automático**:
- Excluir items con prefijos: "Charm |", "Graffiti |", "Sticker |", etc.
- Aplicar filtros de precio mínimo y volumen

### 4. Scraping Detallado por Item

Para cada item de la tabla, realizar scraping en **paralelo**:

#### 4.1. Scraping de BUFF163
- **URL**: Enlace directo desde la tabla
- **Datos extraídos**:
  - Precio de venta actual (EUR)
  - Precio de compra (buy order) si existe
  - Número de listings activos
  - Volumen de ventas 24h
  - Histórico de ventas recientes (últimas 5-10)

#### 4.2. Scraping de Steam Market
- **URL**: Enlace directo desde la tabla
- **Datos extraídos**:
  - Precio de venta más bajo (EUR)
  - Precio de orden de compra más alta (EUR)
  - Cantidad de listings
  - Volumen de ventas 24h
  - Histórico de precios (últimas ventas)

**Optimización**: BUFF y Steam se scrapean **simultáneamente** usando `asyncio.gather()`

### 5. Análisis de Volatilidad

**Objetivo**: Detectar manipulación de precios o dumps recientes

**Proceso**:
1. Obtener últimas 5-10 ventas del histórico
2. Calcular precio promedio de ventas recientes
3. Comparar con precio actual de listing

**Regla de descarte**:
```python
if avg_recent_price < current_price * 0.90:  # 10% más barato
    # Descartar item - posible dump de precio
    skip_item = True
```

**Razón**: Si las ventas recientes fueron 10%+ más baratas que el precio actual, indica:
- Posible dump temporal
- Precio actual inflado artificialmente
- Volatilidad alta (riesgo)

### 6. Cálculo de Rentabilidad

**Fórmulas implementadas**:

#### 6.1. Fees
- **Steam Fee**: 13% (5% Steam + 8% game publisher)
- **BUFF Fee**: 2.5%

#### 6.2. Spread (Diferencia de Precio)
```python
spread_eur = steam_sell_price - buff_buy_price
spread_percent = (spread_eur / buff_buy_price) * 100
```

#### 6.3. Profit Después de Fees
```python
steam_after_fee = steam_sell_price * (1 - 0.13)  # -13% Steam
buff_cost = buff_buy_price * (1 + 0.025)          # +2.5% BUFF

profit_eur = steam_after_fee - buff_cost
profitability_percent = (profit_eur / buff_cost) * 100
```

#### 6.4. ROI (Return on Investment)
```python
roi = (profit_eur / buff_cost) * 100
```

### 7. Almacenamiento de Datos

**Datos guardados**:

#### 7.1. Formato JSON Local
```json
{
  "item_name": "AK-47 | Redline (Field-Tested)",
  "buff_price": 25.50,
  "steam_price": 32.00,
  "spread_eur": 6.50,
  "spread_percent": 25.49,
  "profit_eur": 4.12,
  "profitability_percent": 15.78,
  "volume_24h": 120,
  "timestamp": "2024-12-01T20:30:00Z"
}
```

#### 7.2. Base de Datos (Supabase)
Tabla: `market_data`
- Histórico completo de precios
- Permite análisis de tendencias
- Datos para entrenamiento futuro de modelos IA

### 8. Configuración Anti-Ban

**Modos disponibles**:

| Modo | Concurrencia | Delay Items | Delay Clicks | Wait Time |
|------|-------------|-------------|--------------|-----------|
| **Safe** | 1 item | 5s | 3s | 12s |
| **Balanced** | 2 items | 3s | 2s | 10s |
| **Fast** | 3 items | 2s | 1s | 8s |
| **Stealth** | 1 item | 8s | 4s | 15s |

**Configuración actual**: Modo **Balanced** por defecto
- Reduce riesgo de rate limiting
- Scraping 2-3x más rápido que modo Safe

## 🎯 Presets de Configuración

### Preset 1: STEAM Balance - Lowest Price
- Balance: STEAM
- Sell: STEAM Lowest Price
- Buy: N/A

### Preset 2: STEAM Balance - Highest Buy Order
- Balance: STEAM
- Sell: STEAM Highest Buy Order
- Buy: N/A

### Preset 3: Platform Balance - Lowest/Lowest
- Balance: Platform
- Sell: Platform Lowest Price
- Buy: Platform Lowest Price

### Preset 4: Platform Balance - Lowest/Highest
- Balance: Platform
- Sell: Platform Highest Buy Order
- Buy: Platform Lowest Price

### Preset 5: Platform Balance - Order/Lowest
- Balance: Platform
- Sell: Platform Lowest Price
- Buy: Platform Buy Order

### Preset 6: Platform Balance - Order/Highest
- Balance: Platform
- Sell: Platform Highest Buy Order
- Buy: Platform Buy Order

## 🚀 Ejecución

### Scraper Legacy (src/)
```bash
# Sintaxis: python src/main.py [HEADLESS] [PRESET]
python src/main.py 0 2        # Headless, preset 2
python src/main.py 1 3        # Visible, preset 3
```

### Scraper Clean Architecture (app/)
```bash
# Scraping básico con filtrado automático
python -m app.main scrape

# Scraping con límite de items
python -m app.main scrape --limit 10

# Scraping visible, 2 items concurrentes
python -m app.main scrape --visible --concurrent 2

# Guardar a BD y archivo
python -m app.main scrape --save-db --output data/results.json
```

### Scraping Paralelo con Proxies
```bash
# 5 workers con proxies diferentes
python src/parallel_scraper.py 5 2 0

# Ver guía completa en: PARALLEL_SCRAPING_GUIDE.md
```

## 📊 Métricas Actuales

- **Tiempo por item**: ~3-5 segundos (BUFF + Steam en paralelo)
- **Items procesados**: Variable según filtros
- **Tasa de descarte**: ~20-30% por volatilidad
- **Rentabilidad promedio**: 5-15% después de fees

## 🔮 Próximas Fases (Master Plan)

- **Fase 2**: Migración completa a Clean Architecture ✅ (90% completado)
- **Fase 3**: LangGraph - Orquestación con nodos (Scout → Math → Analyst)
- **Fase 4**: Pydantic-AI - Validación de riesgo con LLMs (Gemini/GPT)

---

**Última actualización**: Diciembre 2024  
**Arquitecturas**: Legacy (`src/`) + Clean (`app/`) coexisten