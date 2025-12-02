# Script para ejecutar el scraper automáticamente
# Ruta: a:\AAAProyectos\Cs-Tracker\run_scraper.ps1

$ProjectPath = "A:\AAAProyectos\Cs-Tracker"
$LogFile = "$ProjectPath\logs\scheduler_$(Get-Date -Format 'yyyyMMdd').log"

# Cambiar al directorio del proyecto
Set-Location $ProjectPath

# Activar el entorno virtual
& "$ProjectPath\venv\Scripts\Activate.ps1"

# Ejecutar el scraper
Write-Output "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Iniciando scraper..." | Out-File -Append $LogFile
python -m app scrape --limit 20 2>&1 | Out-File -Append $LogFile
Write-Output "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Scraper finalizado" | Out-File -Append $LogFile

# Desactivar el entorno virtual
deactivate
