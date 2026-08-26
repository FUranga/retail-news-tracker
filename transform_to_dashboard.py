"""
Transforms the LSE scraper CSV into the JSON that dashboard.html consumes.
100% Colab/Actions, no AI at run time — categorisation is config-driven and
deterministic. The one place AI enters is on-demand, off to the side: see
"AMBIGUOUS LAYER" below.

Three files, three jobs (same parametrisation pattern as lse_config.json):

- category_map.json   Code -> (story type, is_noise). Editable without
                       touching this script. Deliberately does NOT include
                       catch-all codes (e.g. "MSC" = Miscellaneous) — those
                       say nothing reliable about content by code alone.
- article_overrides.json   Per-article overrides, keyed by article id.
                       This is where a Claude-assisted review pass writes
                       its judgement for catch-all/ambiguous codes, or for
                       any item worth overriding individually. Takes
                       priority over category_map.json. Never auto-written
                       by this script — only by a human or an on-demand
                       Claude pass reading unmapped_categories.json / the
                       "Other" queue.
- unmapped_categories.json   Auto-maintained log of codes seen that aren't
                       in category_map.json yet. This is the queue: every
                       code (and article id) that lands here is a candidate
                       for either a permanent category_map.json entry or a
                       one-off article_overrides.json entry.

AMBIGUOUS LAYER (by design, not automatic):
Nothing in this script calls any AI. The unmapped/ambiguous queue just
accumulates in unmapped_categories.json. Reviewing it — and deciding
whether a code deserves a permanent mapping or each article needs its own
judgement — is something you bring to a Claude conversation when you want
to, exactly like the drafting step. That review produces
article_overrides.json entries, which this script then honours on the
next run.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Fallback embedded default — used only if category_map.json is missing,
# same cascade pattern as the LSE config (external file always preferred).
DEFAULT_CATEGORY_MAP = {
    "POS": ["Buyback", True],
    "HOL": ["Holding", True],
    "DSH": ["Director Dealing", False],
    "NOR": ["Notice of Results", False],
    "FR":  ["Results", False],
    "TST": ["Trading Update", False],
    "ACQ": ["M&A", False],
}

CATEGORY_MAP_PATH = Path("category_map.json")
ARTICLE_OVERRIDES_PATH = Path("article_overrides.json")
UNMAPPED_LOG_PATH = Path("unmapped_categories.json")
SECTOR_CONFIG_PATH = Path("sector_config.json")


def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] No se pudo leer {path}, uso default: {e}")
    return default


def get_retail_sector(companyname, sector_config):
    """Asigna categoría editorial de sector a partir del nombre de empresa."""
    if not companyname or not sector_config:
        return None
    mapping = sector_config.get("retailer_categories", {})
    return mapping.get(companyname)


def classify(article_id, code, title, category_map, article_overrides):
    """Devuelve (story_type, is_noise, reviewed_by, note) para un artículo,
    en orden de prioridad: override por artículo > mapa de categoría > 'Other'."""
    key = str(article_id)
    if key in article_overrides:
        ov = article_overrides[key]
        return (
            ov.get("story_type", "Other"),
            ov.get("is_noise", False),
            ov.get("reviewed_by"),
            ov.get("note"),
        )
    if code in category_map:
        story_type, is_noise = category_map[code]
        return (story_type, is_noise, None, None)
    return ("Other", False, None, None)


def log_unmapped(unmapped_log, code, title, article_id):
    """Acumula códigos sin mapear — no pisa lo que ya está, solo suma."""
    if not code:
        return unmapped_log
    entry = unmapped_log.get(code, {"count": 0, "examples": [], "first_seen": datetime.now().isoformat(timespec="seconds")})
    entry["count"] += 1
    ex = {"id": article_id, "title": title}
    if ex not in entry["examples"]:
        entry["examples"] = (entry["examples"] + [ex])[-5:]  # guarda hasta 5 ejemplos
    unmapped_log[code] = entry
    return unmapped_log


def transform(csv_path, out_path="dashboard_data.json"):
    df = pd.read_csv(csv_path)

    category_map = load_json(CATEGORY_MAP_PATH, DEFAULT_CATEGORY_MAP)
    article_overrides = load_json(ARTICLE_OVERRIDES_PATH, {})
    unmapped_log = load_json(UNMAPPED_LOG_PATH, {})
    sector_config = load_json(SECTOR_CONFIG_PATH, {})

    new_items = []
    for _, r in df.iterrows():
        code = r.get("category") if pd.notna(r.get("category")) else None
        article_id = int(r["id"]) if pd.notna(r.get("id")) else None
        title = (r.get("title") or "").strip()

        story_type, is_noise, reviewed_by, note = classify(
            article_id, code, title, category_map, article_overrides
        )

        # Solo logueamos como "no mapeado" si no vino de un override manual
        # y el código no está en el mapa — es decir, cayó en "Other" solo.
        if story_type == "Other" and str(article_id) not in article_overrides:
            unmapped_log = log_unmapped(unmapped_log, code, title, article_id)

        companyname = r.get("companyname") if pd.notna(r.get("companyname")) else None
        item = {
            "id": article_id,
            "datetime": str(r.get("datetime")),
            "title": title,
            "companyname": companyname,
            "companycode": r.get("companycode") if pd.notna(r.get("companycode")) else None,
            "category": code,
            "icbsector": r.get("icbsector") if pd.notna(r.get("icbsector")) else None,
            "retail_sector": get_retail_sector(companyname, sector_config),
            "body": r.get("body") if pd.notna(r.get("body")) else None,
            "source": "LSE",
            "stream": "press_release",
            "story_type": story_type,
            "is_noise": is_noise,
            "paywall": False,
            "url": r.get("url") if pd.notna(r.get("url")) else None,
        }
        if reviewed_by:
            item["reviewed_by"] = reviewed_by
        if note:
            item["review_note"] = note
        new_items.append(item)

    # Acumular contra lo que ya existe (registro histórico), dedup por id.
    existing_items = []
    out_file = Path(out_path)
    if out_file.exists():
        try:
            existing_payload = json.loads(out_file.read_text(encoding="utf-8"))
            existing_items = existing_payload.get("items", [])
        except Exception as e:
            print(f"[WARN] No se pudo leer {out_path} existente, arranco de cero: {e}")

    merged = {item["id"]: item for item in existing_items if item.get("id") is not None}
    for item in new_items:
        if item["id"] is not None:
            merged[item["id"]] = item

    items = sorted(merged.values(), key=lambda x: x["datetime"], reverse=True)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "items": items,
    }
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    UNMAPPED_LOG_PATH.write_text(json.dumps(unmapped_log, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{len(new_items)} items nuevos procesados, {len(items)} items totales en {out_path}")
    noise = sum(1 for i in items if i["is_noise"])
    other = sum(1 for i in items if i["story_type"] == "Other")
    print(f"  {noise} flagged as regulatory noise, {len(items)-noise} as potential news")
    if other:
        print(f"  {other} item(s) still unclassified ('Other') — see {UNMAPPED_LOG_PATH} for the review queue")
    return payload


if __name__ == "__main__":
    csv = sys.argv[1] if len(sys.argv) > 1 else "lse_latest.csv"
    transform(csv)
