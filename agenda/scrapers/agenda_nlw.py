"""
Fuente 8: National Living Wage — fecha de entrada en vigencia del aumento
anual (siempre 1 de abril, fijado por ley — no requiere scraping ni
adivinar una fecha).

Deliberadamente NO incluye la tasa/porcentaje del aumento — eso lo anuncia
el gobierno en el Budget/Autumn Statement, con fecha no fija (ver nota en
CLAUDE.md/README sobre por qué ese evento no está automatizado). Poner acá
un número inventado violaría la regla de no adivinar datos — el evento
solo marca CUÁNDO entra en vigencia, no CUÁNTO va a subir.
"""

from datetime import date, timedelta

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agenda_schema import new_event


def scrape(config: dict) -> list[dict]:
    today = date.today()
    horizon = today + timedelta(days=config.get("broad_window_days", 90))
    results = []

    for year in (today.year, today.year + 1):
        effective_date = date(year, 4, 1)
        if not (today <= effective_date <= horizon):
            continue
        results.append(new_event(
            source="nlw",
            category="macro",
            title="National Living Wage increase takes effect",
            date=effective_date.strftime("%Y-%m-%d"),
            registration_required=False,
            summary=(
                "Fecha fija por ley (1 de abril) en que entra en vigencia el "
                "nuevo National Living Wage / National Minimum Wage. La tasa "
                "exacta se anuncia por separado (Budget/Autumn Statement, sin "
                "fecha fija) — no incluida acá para no inventar un número."
            ),
            detail_url="https://www.gov.uk/national-minimum-wage-rates",
        ))

    return results


if __name__ == "__main__":
    import json
    with open("../agenda_config.json", encoding="utf-8") as f:
        cfg = json.load(f)
    out = scrape(cfg)
    print(f"{len(out)} fechas de NLW dentro de la ventana")
    print(json.dumps(out, indent=2, ensure_ascii=False))
