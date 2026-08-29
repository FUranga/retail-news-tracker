"""
Fuente 4: empresas PRIVADAS (Aldi UK, Lidl GB, Iceland, JLP, Home Bargains,
Poundland, Primark-vía-ABF-ojo-que-esa-es-cotizada, etc.) que no tienen RNS
en LSE, así que no aparecen en el Módulo 1/4 automáticamente.

Reusa el patrón de company_config.json (Google News RSS por empresa) pero
con una query distinta: en vez de buscar la noticia del resultado ya
publicado, busca el ANUNCIO de que van a publicar en tal fecha.

Nota de diseño: esto va a traer bastante ruido al principio (Google News no
tiene un "tipo de evento" como ONS o Parlamento). Conviene correrlo y revisar
manualmente los primeros resultados antes de dejarlo 100% automático — capaz
lo mejor es que esto alimente una cola de "candidatos" que vos confirmás con
un click, en vez de que entre directo al calendario. Lo dejo señalado como
`needs_confirmation: true` en el evento para que el dashboard lo pueda tratar
distinto (por ejemplo, mostrarlo con un ícono de "sin confirmar").
"""

import json
from pathlib import Path

import feedparser

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agenda_schema import new_event, parse_date_loose

# Privadas relevantes sin cobertura RNS — completar/ajustar según tu retailers.json
PRIVATE_COMPANIES = [
    "Aldi UK", "Lidl GB", "Iceland Foods", "John Lewis Partnership",
    "Home Bargains", "The Range", "IKEA UK", "Matalan",
]

GNEWS_TEMPLATE = (
    "https://news.google.com/rss/search?q=%22{company}%22+"
    "(%22trading+update%22+OR+%22annual+results%22+OR+%22full+year+results%22)"
    "+(announced+OR+scheduled+OR+%22will+report%22+OR+%22will+publish%22)"
    "&hl=en-GB&gl=GB&ceid=GB:en"
)


def scrape(config: dict) -> list[dict]:
    results = []
    for company in PRIVATE_COMPANIES:
        url = GNEWS_TEMPLATE.format(company=company.replace(" ", "+"))
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"[agenda_company_ir] error con {company}: {e}")
            continue

        for entry in feed.entries[:5]:  # top 5 por empresa alcanza para no saturar
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            future_date = parse_date_loose(f"{title} {summary}")
            if not future_date:
                continue

            ev = new_event(
                source="company_ir",
                category="earnings",
                title=f"{company} — anuncio de resultados",
                date=future_date,
                company=company,
                registration_required=False,
                summary=title,
                detail_url=entry.get("link"),
            )
            ev["needs_confirmation"] = True  # ver nota arriba
            results.append(ev)

    return results


if __name__ == "__main__":
    with open("../agenda_config.json", encoding="utf-8") as f:
        cfg = json.load(f)
    out = scrape(cfg)
    print(f"{len(out)} candidatos de earnings privados (sin confirmar)")
    print(json.dumps(out[:3], indent=2, ensure_ascii=False))
