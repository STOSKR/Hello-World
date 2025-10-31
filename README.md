# 🎮 CS-Tracker

Web scraper automático para rastrear precios y oportunidades de arbitraje de skins de CS2 desde [SteamDT](https://steamdt.com/hanging).

## 🚀 Características

- ✅ **Scraping Automático**: Extrae datos cada 6 horas usando GitHub Actions
- ✅ **Base de Datos en la Nube**: Almacena historial en Supabase (PostgreSQL)
- ✅ **Sin Costos**: Stack 100% gratuito
- ✅ **Multi-usuario**: Acceso compartido a datos
- ✅ **Historial Completo**: Rastrea cambios de precios a lo largo del tiempo

## 🛠️ Stack Tecnológico

- **Python 3.11** - Lenguaje principal
- **Playwright** - Web scraping con navegador real
- **Supabase** - Base de datos PostgreSQL en la nube (gratis)
- **GitHub Actions** - Automatización y scheduling (gratis)

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
│       └── scraper.yml          # Configuración de GitHub Actions
├── config/
│   └── schema.sql               # Schema de la base de datos
├── src/
│   ├── scraper.py               # Lógica de web scraping
│   ├── database.py              # Conexión con Supabase
│   └── main.py                  # Script principal
├── .env.example                 # Template de variables de entorno
├── .gitignore                   # Archivos ignorados por git
├── requirements.txt             # Dependencias de Python
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

## 📝 Notas Importantes

- ⚠️ **Respeta los términos de servicio** del sitio que scrapeeas
- 🔒 **Nunca commitees** el archivo `.env` con tus credenciales
- 💾 **Supabase gratuito** tiene límite de 500MB
- ⏱️ **GitHub Actions** tiene 2000 minutos/mes gratis (más que suficiente)

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas!

1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -m 'Añadir nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.

## 🔗 Links Útiles

- [Supabase Docs](https://supabase.com/docs)
- [Playwright Docs](https://playwright.dev/python/)
- [GitHub Actions Docs](https://docs.github.com/actions)
- [SteamDT](https://steamdt.com/hanging)

---

Desarrollado con ❤️ para la comunidad de CS2
