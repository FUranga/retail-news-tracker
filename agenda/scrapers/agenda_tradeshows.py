"""
Fuente 7: ferias sectoriales de retail UK (Spring Fair, Autumn Fair — NEC
Birmingham). No hay RSS/API — se extrae el rango de fechas publicado en la
home de cada sitio oficial via regex (patrón "D-D Month YYYY" o
"D Month-D Month YYYY"), en vez de hardcodear fechas adivinadas: si el
patrón no aparece (rediseño del sitio, feria descontinuada), la fuente
devuelve 0 eventos en vez de una fecha inventada.

Ampliar esta lista según haga falta — cualquier feria sectorial con
fechas publicadas en su propia home sirve con el mismo patrón.
"""

import re
from datetime import date, datetime, timedelta

import requests

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agenda_schema import new_event

HEADERS = {"User-Agent": "retail-news-tracker-agenda/1.0"}

SHOWS = [
    {
        "id": "spring_fair",
        "title": "Spring Fair (NEC Birmingham)",
        "url": "https://www.springfair.com/",
        "summary": "Feria de compras mayoristas de gran consumo/regalos — una de las citas anuales más grandes del retail independiente UK.",
    },
    {
        "id": "autumn_fair",
        "title": "Autumn Fair (NEC Birmingham)",
        "url": "https://www.autumnfair.com/",
        "summary": "Edición de otoño de la feria de compras mayoristas de gran consumo/regalos en NEC Birmingham.",
    },
]

MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December"
)

# "7-10 February 2027" o "7–10 February 2027" o "6 September-9 September 2026"
DATE_RANGE_PATTERN = re.compile(
    rf"(\d{{1,2}})\s*[-–]\s*(\d{{1,2}})\s+({MONTHS})\s+(20\d\d)"
)


def _extract_first_day(html: str):
    m = DATE_RANGE_PATTERN.search(html)
    if not m:
        return None
    start_day, _end_day, month_name, year = m.groups()
    try:
        return datetime.strptime(f"{start_day} {month_name} {year}", "%d %B %Y").date()
    except ValueError:
        return None


def scrape(config: dict) -> list[dict]:
    today = date.today()
    horizon = today + timedelta(days=config.get("broad_window_days", 90))
    results = []

    for show in SHOWS:
        try:
            resp = requests.get(show["url"], headers=HEADERS, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[agenda_tradeshows] error bajando {show['id']}: {e}")
            continue

        start_date = _extract_first_day(resp.text)
        if not start_date:
            print(f"[agenda_tradeshows] no encontré un rango de fechas reconocible en {show['url']} — salteando (no invento fecha)")
            continue

        if not (today <= start_date <= horizon):
            continue

        results.append(new_event(
            source="tradeshows",
            category="evento-sectorial",
            title=show["title"],
            date=start_date.strftime("%Y-%m-%d"),
            registration_required=False,
            summary=show["summary"],
            detail_url=show["url"],
        ))

    return results


if __name__ == "__main__":
    import json
    with open("../agenda_config.json", encoding="utf-8") as f:
        cfg = json.load(f)
    out = scrape(cfg)
    print(f"{len(out)} ferias encontradas dentro de la ventana")
    print(json.dumps(out, indent=2, ensure_ascii=False))
