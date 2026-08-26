"""
Scraper de medios UK — Módulo 2 del tracker de retail
Lee media_config.json, captura artículos via RSS (+ scraping donde aplique),
filtra por retailers.json y keywords, y acumula en media_data.json.

100% Python/Colab — sin AI, sin tokens.
Corre a las 6:30, 7:05, 11:00, 14:00 y 16:00 via GitHub Actions.
"""

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

try:
    import feedparser
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "feedparser", "-q"])
    import feedparser

MEDIA_CONFIG_PATH = Path("media_config.json")
RETAILERS_PATH    = Path("retailers.json")
MEDIA_DATA_PATH   = Path("media_data.json")
SECTOR_CONFIG_PATH = Path("sector_config.json")
SLEEP             = 1.0   # segundos entre requests — buen ciudadano

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
}


def load_json(path, default=None):
    if Path(path).exists():
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] No se pudo leer {path}: {e}")
    return default if default is not None else {}


def build_retailer_set(retailers_data, min_tier=2):
    """Construye un set de nombres de retailers hasta min_tier inclusive."""
    names = set()
    tiers = ["tier1", "tier2"] if min_tier >= 2 else ["tier1"]
    if min_tier >= 3:
        tiers.append("tier3")
    for tier in tiers:
        for r in retailers_data.get(tier, []):
            name = r.get("name", "")
            if name:
                names.add(name.lower())
    return names


def get_retail_sector(title, summary, match_reason, sector_config):
    """Asigna categoría editorial de sector a un artículo de noticias.
    Primero intenta via el retailer mencionado (match_reason), luego por keywords."""
    if not sector_config:
        return None
    retailer_map = sector_config.get("retailer_categories", {})
    kw_map = sector_config.get("keyword_categories", {})

    # Si el match fue por un retailer conocido, usar su categoría
    if match_reason and match_reason.startswith("retailer:"):
        name = match_reason.split("retailer:")[1].split(" (")[0].strip()
        # Buscar en el mapa (case-insensitive)
        for retailer, cat in retailer_map.items():
            if retailer.lower() == name.lower():
                return cat

    # Si no, buscar por keywords en el título + summary
    text = ((title or "") + " " + (summary or "")).lower()
    for cat_id, kws in kw_map.items():
        if any(kw.lower() in text for kw in kws):
            return cat_id

    return None


def build_retailer_sets(retailers_data, min_tier=2):
    """Construye dos sets: nombres claros y nombres ambiguos."""
    clear = set()
    ambiguous = set()
    tiers = ["tier1", "tier2"] if min_tier >= 2 else ["tier1"]
    if min_tier >= 3:
        tiers.append("tier3")
    for tier in tiers:
        for r in retailers_data.get(tier, []):
            name = r.get("name", "").lower()
            if not name:
                continue
            if r.get("ambiguous"):
                ambiguous.add(name)
            else:
                clear.add(name)
    return clear, ambiguous


def is_relevant(title, summary, clear_names, ambiguous_names, keywords, context_keywords):
    """Devuelve (relevant, reason).
    - Nombres claros: match directo con word boundary.
    - Nombres ambiguos: solo matchean si el texto también contiene
      al menos una context_keyword (señal de que es contexto retail).
    - Keywords: match directo.
    """
    text = (title + " " + (summary or "")).lower()

    # Nombres claros — match directo
    for name in clear_names:
        if re.search(r'\b' + re.escape(name), text):
            return True, f"retailer:{name}"

    # Nombres ambiguos — requieren contexto retail adicional
    has_context = any(ck in text for ck in context_keywords)
    if has_context:
        for name in ambiguous_names:
            if re.search(r'\b' + re.escape(name), text):
                return True, f"retailer:{name} (context)"

    # Keywords específicas
    for kw in keywords:
        if kw.lower() in text:
            return True, f"keyword:{kw}"

    return False, None


try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False


def fetch_full_body(url, paywall=False):
    """Intenta bajar el texto completo del artículo para medios sin paywall.
    Devuelve el texto limpio o None si falla / es basura."""
    if paywall or not url or not TRAFILATURA_AVAILABLE:
        return None
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        text = trafilatura.extract(resp.text)
        if not text or len(text) < 300:
            return None
        garbage_signals = ["access denied", "englishunited states", "deutsch\n- english\n- español"]
        if any(sig in text.lower()[:200] for sig in garbage_signals):
            return None
        return text
    except Exception:
        return None


def clean_html(raw):
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:1000]


