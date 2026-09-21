"""
Log de auditoría de items descartados por los filtros mecánicos del pipeline.

Cambio de VISIBILIDAD pura: no decide qué se descarta (eso lo sigue
decidiendo cada scraper igual que siempre), solo deja rastro de cada
descarte para poder auditar el filtro después.

Un .jsonl append-only por módulo en data/rejected/ — no uno compartido,
mismo principio que ya rige el repo de que cada workflow solo toca su
propio archivo (evita condiciones de carrera entre workflows en paralelo).

Dos acciones posibles:
- "dropped": el item nunca llega al *_data.json / dashboard_data.json.
- "flagged_noise": el item SÍ llega, solo queda marcado is_noise=true
  (caso LSE: category_map.json / article_overrides.json).
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

REJECTED_DIR = Path("data/rejected")


def _log_path(module: str) -> Path:
    return REJECTED_DIR / f"{module}.jsonl"


def append_rejected(module: str, item: dict, reason: str, action: str = "dropped", stage: str = "scraper") -> None:
    """Agrega una línea al log de descartes de un módulo. No relee el
    archivo — se llama potencialmente cientos de veces por corrida."""
    REJECTED_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "module": module,
        "stage": stage,
        "action": action,
        "source_id": item.get("source_id"),
        "source_name": item.get("source_name"),
        "title": item.get("title"),
        "url": item.get("url"),
        "datetime": item.get("datetime"),
        "reject_reason": reason,
    }
    with _log_path(module).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def prune_rejected(module: str, keep_days: int) -> int:
    """Elimina líneas más viejas que keep_days. Devuelve cuántas se sacaron.
    Mismo patrón que la purga por fecha que ya usan los scrapers para
    all_items — se lee una vez, se reescribe filtrado."""
    path = _log_path(module)
    if not path.exists():
        return 0

    cutoff = (datetime.now().astimezone() - timedelta(days=keep_days)).isoformat()
    kept_lines = []
    pruned = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except Exception:
            pruned += 1
            continue
        if entry.get("ts", "") >= cutoff:
            kept_lines.append(line)
        else:
            pruned += 1

    if pruned:
        path.write_text("\n".join(kept_lines) + ("\n" if kept_lines else ""), encoding="utf-8")
    return pruned
