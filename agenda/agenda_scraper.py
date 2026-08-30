"""
Orquestador del Módulo 7 (Agenda).

Corre 1 vez/día (mismo patrón de GitHub Actions que los otros módulos).
Combina:
  - radar amplio: todo evento detectado dentro de broad_window_days (90 por
    defecto), con el nivel de detalle que cada fuente pueda dar de entrada.
  - pasada granular: para eventos dentro de granular_window_days (14 por
    defecto), se re-scrapean las fuentes que pueden dar más detalle
    (inscripción, agenda, materiales) — hoy ONS y Parlamento ya traen esto
    en la primera pasada; BRC es la que más se beneficia de un segundo paso
    focalizado si hace falta más adelante.

Preserva:
  - to_cover / manual / research_summary de eventos ya existentes en
    agenda_data.json (no se pisan al re-scrapear).
  - todos los eventos manuales de manual_events.json, siempre.

Uso:
    python agenda_scraper.py
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schedule_guard import should_run  # noqa: E402 — vive en la raíz del repo, no en agenda/

from scrapers import agenda_ons, agenda_parliament, agenda_lse_earnings, agenda_company_ir, agenda_brc
from agenda_ics import generate_ics

CONFIG_PATH = Path("agenda_config.json")

SCRAPERS = {
    "ons": agenda_ons,
    "parliament_committees": agenda_parliament,
    "lse_earnings": agenda_lse_earnings,
    "company_ir": agenda_company_ir,
    "brc": agenda_brc,
}


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_existing(output_path: Path) -> dict:
    if output_path.exists():
        return {e["id"]: e for e in json.loads(output_path.read_text(encoding="utf-8"))}
    return {}


def load_manual(manual_path: Path) -> list[dict]:
    if manual_path.exists():
        return json.loads(manual_path.read_text(encoding="utf-8"))
    return []


def merge_event(new_ev: dict, existing: dict) -> dict:
    """Un evento re-scrapeado no debe perder las decisiones editoriales
    tomadas en el dashboard (to_cover, research_summary)."""
    old = existing.get(new_ev["id"])
    if old:
        new_ev["to_cover"] = old.get("to_cover", False)
        new_ev["research_summary"] = old.get("research_summary")
    return new_ev


def prune_past(events: list[dict], retention_days_past: int) -> list[dict]:
    cutoff = (datetime.now() - timedelta(days=retention_days_past)).strftime("%Y-%m-%d")
    return [e for e in events if e["date"] >= cutoff]


def run():
    config = load_config()

    if not should_run(config.get("schedule", {}).get("runs_uk", [])):
        print("[agenda_scraper] fuera de ventana horaria UK, no corro esta vez")
        return

    output_path = Path(config["output_file"])
    manual_path = Path(config["manual_file"])

    existing = load_existing(output_path)
    all_events = []
    total_found = 0
    sources_run = 0

    for source_cfg in config["sources"]:
        sid = source_cfg["id"]
        if not source_cfg.get("enabled", True):
            continue
        scraper = SCRAPERS.get(sid)
        if not scraper:
            print(f"[agenda_scraper] no hay implementación para fuente '{sid}', salteando")
            continue
        sources_run += 1
        print(f"[agenda_scraper] corriendo fuente: {sid}")
        try:
            found = scraper.scrape(config)
        except Exception as e:
            print(f"[agenda_scraper] fuente '{sid}' falló: {e}")
            found = []
        print(f"  -> {len(found)} eventos")
        total_found += len(found)
        all_events.extend(merge_event(ev, existing) for ev in found)

    if sources_run and total_found == 0:
        print(f"[HEALTH] 0 eventos encontrados en {sources_run} fuentes habilitadas "
              f"— revisar si alguna dejó de responder (endpoints de Parlamento/ONS "
              f"cambian con más frecuencia que un RSS estándar).")

    # eventos manuales siempre entran, sin pasar por merge (ya vienen con su
    # propio to_cover/research_summary si el usuario los seteó)
    manual_events = load_manual(manual_path)
    for ev in manual_events:
        ev["manual"] = True
    all_events.extend(manual_events)

    # dedupe por id (por si dos fuentes detectan el mismo evento)
    dedup = {e["id"]: e for e in all_events}
    final_events = list(dedup.values())

    final_events = prune_past(final_events, config["retention_days_past"])
    final_events.sort(key=lambda e: (e["date"], e.get("time") or "99:99"))

    output_path.write_text(json.dumps(final_events, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[agenda_scraper] {len(final_events)} eventos totales escritos en {output_path}")

    ics_path = config.get("ics_output")
    if ics_path:
        generate_ics(final_events, ics_path)


if __name__ == "__main__":
    run()
