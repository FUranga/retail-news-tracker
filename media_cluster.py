"""
Agrupa items de media_data.json que cubren la MISMA noticia contada por
fuentes distintas de media_config.json (48 fuentes), para que el dashboard
pueda mostrar "+N fuentes" en vez de tarjetas sueltas sin relación.

Determinístico, sin AI: similaridad Jaccard de tokens del título, solo
entre items de source_id distinto, dentro de una ventana de días. No toca
el dedup por URL exacta dentro de la misma fuente (eso ya lo hace
media_scraper.py) — esto es un paso aparte, posterior, standalone, para
poder ajustar threshold/ventana re-corriendo sobre datos ya scrapeados
sin necesidad de red.

Uso:
    python media_cluster.py media_data.json
"""

import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

MEDIA_CONFIG_PATH = Path("media_config.json")

DEFAULT_CLUSTERING = {
    "enabled": True,
    "window_days": 1,
    "jaccard_threshold": 0.6,
    "min_title_tokens": 4,
    "stopwords": ["the", "a", "an", "to", "of", "in", "on", "for", "and", "uk",
                  "says", "after", "as", "with", "at", "is", "its", "over"],
}


def load_json(path, default=None):
    if Path(path).exists():
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] No se pudo leer {path}: {e}")
    return default if default is not None else {}


def normalize_title(title, stopwords):
    """minúsculas, quita puntuación, tokeniza, filtra stopwords y tokens <3 chars."""
    text = re.sub(r"[^a-z0-9\s]", " ", (title or "").lower())
    tokens = [t for t in text.split() if len(t) >= 3 and t not in stopwords]
    return set(tokens)


def jaccard(a, b):
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def _parse_dt(value):
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def build_clusters(items, window_days, threshold, min_title_tokens, stopwords):
    """Devuelve {url: cluster_id}. Solo compara items con source_id distinto
    y |fecha_a - fecha_b| <= window_days. Agrupa transitivamente (union-find)."""
    n = len(items)
    token_sets = [normalize_title(it.get("title"), stopwords) for it in items]
    dts = [_parse_dt(it.get("datetime")) for it in items]

    uf = UnionFind(n)
    for i in range(n):
        if len(token_sets[i]) < min_title_tokens or dts[i] is None:
            continue
        for j in range(i + 1, n):
            if items[i].get("source_id") == items[j].get("source_id"):
                continue
            if len(token_sets[j]) < min_title_tokens or dts[j] is None:
                continue
            if abs((dts[i] - dts[j]).days) > window_days:
                continue
            if jaccard(token_sets[i], token_sets[j]) >= threshold:
                uf.union(i, j)

    groups = {}
    for i in range(n):
        root = uf.find(i)
        groups.setdefault(root, []).append(i)

    cluster_map = {}
    for root, idxs in groups.items():
        if len(idxs) < 2:
            continue
        # id determinístico: sha1 del url del item más antiguo del grupo (el
        # "original" presunto) — NO usar hash() built-in, que randomiza por
        # proceso (PYTHONHASHSEED) y rompería la idempotencia entre corridas.
        oldest_idx = min(idxs, key=lambda k: dts[k] or datetime.max)
        cluster_id = hashlib.sha1(items[oldest_idx].get("url", "").encode("utf-8")).hexdigest()[:16]
        for idx in idxs:
            url = items[idx].get("url")
            if url:
                cluster_map[url] = cluster_id

    return cluster_map


def annotate_clusters(items, cluster_map):
    """Agrega cluster_id (o None) y cluster_size a cada item, in place."""
    size_by_cluster = {}
    for it in items:
        cid = cluster_map.get(it.get("url"))
        if cid:
            size_by_cluster[cid] = size_by_cluster.get(cid, 0) + 1

    for it in items:
        cid = cluster_map.get(it.get("url"))
        it["cluster_id"] = cid
        it["cluster_size"] = size_by_cluster.get(cid, 1) if cid else 1
    return items


def run(media_data_path):
    path = Path(media_data_path)
    payload = load_json(path, {"items": [], "generated_at": None})
    items = payload.get("items", [])

    config = load_json(MEDIA_CONFIG_PATH, {})
    clustering = {**DEFAULT_CLUSTERING, **config.get("clustering", {})}

    if not clustering.get("enabled", True):
        print("[media_cluster] clustering deshabilitado en media_config.json, no hago nada")
        return payload

    stopwords = set(w.lower() for w in clustering.get("stopwords", []))
    cluster_map = build_clusters(
        items,
        window_days=clustering.get("window_days", 1),
        threshold=clustering.get("jaccard_threshold", 0.6),
        min_title_tokens=clustering.get("min_title_tokens", 4),
        stopwords=stopwords,
    )
    items = annotate_clusters(items, cluster_map)
    payload["items"] = items

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    n_clustered = sum(1 for it in items if it.get("cluster_id"))
    n_groups = len(set(cid for cid in cluster_map.values()))
    print(f"[media_cluster] {n_clustered} items agrupados en {n_groups} clusters (de {len(items)} totales)")
    return payload


if __name__ == "__main__":
    media_data_path = sys.argv[1] if len(sys.argv) > 1 else "media_data.json"
    run(media_data_path)
