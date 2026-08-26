"""
Scraper de fuentes gubernamentales UK — Módulo 3 del tracker de retail
Lee gov_config.json, captura artículos via RSS de fuentes oficiales,
estadísticas, regulación y parlamento, filtra por relevancia retail,
y acumula en gov_data.json.

100% Python — sin AI, sin tokens.
Corre a las 7:00, 9:45, 12:30, 14:30 y 17:30 BST via GitHub Actions.
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

GOV_CONFIG_PATH  = Path("gov_config.json")
RETAILERS_PATH   = Path("retailers.json")
SECTOR_CONFIG_PATH = Path("sector_config.json")
GOV_DATA_PATH    = Path("gov_data.json")
SLEEP            = 1.5

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


def clean_html(raw):
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:1500]


def build_retailer_names(retailers_data):
    """Set de nombres de retailers (todos los tiers)."""
    names = set()
    for tier in ["tier1", "tier2", "tier3"]:
        for r in retailers_data.get(tier, []):
            name = r.get("name", "")
            if name:
                names.add(name.lower())
    return names


def is_relevant_gov(title, summary, source, retailer_names, keywords):
    """Para fuentes high priority: siempre relevante.
    Para medium/low: filtra por keywords de la fuente o menciones de retailers."""
    priority = source.get("priority", "medium")

    if priority == "high":
        return True, f"priority:high ({source['id']})"

    text = (title + " " + (summary or "")).lower()

    # Chequear keywords específicas de la fuente
    source_tags = [t.lower() for t in source.get("tags", [])]
    for tag in source_tags:
        if tag in text:
            return True, f"tag:{tag}"

    # Chequear retailers
    for name in retailer_names:
        if re.search(r'\b' + re.escape(name), text):
            return True, f"retailer:{name}"

    # Chequear keywords globales de retail
    for kw in keywords:
        if kw.lower() in text:
            return True, f"keyword:{kw}"

    return False, None


def get_retail_sector(title, summary, match_reason, sector_config):
    """Asigna categoría editorial basada en el match."""
    if not sector_config:
        return None
    kw_map = sector_config.get("keyword_categories", {})
    text = ((title or "") + " " + (summary or "")).lower()
    for cat_id, kws in kw_map.items():
        if any(kw.lower() in text for kw in kws):
            return cat_id
    return "macro"  # default para gov — casi todo tiene dimensión macro


def fetch_rss(source):
    """Parsea un feed RSS gubernamental."""
    try:
        resp = requests.get(source["rss"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        articles = []
        for entry in feed.entries:
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            dt = datetime(*pub[:6]).isoformat() if pub else datetime.now().isoformat()

            articles.append({
                "source_id":   source["id"],
                "source_name": source["name"],
                "source_cat":  source["category"],
                "source_pri":  source.get("priority", "medium"),
                "paywall":     source.get("paywall", False),
                "title":       entry.get("title", "").strip(),
                "url":         entry.get("link", ""),
                "summary":     clean_html(entry.get("summary", "")),
                "datetime":    dt,
            })
        return articles
    except Exception as e:
        print(f"  [WARN] {source['name']}: {e}")
        return []


def run():
    config       = load_json(GOV_CONFIG_PATH)
    retailers    = load_json(RETAILERS_PATH)
    sector_config = load_json(SECTOR_CONFIG_PATH)
    existing     = load_json(GOV_DATA_PATH, {"items": [], "generated_at": None})

    retailer_names = build_retailer_names(retailers)
    keywords       = retailers.get("keywords", [])

    existing_ids = {item["url"] for item in existing.get("items", []) if item.get("url")}
    new_items    = []
    total_fetched = 0

    for source in config.get("sources", []):
        method = source.get("method", "rss")

        if method != "rss" or not source.get("rss"):
            if method == "scrape":
                print(f"  [SKIP] {source['name']}: scraping no implementado todavía")
            continue

        print(f"  Fetching: {source['name']} [{source.get('priority','?')}]...")
        articles = fetch_rss(source)
        total_fetched += len(articles)

        for a in articles:
            if a["url"] in existing_ids:
                # Re-intentar si ya existe pero sin match_reason (primera vez)
                continue

            relevant, match = is_relevant_gov(
                a["title"], a["summary"], source, retailer_names, keywords
            )
            if not relevant:
                continue

            a["match_reason"]  = match
            a["stream"]        = "government"
            a["story_type"]    = source.get("category", "policy")
            a["is_noise"]      = False
            a["retail_sector"] = get_retail_sector(
                a["title"], a["summary"], match, sector_config
            )
            a["tags"]          = source.get("tags", [])
            new_items.append(a)
            existing_ids.add(a["url"])

        time.sleep(SLEEP)

    # Acumular y purgar
    all_items = existing.get("items", []) + new_items
    keep_days = config.get("retention", {}).get("keep_days", 14)
    cutoff = (datetime.now() - timedelta(days=keep_days)).isoformat()
    before = len(all_items)
    all_items = [i for i in all_items if i.get("datetime", "") >= cutoff]
    purged = before - len(all_items)

    all_items.sort(key=lambda x: x.get("datetime", ""), reverse=True)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "items": all_items,
    }
    GOV_DATA_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\nFetched {total_fetched} artículos de {len(config.get('sources', []))} fuentes")
    print(f"{len(new_items)} nuevos relevantes para retail/gov")
    print(f"{len(all_items)} artículos totales en {GOV_DATA_PATH}")
    if purged:
        print(f"{purged} artículos purgados (>{keep_days} días)")
    return payload


if __name__ == "__main__":
    run()
