"""
Fuente 1: ONS release calendar.

Dos vías combinadas:
  - RSS con query param de keyword (?query=retail&release-type=type-upcoming)
    -> liviano, sirve para el barrido amplio (broad radar).
  - iCal completo (/calendar/releasecalendar) -> trae TODOS los releases
    confirmados con fecha exacta (DTSTART) y descripción; lo filtramos
    localmente por keyword. Mejor para la pasada granular (próximas 2 semanas)
    porque el iCal trae hora exacta y STATUS (Confirmed/Provisional).

No requiere API key. Ambos endpoints son públicos.
"""

import re
import requests
import feedparser
from datetime import datetime, timezone

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agenda_schema import new_event, matches_keywords

ICAL_URL = "https://www.ons.gov.uk/calendar/releasecalendar"
RSS_TEMPLATE = (
    "https://www.ons.gov.uk/releasecalendar?rss=&highlight=true&limit=40"
    "&page=1&release-type=type-upcoming&sort=date-oldest&query={keyword}"
)

HEADERS = {"User-Agent": "retail-news-tracker-agenda/1.0 (contacto: Francisco)"}


def _parse_ical(text: str) -> list[dict]:
    """Parser mínimo de VEVENT sin dependencia externa (evita agregar la lib
    'icalendar' si no hace falta). Si preferís, cambiar por `pip install icalendar`
    y usar su parser real — más robusto ante líneas plegadas (folding)."""
    events = []
    blocks = text.split("BEGIN:VEVENT")[1:]
    for block in blocks:
        block = block.split("END:VEVENT")[0]

        def field(name):
            m = re.search(rf"{name}:([^\r\n]+)", block)
            return m.group(1).strip() if m else None

        summary = field("SUMMARY")
        dtstart = field("DTSTART")
        status = field("STATUS")
        description = field("DESCRIPTION") or ""
        uid = field("UID") or ""

        if not summary or not dtstart:
            continue

        # DTSTART viene como 20260916T083000Z
        try:
            dt = datetime.strptime(dtstart, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        events.append({
            "title": summary,
            "date": dt.strftime("%Y-%m-%d"),
            "time": dt.strftime("%H:%M"),
            "status": status,
            "description": description,
            "detail_url": f"https://www.ons.gov.uk{uid}" if uid.startswith("/") else uid,
        })
    return events


def scrape(config: dict) -> list[dict]:
    keywords = config["keywords_retail"]
    results = []

    # --- vía iCal (fuente principal, más completa) ---
    try:
        resp = requests.get(ICAL_URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        raw_events = _parse_ical(resp.text)
    except requests.RequestException as e:
        print(f"[agenda_ons] error bajando iCal: {e}")
        raw_events = []

    for ev in raw_events:
        haystack = f"{ev['title']} {ev['description']}"
        if not matches_keywords(haystack, keywords):
            continue
        results.append(new_event(
            source="ons",
            category="estadistica",
            title=ev["title"],
            date=ev["date"],
            time=ev["time"],
            location=None,
            registration_required=False,
            summary=ev["description"][:400] if ev["description"] else None,
            detail_url=ev["detail_url"],
        ))

    # --- vía RSS por keyword (red de seguridad — a veces el iCal tarda en actualizar) ---
    seen_titles = {r["title"] for r in results}
    for kw in keywords[:5]:  # limitar para no pegarle demasiadas veces al mismo endpoint
        url = RSS_TEMPLATE.format(keyword=kw.replace(" ", "+"))
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"[agenda_ons] error RSS keyword={kw}: {e}")
            continue
        for entry in feed.entries:
            title = entry.get("title", "")
            if title in seen_titles:
                continue
            pub = entry.get("published_parsed")
            if not pub:
                continue
            date_str = datetime(*pub[:6]).strftime("%Y-%m-%d")
            results.append(new_event(
                source="ons",
                category="estadistica",
                title=title,
                date=date_str,
                summary=entry.get("summary"),
                detail_url=entry.get("link"),
            ))
            seen_titles.add(title)

    return results


if __name__ == "__main__":
    import json
    with open("../agenda_config.json", encoding="utf-8") as f:
        cfg = json.load(f)
    out = scrape(cfg)
    print(f"{len(out)} eventos ONS encontrados")
    print(json.dumps(out[:3], indent=2, ensure_ascii=False))
