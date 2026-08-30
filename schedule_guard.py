"""
Guardia horaria compartida por los 5 scrapers del tracker.

Problema que resuelve: GitHub Actions cron corre siempre en UTC, pero
los horarios que importan son hora de Londres (BST en verano, GMT en
invierno). Antes había que editar 5 archivos YAML a mano, dos veces al
año, para sumar/restar 1 hora — frágil y fácil de olvidar.

Solución: cada workflow .yml schedulea AMBOS horarios UTC posibles para
cada hora local deseada (el que corresponde a BST y el que corresponde a
GMT). Esta guardia, corrida al principio de cada script, mira la hora
real de Londres en el momento de la ejecución y decide si esta corrida
es la que "toca" o si es la mitad sobrante del cron (la de la estación
que no está vigente) — en ese caso no hace ningún trabajo (sin red, sin
commit) y sale.

Uso en cada scraper:
    from schedule_guard import should_run
    if not should_run(config["schedule"]["runs_uk"]):
        print("[schedule_guard] fuera de ventana horaria UK, no corro esta vez")
        raise SystemExit(0)

Un `workflow_dispatch` manual (o correr el script a mano localmente)
puede saltear la guardia seteando la variable de entorno FORCE_RUN=true.
"""

import os
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python <3.9, no debería pasar en este repo
    ZoneInfo = None

try:
    # En Windows, zoneinfo necesita el paquete tzdata (Linux/GH Actions ya
    # trae la base de datos de zonas horarias del sistema operativo).
    import tzdata  # noqa: F401
except ImportError:
    pass

LONDON = "Europe/London"
DEFAULT_TOLERANCE_MINUTES = 12


def should_run(trigger_times_uk, tolerance_minutes=DEFAULT_TOLERANCE_MINUTES, now=None):
    """trigger_times_uk: lista de horarios locales de Londres, formato 'HH:MM'.
    Devuelve True si corresponde hacer el trabajo ahora."""
    if os.environ.get("FORCE_RUN", "").lower() == "true":
        print("[schedule_guard] FORCE_RUN=true, salteo la guardia horaria")
        return True

    if not trigger_times_uk:
        return True

    if ZoneInfo is None:
        print("[schedule_guard] zoneinfo no disponible, no bloqueo la corrida")
        return True

    now = now or datetime.now(ZoneInfo(LONDON))
    now_minutes = now.hour * 60 + now.minute

    for t in trigger_times_uk:
        h, m = map(int, t.split(":"))
        target_minutes = h * 60 + m
        if abs(now_minutes - target_minutes) <= tolerance_minutes:
            return True

    print(
        f"[schedule_guard] hora actual Londres {now.strftime('%H:%M')} no cae "
        f"dentro de +/-{tolerance_minutes}min de ninguno de {trigger_times_uk}"
    )
    return False
