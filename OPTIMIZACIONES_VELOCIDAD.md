# Optimizaciones Propuestas para Reducir Tiempo de Scraping

## 🐌 Problema Actual: 20 minutos para 50 items

### Análisis de Tiempos
```
Por cada item:
- Delay anti-ban: 5s + random(2-5s) = ~8.5s
- BUFF initial delay: random(2-5s) = ~3.5s  
- BUFF page wait: 5s × 2 navegaciones = 10s
- Steam navigation: ~3s
- Total por item: ~25s

50 items / 2 workers = 25 items/worker × 25s = 625s ≈ 10.5 minutos
Con errores/retries: ~20 minutos ✓
```

---

## 🚀 Optimizaciones Propuestas

### 1. **REDUCIR DELAYS ANTI-BAN** (Impacto: 3-4x más rápido)

**Configuración Actual:**
```python
delay_between_items: 5000ms     # ❌ Muy conservador
random_delay_min: 2000ms
random_delay_max: 5000ms
```

**Configuración Agresiva (pero segura con 2 workers):**
```python
delay_between_items: 1000ms     # ✅ 1s fijo
random_delay_min: 500ms         # ✅ 0.5-2s random
random_delay_max: 2000ms
# Total: 1.5-3s por item (vs 7-10s actual)
```

**Impacto:** 50 items de 10.5 min → **3-4 minutos**

---

### 2. **REDUCIR BUFF INITIAL DELAY** (Impacto: 2x más rápido en BUFF)

**Actual:**
```python
BUFF_INITIAL_DELAY_MIN = 2000  # 2-5s antes de cada navegación
BUFF_INITIAL_DELAY_MAX = 5000
```

**Optimizado:**
```python
BUFF_INITIAL_DELAY_MIN = 500   # 0.5-1.5s
BUFF_INITIAL_DELAY_MAX = 1500
```

**Impacto:** BUFF navigation de ~8s → **4-5s**

---

### 3. **REDUCIR PAGE WAIT DINÁMICO** (Impacto: 5-10s menos por item)

**Actual:**
```python
await page.wait_for_timeout(5000)  # ❌ Espera fija 5s
```

**Optimizado con selector wait:**
```python
# Esperar elemento específico en lugar de timeout fijo
await page.wait_for_selector('.selling-item', timeout=5000)
# Solo espera lo necesario (1-2s típicamente)
```

**Impacto:** De 5s fijo → **1-2s promedio**

---

### 4. **ELIMINAR NAVEGACIÓN A HISTORY** (Impacto: 50% menos tiempo en BUFF)

**Problema actual:** 
- Navega a BUFF selling tab (5s)
- Navega a BUFF history tab (5s)
- **Total: 10s por item**

**Optimización:**
```python
# Solo navegar a selling si price_drop_validation está deshabilitada
if settings.validate_price_drops:
    trade_records = await self.extract_trade_records(page)
else:
    trade_records = []  # Skip history navigation
```

**Impacto:** 10s → **5s por item** (50% más rápido)

---

### 5. **CACHE DE PÁGINAS WORKER** (Impacto: Eliminar page creation overhead)

**Actual:** Pre-crea páginas ✅ (ya implementado)

**Mejora adicional:** Reusar páginas sin cerrar/reabrir
```python
# Ya está implementado correctamente, no hay mejora aquí
```

---

### 6. **SKIP ITEMS CON BAJO VOLUMEN ANTES DE SCRAPING DETALLADO**

**Idea:** Extraer volumen desde la tabla principal antes de abrir BUFF/Steam

**Problema:** La tabla de SteamDT no muestra volumen
**Status:** ❌ No aplicable

---

### 7. **AUMENTAR WORKERS A 3-4** (Impacto: 1.5-2x más rápido)

**Actual:** 2 scraper workers

**Propuesta:** 3-4 scraper workers (balanceado con delays reducidos)

```bash
python -m app scrape --concurrent 4 --limit 50
```

**Impacto con delays optimizados:**
- 2 workers: ~4 minutos
- 4 workers: ~**2 minutos**

**Riesgo:** Más workers = más probabilidad de ban
**Mitigación:** Delays reducidos pero no eliminados

---

## 📊 Comparativa de Configuraciones

| Configuración | Tiempo 50 items | Workers | Delays | Riesgo Ban |
|---------------|----------------|---------|---------|------------|
| **Actual** | ~20 min | 2 | 5s + 2-5s | Muy Bajo |
| **Conservadora** | ~8 min | 2 | 2s + 1-2s | Bajo |
| **Balanceada** | ~4 min | 3 | 1s + 0.5-2s | Medio |
| **Agresiva** | ~2 min | 4 | 0.5s + 0.5-1s | Alto |

---

## 🎯 Recomendación: Configuración Balanceada

```python
# config.py
max_concurrent: 3
delay_between_items: 1000        # 1s fijo
random_delay_min: 500            # 0.5-2s random
random_delay_max: 2000

# constants.py
BUFF_INITIAL_DELAY_MIN = 500
BUFF_INITIAL_DELAY_MAX = 1500
PAGE_WAIT_DYNAMIC_CONTENT = 2000  # Reducir de 5s a 2s
```

**Resultado esperado: 50 items en ~4 minutos** (5x más rápido)

---

## 🔧 Optimizaciones Adicionales (Más avanzadas)

### 8. **PARALLEL BUFF SELLING + HISTORY**

En lugar de navegar secuencialmente:
```python
# Actual (secuencial):
await goto(selling_url)  # 5s
selling_items = extract()
await goto(history_url)  # 5s
history = extract()

# Optimizado (paralelo con 2 páginas):
selling_task = page1.goto(selling_url)
history_task = page2.goto(history_url)
await asyncio.gather(selling_task, history_task)
# Total: 5s en lugar de 10s
```

**Impacto:** 50% más rápido en BUFF (pero requiere más páginas)

---

### 9. **SMART TIMEOUT BASADO EN RESPONSE**

```python
# Esperar solo hasta que llegue la respuesta del servidor
await page.goto(url, wait_until='domcontentloaded')  # Más rápido que 'networkidle'
```

**Impacto:** 1-2s menos por navegación

---

### 10. **CIRCUIT BREAKER PARA ITEMS PROBLEMÁTICOS**

```python
if consecutive_errors > 3:
    logger.warning("Skipping remaining BUFF items - circuit breaker activated")
    return None  # Skip BUFF entirely for this session
```

**Impacto:** Evita perder 30s+ en retries fallidos

---

## 💡 Implementación Inmediata

**Archivo de configuración rápida para testing:**

```json
// config/fast_scraper_config.json
{
  "max_concurrent": 3,
  "delay_between_items": 1000,
  "random_delay_min": 500,
  "random_delay_max": 2000,
  "headless": true
}
```

**Uso:**
```bash
# Testing rápido
python -m app scrape --limit 10 --concurrent 3

# Producción optimizada
python -m app scrape --limit 50 --concurrent 3
```

---

## ⚠️ Consideraciones

1. **BUFF/Steam pueden detectar scraping agresivo**
   - Recomendado: Empezar con configuración balanceada
   - Monitorear: Si aparecen captchas, aumentar delays

2. **Calidad de datos vs Velocidad**
   - Menos delay = menos tiempo para cargar datos dinámicos
   - Validar que datos extraídos sean correctos

3. **Trade-off: Velocidad vs Ban Risk**
   - 2 workers + delays altos = Seguro pero lento
   - 4 workers + delays bajos = Rápido pero riesgoso
   - **3 workers + delays medios = Balance óptimo** ✅
