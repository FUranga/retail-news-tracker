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


def is_relevant(title, summary, retailer_names, keywords):
    """Devuelve True si el artículo menciona un retailer o contiene una keyword."""
    text = (title + " " + (summary or "")).lower()
    for name in retailer_names:
        if name in text:
            return True, f"retailer:{name}"
    for kw in keywords:
        if kw.lower() in text:
            return True, f"keyword:{kw}"
    return False, None


def clean_html(raw):
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:1000]  # cap summary a 1000 chars


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

    min_tier = config.get("filtering", {}).get("min_tier", 2)
    use_kw   = config.get("filtering", {}).get("use_keywords", True)

    retailer_names = build_retailer_set(retailers, min_tier)
    keywords       = retailers.get("keywords", []) if use_kw else []

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

        for a in articles:
            if a["url"] in existing_ids:
                continue  # ya lo tenemos

            relevant, match = is_relevant(a["title"], a["summary"], retailer_names, keywords)
            if not relevant:
                continue

            a["match_reason"] = match
            a["stream"]       = "news"
            a["story_type"]   = None  # se asigna en la capa de AI on-demand
            a["is_noise"]     = False
            new_items.append(a)
            existing_ids.add(a["url"])

        time.sleep(SLEEP)

    # Acumular contra el histórico existente
    all_items = existing.get("items", []) + new_items
    all_items.sort(key=lambda x: x.get("datetime", ""), reverse=True)

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
