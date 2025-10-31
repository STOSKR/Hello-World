# 🎯 Guía de Configuración Rápida

## 📝 Pasos para poner en marcha el proyecto

### 1. Crear cuenta y proyecto en Supabase

1. Ve a [supabase.com](https://supabase.com) y regístrate
2. Clic en **"New Project"**
3. Elige un nombre (ejemplo: `cs-tracker`)
4. Elige una contraseña fuerte
5. Selecciona región más cercana
6. Espera 2 minutos a que se cree el proyecto

### 2. Crear la base de datos

1. En el dashboard de tu proyecto, ve a **SQL Editor** (en el menú lateral)
2. Clic en **"New Query"**
3. Abre el archivo `config/schema.sql` de este proyecto
4. Copia TODO el contenido y pégalo en el editor SQL
5. Clic en **"Run"** o presiona `Ctrl + Enter`
6. Deberías ver: ✅ Success. No rows returned

### 3. Obtener credenciales

1. Ve a **Settings → API** (en el menú lateral)
2. Copia estos dos valores:

```
Project URL: https://xxxxxxxxxxxxx.supabase.co
anon public: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ey...
```

### 4. Configurar el proyecto localmente

```powershell
# 1. Clonar o abrir el proyecto
cd a:\AAAProyectos\Cs-Tracker

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt
playwright install chromium

# 4. Crear archivo .env
copy .env.example .env

# 5. Editar .env con tus credenciales (usar notepad o VS Code)
notepad .env
```

En el archivo `.env`, reemplaza:
```env
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ey...
```

### 5. Probar el scraper

```powershell
python src/main.py
```

Si todo funciona verás:
- ✅ Conexión a Supabase establecida
- 📡 Navegando a la página...
- ✅ X items extraídos
- ✅ Trabajo completado exitosamente

### 6. Configurar GitHub Actions (Automatización)

1. Sube el código a GitHub (si no lo has hecho):
```powershell
git add .
git commit -m "Setup CS-Tracker"
git push origin main
```

2. En GitHub, ve a tu repositorio
3. **Settings → Secrets and variables → Actions**
4. Clic en **"New repository secret"**
5. Añade dos secrets:

   **Secret 1:**
   - Name: `SUPABASE_URL`
   - Value: `https://xxxxxxxxxxxxx.supabase.co` (tu URL)
   
   **Secret 2:**
   - Name: `SUPABASE_KEY`
   - Value: `eyJhbGc...` (tu anon key)

6. Ve a **Actions** y verás el workflow configurado
7. Puedes ejecutarlo manualmente con **"Run workflow"**

### 7. Verificar que funciona

1. Ve a la pestaña **Actions** en GitHub
2. Verás una ejecución en progreso o completada
3. Clic en ella para ver los logs
4. Deberías ver: ✅ Run scraper (con checkmark verde)

En Supabase:
1. Ve a **Table Editor → scraped_items**
2. Deberías ver los datos scrapeados

## 🎉 ¡Listo!

El scraper ahora se ejecutará automáticamente cada 6 horas.

## ⏱️ Horarios de ejecución automática (UTC)

- 00:00 UTC (medianoche)
- 06:00 UTC (6 AM)
- 12:00 UTC (mediodía)
- 18:00 UTC (6 PM)

Para convertir a tu zona horaria:
- **España (CET/CEST)**: UTC +1/+2
- **México (CST)**: UTC -6
- **Argentina (ART)**: UTC -3

## 🐛 Si algo falla

1. Revisa los logs en GitHub Actions
2. Verifica que los secrets estén bien configurados
3. Prueba localmente primero con `python src/main.py`
4. Revisa que la tabla `scraped_items` existe en Supabase
