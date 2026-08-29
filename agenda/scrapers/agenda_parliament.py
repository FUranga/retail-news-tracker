"""
Fuente 2: UK Parliament — sesiones públicas de comités relevantes.

Confirmado en vivo (29/08/2026) contra committees-api.parliament.uk:
  - Business and Trade Committee → id 365
  - Treasury Committee → id 158
  - Housing, Communities and Local Government Committee → id 17
    (nombre actual — antes "Levelling Up, Housing and Communities")

El endpoint /api/Events?CommitteeId=X devuelve eventos SIN respetar
confiablemente FromDate/ToDate (probado: pidiendo desde 2026-08-29 trajo
un evento de 2026-07-14) — así que filtramos la fecha nosotros mismos
en Python en vez de confiar en esos query params.

Campos reales del evento (no lo que asumí originalmente):
  - "startDate" (no "date"/"Date") — formato "2026-07-14T13:00:00"
  - "location" — string plano, ej "The Wilson Room, Portcullis House"
  - "name" — a veces null; cuando es null, el título real está en
    committeeBusinesses[0]["title"]
"""

import requests
from datetime import datetime, timedelta

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agenda_schema import new_event, matches_keywords

API_BASE = "https://committees-api.parliament.uk/api"
HEADERS = {"User-Agent": "retail-news-tracker-agenda/1.0"}

COMMITTEES = {
    "business_and_trade": 365,
    "treasury": 158,
    "levelling_up_housing_communities": 17,
}


def _event_title(item: dict) -> str:
    if item.get("name"):
        return item["name"]
    businesses = item.get("committeeBusinesses") or []
    if businesses and businesses[0].get("title"):
        return businesses[0]["title"]
    event_type = (item.get("eventType") or {}).get("name")
    return event_type or "Sesión de comité"


def scrape(config: dict) -> list[dict]:
    keywords = config["keywords_retail"]
    committee_ids = config["sources"][3].get("committee_ids", COMMITTEES)

    now = datetime.now()
    horizon = now + timedelta(days=config["broad_window_days"])

    results = []

    for label, cid in committee_ids.items():
        if not cid:
            continue
        try:
            resp = requests.get(
                f"{API_BASE}/Events",
                params={"CommitteeId": cid},
                headers=HEADERS, timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"[agenda_parliament] error trayendo eventos de {label} (id={cid}): {e}")
            continue

        items = data.get("items") or []
        for item in items:
            start_raw = item.get("startDate")
            if not start_raw:
                continue
            try:
                dt = datetime.fromisoformat(start_raw)
            except ValueError:
                continue

            # filtro de fecha manual — la API no lo hace confiablemente
            if not (now.date() <= dt.date() <= horizon.date()):
                continue

            title = _event_title(item)
            businesses = item.get("committeeBusinesses") or []
            business_summary = businesses[0].get("title", "") if businesses else ""
            haystack = f"{title} {business_summary}"

            # los 3 comités elegidos ya son de por sí relevantes para
            # economía/negocios/vivienda, así que priorizamos coincidencia
            # explícita de retail pero sin ser demasiado estrictos
            if not matches_keywords(
                haystack,
                keywords + ["business rates", "high street", "consumer", "retail", "cost of living"]
            ):
                continue

            location = item.get("location")
            event_type_name = (item.get("eventType") or {}).get("name", "")

            results.append(new_event(
                source="parliament_committees",
                category="reunion-publica",
                title=title,
                date=dt.strftime("%Y-%m-%d"),
                time=dt.strftime("%H:%M"),
                location=location,
                registration_required=False,
                summary=f"{event_type_name} — {business_summary}".strip(" —") or None,
                detail_url=f"https://committees.parliament.uk/committee/{cid}/",
            ))

    return results


if __name__ == "__main__":
    import json
    with open("../agenda_config.json", encoding="utf-8") as f:
        cfg = json.load(f)
    out = scrape(cfg)
    print(f"{len(out)} eventos de Parlamento encontrados")
    print(json.dumps(out[:3], indent=2, ensure_ascii=False))
