"""
Agregar un evento a mano a manual_events.json — para lo que te llega por
mail/WhatsApp/lo que sea y no lo detecta ningún scraper.

Uso interactivo:
    python add_manual_event.py

O directo por flags (útil si después lo querés invocar desde un shortcut):
    python add_manual_event.py --title "Mesa de diálogo sector textil" \
        --date 2026-09-15 --time 10:00 --location "Cámara Argentina de Comercio" \
        --category reunion-publica --registration --cost gratis \
        --link https://ejemplo.com/inscripcion
"""

import argparse
import json
from pathlib import Path

from agenda_schema import new_event

MANUAL_PATH = Path("manual_events.json")

CATEGORIES = ["estadistica", "earnings", "informe", "reunion-publica", "evento-sectorial"]


def prompt(label, default=None, required=False):
    suffix = f" [{default}]" if default else ""
    while True:
        val = input(f"{label}{suffix}: ").strip()
        if not val and default is not None:
            return default
        if not val and required:
            print("  (obligatorio)")
            continue
        return val or None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--title")
    parser.add_argument("--date")  # YYYY-MM-DD
    parser.add_argument("--time")
    parser.add_argument("--location")
    parser.add_argument("--company")
    parser.add_argument("--category", choices=CATEGORIES)
    parser.add_argument("--registration", action="store_true")
    parser.add_argument("--cost")  # gratis | pago | None
    parser.add_argument("--link")
    parser.add_argument("--agenda-link")
    parser.add_argument("--to-cover", action="store_true")
    args = parser.parse_args()

    interactive = args.title is None

    if interactive:
        print("=== Nuevo evento manual ===")
        title = prompt("Título", required=True)
        date = prompt("Fecha (YYYY-MM-DD)", required=True)
        time = prompt("Hora (HH:MM, opcional)")
        location = prompt("Lugar (opcional)")
        company = prompt("Empresa relacionada (opcional)")
        category = prompt(f"Categoría {CATEGORIES}", default="evento-sectorial")
        reg = prompt("¿Requiere inscripción? (s/n)", default="n").lower().startswith("s")
        cost = prompt("Costo (gratis/pago, opcional)") if reg else None
        link = prompt("Link de inscripción (opcional)")
        agenda_link = prompt("Link a agenda/material (opcional)")
        to_cover = prompt("¿Marcar como 'a cubrir'? (s/n)", default="n").lower().startswith("s")
    else:
        title, date, time, location, company = args.title, args.date, args.time, args.location, args.company
        category = args.category or "evento-sectorial"
        reg, cost, link, agenda_link, to_cover = args.registration, args.cost, args.link, args.agenda_link, args.to_cover

    ev = new_event(
        source="manual",
        category=category,
        title=title,
        date=date,
        time=time,
        location=location,
        company=company,
        registration_required=reg,
        registration_cost=cost,
        registration_link=link,
        agenda_link=agenda_link,
    )
    ev["manual"] = True
    ev["to_cover"] = to_cover

    events = json.loads(MANUAL_PATH.read_text(encoding="utf-8")) if MANUAL_PATH.exists() else []
    events.append(ev)
    MANUAL_PATH.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nAgregado: {ev['title']} ({ev['date']}) — id {ev['id']}")


if __name__ == "__main__":
    main()
