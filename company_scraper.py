"""
Scraper de webs corporativas de retailers UK — Módulo 4
Lee company_config.json y captura comunicados de prensa via Google News RSS.
Toda publicación de estas fuentes es relevante por definición.

100% Python — sin AI, sin tokens.
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

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

COMPANY_CONFIG_PATH = Path("company_config.json")
COMPANY_DATA_PATH   = Path("company_data.json")
SLEEP               = 1.5

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


def fetch_full_body(url):
    if not url or not TRAFILATURA_AVAILABLE:
        return None
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        text = trafilatura.extract(resp.text)
        if not text or len(text) < 200:
            return None
        garbage = ["access denied", "javascript is required", "sign in to continue"]
        if any(g in text.lower()[:200] for g in garbage):
            return None
        return text
    except Exception:
        return None


def fetch_rss(source, noise_signals=None):
    noise_signals = noise_signals or []
    try:
        resp = requests.get(source["rss"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        articles = []
        for entry in feed.entries:
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            dt = datetime(*pub[:6]).isoformat() if pub else datetime.now().isoformat()

            # Filtrar resultados que claramente no son noticias
            title = entry.get("title", "").strip()
            if not title or len(title) < 5:
                continue

            # Descartar ruido típico de webs corporativas
            title_lower = title.lower()
            url_lower = entry.get("link", "").lower()
            if any(sig in title_lower or sig in url_lower for sig in noise_signals):
                continue

            articles.append({
                "source_id":     source["id"],
                "source_name":   source["name"],
                "companyname":   source["name"],
                "retail_sector": source.get("retail_sector"),
                "listed":        source.get("listed"),
                "tier":          source.get("tier", 2),
                "paywall":       False,
                "title":         title,
                "url":           entry.get("link", ""),
                "summary":       clean_html(entry.get("summary", "")),
                "datetime":      dt,
            })
        return articles
    except Exception as e:
        print(f"  [WARN] {source['name']}: {e}")
        return []


def run():
    config   = load_json(COMPANY_CONFIG_PATH)
    existing = load_json(COMPANY_DATA_PATH, {"items": [], "generated_at": None})

    # Señales de ruido configurables
    noise_signals = [s.lower() for s in config.get("noise_title_signals", [
        "store colleague", "part time", "full time", "full-time", "part-time",
        "fitness coach", "supervisor", "merchandiser", "general assistant",
        "media centre & uk press releases", "help and advice hub",
        "sign up to emails", "kitchen & household", "fashion, home & beauty",
    ])]

    existing_ids = {item["url"] for item in existing.get("items", []) if item.get("url")}
    new_items    = []
    total_fetched = 0

    for source in config.get("sources", []):
        if not source.get("rss"):
            continue

        print(f"  Fetching: {source['name']} [tier {source.get('tier',2)}]...")
        articles = fetch_rss(source, noise_signals)
        total_fetched += len(articles)

        for a in articles:
            if a["url"] in existing_ids:
                continue

            a["stream"]      = "company"
            a["story_type"]  = None
            a["is_noise"]    = False
            a["match_reason"] = f"company:{source['name']}"
            a["body"]        = None  # body fetch desactivado — demasiado lento para webs corporativas
            new_items.append(a)
            existing_ids.add(a["url"])

        time.sleep(SLEEP)

    # Acumular y purgar
    all_items = existing.get("items", []) + new_items
    keep_days = config.get("retention", {}).get("keep_days", 7)
    cutoff = (datetime.now() - timedelta(days=keep_days)).isoformat()
    before = len(all_items)
    all_items = [i for i in all_items if i.get("datetime", "") >= cutoff]
    purged = before - len(all_items)

    all_items.sort(key=lambda x: x.get("datetime", ""), reverse=True)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "items": all_items,
    }
    COMPANY_DATA_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\nFetched {total_fetched} artículos de {len(config.get('sources', []))} empresas")
    print(f"{len(new_items)} nuevos comunicados capturados")
    print(f"{len(all_items)} artículos totales en {COMPANY_DATA_PATH}")
    if purged:
        print(f"{purged} artículos purgados (>{keep_days} días)")
    return payload


if __name__ == "__main__":
    run()
