"""
Fuente 3: earnings/AGM de las COTIZADAS, sin scraping nuevo.

Reusa dashboard_data.json que ya produce el Módulo 1 (LSE RNS, sectores ICB
Retailers/Grocery/Personal Goods). La lógica es: cada vez que aparece un RNS
de resultados (prelims, interims, trading update) suele mencionar la próxima
fecha de publicación ("Next results: 14 October 2026" o similar dentro del
cuerpo). También capturamos avisos de AGM, que traen fecha y lugar.

Este scraper NO hace requests HTTP — solo lee el JSON que ya tenés en el repo.
Ajustar `DATA_PATH` y los nombres de campo (headline/body/company/date) a como
estén realmente en tu dashboard_data.json — acá asumo una forma razonable
basada en lo que describiste del Módulo 1.
"""

import json
import re
from pathlib import Path

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agenda_schema import new_event, parse_date_loose

DATA_PATH = Path("../dashboard_data.json")  # cwd al correr es agenda/ (agenda_scraper.py corre desde ahí), y dashboard_data.json vive un nivel arriba, en la raíz del repo

TRIGGER_PATTERNS = [
    r"trading (statement|update)",
    r"preliminary results",
    r"interim results",
    r"full[- ]year results",
    r"annual results",
    r"half[- ]year results",
    r"annual general meeting|\bAGM\b",
]

NEXT_DATE_HINTS = [
    r"next (?:results?|trading update|announcement)[^.\n]{0,40}?(\d{1,2}\s+\w+\s+\d{4})",
    r"will (?:report|announce|publish)[^.\n]{0,60}?(\d{1,2}\s+\w+\s+\d{4})",
    r"scheduled for[^.\n]{0,20}?(\d{1,2}\s+\w+\s+\d{4})",
]


def _find_next_date(body: str) -> str | None:
    for pat in NEXT_DATE_HINTS:
        m = re.search(pat, body, re.IGNORECASE)
        if m:
            return parse_date_loose(m.group(1))
    return None


def scrape(config: dict) -> list[dict]:
    if not DATA_PATH.exists():
        print(f"[agenda_lse_earnings] no encontré {DATA_PATH} — ajustar ruta")
        return []

    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    items = raw if isinstance(raw, list) else raw.get("items", [])

    results = []
    for item in items:
        headline = item.get("headline") or item.get("title") or ""
        body = item.get("body") or item.get("content") or ""
        company = item.get("companyname") or item.get("company") or item.get("company_name")

        if not any(re.search(p, headline, re.IGNORECASE) for p in TRIGGER_PATTERNS):
            continue

        next_date = _find_next_date(body) or _find_next_date(headline)
        if not next_date:
            continue  # sin fecha futura mencionada, no hay evento que agendar

        is_agm = bool(re.search(r"annual general meeting|\bAGM\b", headline, re.IGNORECASE))

        results.append(new_event(
            source="lse_earnings",
            category="earnings" if not is_agm else "reunion-publica",
            title=f"{company} — {'AGM' if is_agm else 'próximos resultados'}",
            date=next_date,
            company=company,
            registration_required=is_agm,
            summary=headline,
            detail_url=item.get("url") or item.get("link"),
        ))

    return results


if __name__ == "__main__":
    import json as _json
    with open("../agenda_config.json", encoding="utf-8") as f:
        cfg = _json.load(f)
    out = scrape(cfg)
    print(f"{len(out)} fechas de earnings/AGM detectadas")
    print(_json.dumps(out[:3], indent=2, ensure_ascii=False))