def fetch_rss(source):
    """Parsea un feed RSS y devuelve lista de artículos."""
    try:
        resp = requests.get(source["rss"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        articles = []
        for entry in feed.entries:
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            if pub:
                dt = datetime(*pub[:6]).isoformat()
            else:
                dt = datetime.now().isoformat()

            articles.append({
                "source_id":    source["id"],
                "source_name":  source["name"],
                "source_cat":   source["category"],
                "paywall":      source.get("paywall", False),
                "title":        entry.get("title", "").strip(),
                "url":          entry.get("link", ""),
                "summary":      clean_html(entry.get("summary", "")),
                "datetime":     dt,
            })
        return articles
    except Exception as e:
        print(f"  [WARN] {source['name']}: {e}")
        return []


def fetch_source(source):
    """Despacha al método correcto según source['method']."""
    method = source.get("method", "rss")
    if method == "rss" and source.get("rss"):
        return fetch_rss(source)
    elif method == "scrape":
        print(f"  [SKIP] {source['name']}: scraping no implementado todavía")
        return []
    elif method == "api":
        print(f"  [SKIP] {source['name']}: API no implementada todavía")
        return []
    else:
        print(f"  [SKIP] {source['name']}: sin método de captura válido")
        return []


def run():
    config   = load_json(MEDIA_CONFIG_PATH)
    retailers = load_json(RETAILERS_PATH)
    existing  = load_json(MEDIA_DATA_PATH, {"items": [], "generated_at": None})
    sector_config = load_json(SECTOR_CONFIG_PATH, {})

    min_tier = config.get("filtering", {}).get("min_tier", 2)
    use_kw   = config.get("filtering", {}).get("use_keywords", True)
    max_per_source = config.get("filtering", {}).get("max_per_source", 50)

    clear_names, ambiguous_names = build_retailer_sets(retailers, min_tier)
    keywords        = retailers.get("keywords", []) if use_kw else []
    context_keywords = retailers.get("ambiguous_context_keywords", [])

    existing_ids = {item["url"] for item in existing.get("items", []) if item.get("url")}
    new_items    = []
    total_fetched = 0

    for source in config.get("sources", []):
        if not source.get("rss") and source.get("method") == "rss":
            print(f"  [SKIP] {source['name']}: sin URL de RSS")
            continue

        print(f"  Fetching: {source['name']}...")
        articles = fetch_source(source)
        total_fetched += len(articles)

        source_new = 0
        for a in articles:
            if source_new >= max_per_source:
                break

            relevant, match = is_relevant(
                a["title"], a["summary"],
                clear_names, ambiguous_names,
                keywords, context_keywords
            )
            if not relevant:
                continue

            # Si ya existe en el histórico, solo actualizar el body si falta
            if a["url"] in existing_ids:
                existing_item = next((i for i in existing.get("items", []) if i.get("url") == a["url"]), None)
                if existing_item and not existing_item.get("body"):
                    full_body = fetch_full_body(a.get("url"), paywall=source.get("paywall", False))
                    if full_body:
                        existing_item["body"] = full_body
                continue

            a["match_reason"]  = match
            a["stream"]        = "news"
            a["story_type"]    = None
            a["is_noise"]      = False
            a["retail_sector"] = get_retail_sector(a["title"], a.get("summary",""), match, sector_config)
            full_body = fetch_full_body(a.get("url"), paywall=source.get("paywall", False))
            a["body"] = full_body
            new_items.append(a)
            existing_ids.add(a["url"])
            source_new += 1

        time.sleep(SLEEP)

    # Acumular contra el histórico existente
    all_items = existing.get("items", []) + new_items
    all_items.sort(key=lambda x: x.get("datetime", ""), reverse=True)

    # Purgar artículos más viejos que keep_days
    keep_days = config.get("retention", {}).get("keep_days", 7)
    cutoff = (datetime.now() - timedelta(days=keep_days)).isoformat()
    before_purge = len(all_items)
    all_items = [i for i in all_items if i.get("datetime", "") >= cutoff]
    purged = before_purge - len(all_items)
    if purged:
        print(f"{purged} artículos purgados (más de {keep_days} días)")

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "items": all_items,
    }
    MEDIA_DATA_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\nFetched {total_fetched} artículos de {len(config.get('sources', []))} fuentes")
    print(f"{len(new_items)} nuevos relevantes para retail")
    print(f"{len(all_items)} artículos totales en {MEDIA_DATA_PATH}")
    return payload


if __name__ == "__main__":
    run()
