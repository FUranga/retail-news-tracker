"""
Fuente 5: BRC — informes recurrentes con cronograma predecible.

Decisión de diseño (29/08/2026): en vez de scrapear brc.org.uk (HTML frágil,
sin API, se rompe con cualquier rediseño), calculamos la fecha esperada de
sus informes mensuales recurrentes, que salen con un patrón conocido y
bastante estable:

  - BRC-KPMG Retail Sales Monitor: ~7 días hábiles después del cierre del
    mes de referencia (confirmado vía metodología de ONS que los compara).

Esto da una fecha ESTIMADA, no confirmada oficialmente — se marca así en el
evento (needs_confirmation=True) para que quede claro en el dashboard que
es un cálculo, no un dato scrapeado de una fuente que lo publicó.

Eventos puntuales de BRC (webinars, jornadas, cumbres sectoriales) son
esporádicos y no seguían un patrón — esos quedan mejor como carga manual
cuando Francisco se entera de ellos, no vale la pena mantener un scraper
frágil para algo tan poco frecuente.
"""

from datetime import date, timedelta
import calendar

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agenda_schema import new_event


def _add_working_days(start: date, n: int) -> date:
    d = start
    added = 0
    while added < n:
        d += timedelta(days=1)
        if d.weekday() < 5:  # lunes=0 .. viernes=4
            added += 1
    return d


def _last_day_of_month(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def _next_n_months(start: date, n: int):
    y, m = start.year, start.month
    for _ in range(n):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def scrape(config: dict) -> list[dict]:
    today = date.today()
    results = []

    # Retail Sales Monitor — el mes de referencia es siempre el mes ANTERIOR
    # al mes de publicación (ej: el monitor de "agosto" sale en septiembre).
    # Generamos para los próximos meses dentro del broad_window.
    months_ahead = max(1, config["broad_window_days"] // 28 + 1)
    for y, m in _next_n_months(date(today.year, today.month, 1), months_ahead):
        ref_month_end = _last_day_of_month(y, m)
        publish_date = _add_working_days(ref_month_end, 7)

        if publish_date < today:
            continue

        ref_month_name = ref_month_end.strftime("%B %Y")
        ev = new_event(
            source="brc",
            category="informe",
            title=f"BRC-KPMG Retail Sales Monitor — {ref_month_name}",
            date=publish_date.strftime("%Y-%m-%d"),
            registration_required=False,
            summary=(
                f"Informe mensual de ventas retail UK (BRC-KPMG), dato de referencia {ref_month_name}. "
                f"Fecha ESTIMADA (~7 días hábiles tras cierre de mes) — confirmar contra brc.org.uk cerca de la fecha."
            ),
            detail_url="https://brc.org.uk/market-intelligence/publications/monitors/",
        )
        ev["needs_confirmation"] = True
        results.append(ev)

    return results


if __name__ == "__main__":
    import json
    with open("../agenda_config.json", encoding="utf-8") as f:
        cfg = json.load(f)
    out = scrape(cfg)
    print(f"{len(out)} fechas estimadas de informes BRC")
    print(json.dumps(out, indent=2, ensure_ascii=False))
