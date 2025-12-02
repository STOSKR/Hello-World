"""
Script para ejecutar el scraper continuamente cada X horas.
Uso: python scheduler.py --interval 6
"""

import asyncio
import time
from datetime import datetime
import click
from app.main import main as scraper_main


@click.command()
@click.option("--interval", default=6, help="Horas entre ejecuciones")
@click.option("--limit", default=20, help="Número máximo de items a scrapear")
def scheduler(interval: int, limit: int):
    """Ejecuta el scraper cada X horas."""
    click.echo(f"🕒 Scheduler iniciado - Ejecutando cada {interval} horas")
    click.echo(f"📊 Límite de items: {limit}")
    click.echo(
        f"⏰ Próxima ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )

    while True:
        try:
            # Ejecutar scraper
            click.echo(f"\n{'='*60}")
            click.echo(
                f"🚀 Iniciando scraping - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            click.echo(f"{'='*60}")

            # Llamar al comando scrape
            import sys

            sys.argv = ["app", "scrape", "--limit", str(limit)]
            asyncio.run(scraper_main())

            # Esperar hasta la próxima ejecución
            wait_seconds = interval * 3600
            next_run = datetime.fromtimestamp(time.time() + wait_seconds)

            click.echo(f"\n✅ Scraping completado")
            click.echo(f"💤 Esperando {interval} horas...")
            click.echo(
                f"⏰ Próxima ejecución: {next_run.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )

            time.sleep(wait_seconds)

        except KeyboardInterrupt:
            click.echo("\n\n⛔ Scheduler detenido por el usuario")
            break
        except Exception as e:
            click.echo(f"\n❌ Error en ejecución: {e}")
            click.echo(f"🔄 Reintentando en {interval} horas...")
            time.sleep(interval * 3600)


if __name__ == "__main__":
    scheduler()
