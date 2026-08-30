"""
Fuente 6: Bank of England — fechas del Monetary Policy Committee (MPC).

Las decisiones de tasas de interés del BoE mueven directamente el gasto de
consumo/crédito — alto impacto editorial para retail aunque no sea un
evento "de retail" en sí.

No hay RSS/API — se parsea la tabla HTML pública de fechas confirmadas y
provisionales (agrupadas por año bajo un <h2>YYYY ...</h2>), que el BoE
mantiene actualizada con 1-2 años de anticipación. Sin scraping de HTML
frágil de terceros: es la fuente oficial y el formato (tabla simple bajo
un h2 con el año) es estable.
"""

import re
from datetime import datetime, date, timedelta

import requests

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agenda_schema import new_event

URL = "https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates"
HEADERS = {"User-Agent": "retail-news-tracker-agenda/1.0"}

MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December"
)


def _parse_dates(html: str) -> list[dict]:
    """Devuelve [{"date": "YYYY-MM-DD"}] parseando los bloques
    <h2>YYYY ...</h2><table>...<td>Weekday D Month</td>...</table>."""
    results = []
    # Cada bloque: un h2 con el año, seguido del primer <table> que aparece.
    blocks = re.split(r"<h2>(\d{4})[^<]*</h2>", html)[1:]  # descarta preámbulo
    # re.split con grupo de captura intercala: [year, resto_html, year, resto_html, ...]
    for i in range(0, len(blocks) - 1, 2):
        year = int(blocks[i])
        chunk = blocks[i + 1]
        table_match = re.search(r"<table>.*?</table>", chunk, re.DOTALL)
        if not table_match:
            continue
        table_html = table_match.group(0)
        for cell in re.findall(r"<td>([^<]+)</td>", table_html):
            cell = cell.replace("&nbsp;", " ").strip()
            m = re.search(rf"(\d{{1,2}})\s+({MONTHS})", cell)
            if not m:
                continue
            day = int(m.group(1))
            month_name = m.group(2)
            try:
                dt = datetime.strptime(f"{day} {month_name} {year}", "%d %B %Y").date()
            except ValueError:
                continue
            results.append({"date": dt})
    return results


def scrape(config: dict) -> list[dict]:
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[agenda_boe] error bajando la página de fechas del BoE: {e}")
        return []

    try:
        raw_dates = _parse_dates(resp.text)
    except Exception as e:
        print(f"[agenda_boe] error parseando la tabla de fechas: {e}")
        return []

    today = date.today()
    horizon_days = config.get("broad_window_days", 90)
    horizon = today + timedelta(days=horizon_days)

    results = []
    for d in raw_dates:
        dt = d["date"]
        if not (today <= dt <= horizon):
            continue
        results.append(new_event(
            source="boe",
            category="macro",
            title="Bank of England — MPC rate decision",
            date=dt.strftime("%Y-%m-%d"),
            registration_required=False,
            summary=(
                "El Comité de Política Monetaria del Banco de Inglaterra anuncia "
                "su decisión de tasa de interés — impacto directo en gasto de "
                "consumo, crédito e hipotecas."
            ),
            detail_url=URL,
        ))

    return results


if __name__ == "__main__":
    import json
    with open("../agenda_config.json", encoding="utf-8") as f:
        cfg = json.load(f)
    out = scrape(cfg)
    print(f"{len(out)} fechas de MPC encontradas")
    print(json.dumps(out, indent=2, ensure_ascii=False))
