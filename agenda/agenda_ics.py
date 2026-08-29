"""
Genera agenda_to_cover.ics a partir de los eventos con to_cover=true.

Se sirve como archivo estático más (GitHub Pages ya lo publica solo, igual
que agenda_data.json). Google Calendar lo puede "suscribir" por URL —
Google chequea el archivo cada tanto (típicamente cada 8-24hs, no es
instantáneo, pero como el scraper corre 1 vez/día ya alcanza) y se
actualiza solo sin que hagas nada manual.

Se llama desde agenda_scraper.py al final de cada corrida.
"""

from datetime import datetime, timedelta, timezone


def _escape_ics(text: str) -> str:
    if not text:
        return ""
    return (text.replace("\\", "\\\\").replace(";", "\\;")
                .replace(",", "\\,").replace("\n", "\\n"))


def _event_to_vevent(ev: dict) -> str:
    date = ev["date"].replace("-", "")
    uid = f"{ev['id']}@retail-news-tracker"
    now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if ev.get("time"):
        hh, mm = ev["time"].split(":")
        dtstart = f"DTSTART:{date}T{hh}{mm}00"
        # evento de 1 hora por defecto si no sabemos duración real
        end_dt = datetime.strptime(f"{ev['date']} {ev['time']}", "%Y-%m-%d %H:%M") + timedelta(hours=1)
        dtend = f"DTEND:{end_dt.strftime('%Y%m%dT%H%M00')}"
    else:
        # evento de todo el día — DTEND es el día siguiente (exclusivo, así lo pide iCal)
        next_day = (datetime.strptime(ev["date"], "%Y-%m-%d") + timedelta(days=1)).strftime("%Y%m%d")
        dtstart = f"DTSTART;VALUE=DATE:{date}"
        dtend = f"DTEND;VALUE=DATE:{next_day}"

    description_parts = []
    if ev.get("summary"):
        description_parts.append(ev["summary"])
    if ev.get("registration", {}).get("required"):
        description_parts.append(f"Inscripción: {ev['registration'].get('link') or 'requerida'}")
    if ev.get("detail_url"):
        description_parts.append(f"Fuente: {ev['detail_url']}")
    description = _escape_ics(" | ".join(description_parts))

    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now_stamp}",
        dtstart,
        dtend,
        f"SUMMARY:{_escape_ics(ev['title'])}",
    ]
    if ev.get("location"):
        lines.append(f"LOCATION:{_escape_ics(ev['location'])}")
    if description:
        lines.append(f"DESCRIPTION:{description}")
    if ev.get("detail_url"):
        lines.append(f"URL:{ev['detail_url']}")
    lines.append("END:VEVENT")
    return "\r\n".join(lines)


def generate_ics(events: list[dict], output_path: str):
    to_cover = [e for e in events if e.get("to_cover")]
    body = "\r\n".join(_event_to_vevent(ev) for ev in to_cover)
    ics = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//retail-news-tracker//agenda//ES\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "X-WR-CALNAME:Retail Wire — a cubrir\r\n"
        f"{body}\r\n"
        "END:VCALENDAR\r\n"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ics)
    print(f"[agenda_ics] {len(to_cover)} eventos 'a cubrir' escritos en {output_path}")
