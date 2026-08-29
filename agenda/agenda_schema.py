"""
Schema común de evento para el Módulo 7 (Agenda) del retail-news-tracker.

Cada scraper de fuente (agenda_ons.py, agenda_parliament.py, etc.) debe
devolver una lista de dicts con esta forma exacta, para que agenda_scraper.py
los pueda mergear con manual_events.json sin fricción.
"""

import hashlib
import re
from datetime import datetime, timezone


def make_event_id(source: str, title: str, date: str) -> str:
    """ID estable: mismo evento scrapeado dos veces = mismo id (evita duplicados)."""
    raw = f"{source}|{title.strip().lower()}|{date}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def new_event(
    source: str,
    category: str,
    title: str,
    date: str,                 # "YYYY-MM-DD"
    time: str | None = None,   # "HH:MM" o None si no se sabe
    location: str | None = None,
    company: str | None = None,
    registration_required: bool | None = None,
    registration_cost: str | None = None,   # "gratis" | "pago" | None
    registration_link: str | None = None,
    agenda_link: str | None = None,
    prior_report_link: str | None = None,
    relevance_sectors: list[str] | None = None,
    summary: str | None = None,
    detail_url: str | None = None,
) -> dict:
    return {
        "id": make_event_id(source, title, date),
        "source": source,
        "category": category,          # estadistica | earnings | informe | reunion-publica | evento-sectorial
        "title": title.strip(),
        "date": date,
        "time": time,
        "location": location,
        "company": company,
        "registration": {
            "required": registration_required,
            "cost": registration_cost,
            "link": registration_link,
        },
        "materials": {
            "agenda_link": agenda_link,
            "prior_report_link": prior_report_link,
        },
        "relevance_sectors": relevance_sectors or [],
        "summary": summary,
        "detail_url": detail_url,
        "to_cover": False,
        "manual": False,
        "research_summary": None,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def matches_keywords(text: str, keywords: list[str]) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(kw.lower() in t for kw in keywords)


def parse_date_loose(text: str) -> str | None:
    """Intenta extraer una fecha futura de un texto libre (headlines, RNS body).
    Devuelve YYYY-MM-DD o None. Cubre formatos tipo '14 October 2026',
    'Oct 14, 2026', '14/10/2026'. Ampliar según lo que aparezca en la práctica."""
    patterns = [
        (r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|"
         r"September|October|November|December)\s+(\d{4})", "%d %B %Y"),
        (r"(January|February|March|April|May|June|July|August|September|"
         r"October|November|December)\s+(\d{1,2}),?\s+(\d{4})", "%B %d %Y"),
        (r"(\d{1,2})/(\d{1,2})/(\d{4})", "%d/%m/%Y"),
    ]
    for pat, fmt in patterns:
        m = re.search(pat, text)
        if m:
            try:
                if fmt == "%B %d %Y":
                    dt = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", fmt)
                elif fmt == "%d/%m/%Y":
                    dt = datetime.strptime(m.group(0), fmt)
                else:
                    dt = datetime.strptime(m.group(0), fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None
