"""
Diagnóstico funcional de TODAS las fuentes del tracker (Módulos 1-5).

No es parte del pipeline automático — es una herramienta manual para
correr cuando querés saber "¿qué fuentes están rotas ahora mismo?" sin
esperar a que un workflow falle solo (el HEALTH check de cada scraper
avisa cuando TODAS las fuentes de un módulo fallan a la vez, pero no
te dice cuál de 44 feeds de company_config.json es la que viene
devolviendo cero desde hace semanas).

Prueba en vivo, contra internet real:
  - Módulo 1 (LSE): el endpoint de listado.
  - Módulo 2 (media_config.json), Módulo 3 (gov_config.json), Módulo 4
    (company_config.json): cada fuente RSS configurada.
  - Módulo 7 (agenda): cada scraper en agenda/scrapers/, vía su función
    scrape(config).

Uso:
    python diagnose_sources.py                  # todo
    python diagnose_sources.py --module media    # solo un módulo
                                                  # (media|gov|company|lse|agenda)
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import feedparser
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 15
MAX_WORKERS = 8


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_rss(url, timeout=TIMEOUT):
    t0 = time.time()
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
    except Exception as e:
        return {"status": "ERROR", "detail": type(e).__name__ + ": " + str(e)[:140], "count": 0, "elapsed": time.time() - t0}
    elapsed = time.time() - t0
    if resp.status_code != 200:
        return {"status": "ERROR", "detail": f"HTTP {resp.status_code}", "count": 0, "elapsed": elapsed}
    try:
        feed = feedparser.parse(resp.content)
    except Exception as e:
        return {"status": "ERROR", "detail": f"parse error: {e}", "count": 0, "elapsed": elapsed}
    n = len(feed.entries)
    if n == 0:
        bozo_msg = getattr(feed, "bozo_exception", None)
        detail = f"200 OK pero 0 entries" + (f" (bozo: {bozo_msg})" if bozo_msg else "")
        return {"status": "EMPTY", "detail": detail, "count": 0, "elapsed": elapsed}
    return {"status": "OK", "detail": f"{n} entries", "count": n, "elapsed": elapsed}


def check_config_sources(config_path, label):
    config = load_json(config_path)
    sources = config.get("sources", [])
    tasks = []
    for s in sources:
        if s.get("rss") and s.get("method", "rss") == "rss":
            tasks.append(s)

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(check_rss, s["rss"]): s for s in tasks}
        for fut in as_completed(futures):
            s = futures[fut]
            r = fut.result()
            r["id"] = s["id"]
            r["name"] = s.get("name", s["id"])
            r["url"] = s["rss"]
            results.append(r)

    results.sort(key=lambda r: (r["status"] != "ERROR", r["status"] != "EMPTY", r["id"]))
    return results


def check_lse():
    sys.path.insert(0, ".")
    import lse_scraper
    config = lse_scraper.load_config()
    t0 = time.time()
    try:
        payload = lse_scraper.fetch_list_page(config, page=0)
        block = lse_scraper._find_search_block(payload)
        n = len(block.get("content", [])) if block else 0
        elapsed = time.time() - t0
        status = "OK" if n > 0 else "EMPTY"
        detail = f"{n} artículos en la primera página del listado (sin filtrar por sector)"
        return [{"id": "lse_list_endpoint", "name": "LSE News Explorer — listado", "url": lse_scraper.LIST_URL,
                 "status": status, "detail": detail, "count": n, "elapsed": elapsed}]
    except Exception as e:
        return [{"id": "lse_list_endpoint", "name": "LSE News Explorer — listado", "url": lse_scraper.LIST_URL,
                 "status": "ERROR", "detail": f"{type(e).__name__}: {e}", "count": 0, "elapsed": time.time() - t0}]


def check_agenda():
    import os
    agenda_dir = Path("agenda").resolve()
    sys.path.insert(0, str(agenda_dir))
    cwd = os.getcwd()
    os.chdir(agenda_dir)
    try:
        import agenda_scraper
        scrapers = agenda_scraper.SCRAPERS  # única fuente de verdad — no duplicar esta lista acá
        config = json.loads(Path("agenda_config.json").read_text(encoding="utf-8"))
        results = []
        for source_cfg in config["sources"]:
            sid = source_cfg["id"]
            if not source_cfg.get("enabled", True):
                continue
            mod = scrapers.get(sid)
            if not mod:
                continue
            t0 = time.time()
            try:
                found = mod.scrape(config)
                elapsed = time.time() - t0
                status = "OK" if found else "EMPTY"
                results.append({"id": sid, "name": source_cfg.get("label", sid), "url": "-",
                                 "status": status, "detail": f"{len(found)} eventos", "count": len(found), "elapsed": elapsed})
            except Exception as e:
                elapsed = time.time() - t0
                results.append({"id": sid, "name": source_cfg.get("label", sid), "url": "-",
                                 "status": "ERROR", "detail": f"{type(e).__name__}: {e}", "count": 0, "elapsed": elapsed})
        return results
    finally:
        os.chdir(cwd)


def print_report(label, results):
    print(f"\n=== {label} ({len(results)} fuentes) ===")
    n_ok = sum(1 for r in results if r["status"] == "OK")
    n_empty = sum(1 for r in results if r["status"] == "EMPTY")
    n_err = sum(1 for r in results if r["status"] == "ERROR")
    print(f"OK: {n_ok}  EMPTY: {n_empty}  ERROR: {n_err}")
    for r in results:
        mark = {"OK": "OK   ", "EMPTY": "EMPTY", "ERROR": "ERR  "}[r["status"]]
        print(f"  [{mark}] {r['id']:<20} {r['detail']:<55} ({r['elapsed']:.1f}s)  {r['name']}")
    return {"label": label, "ok": n_ok, "empty": n_empty, "error": n_err, "results": results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", choices=["lse", "media", "gov", "company", "supplier", "agenda"], default=None)
    args = parser.parse_args()

    all_reports = []

    if args.module in (None, "lse"):
        all_reports.append(print_report("Módulo 1 — LSE", check_lse()))
    if args.module in (None, "media"):
        all_reports.append(print_report("Módulo 2 — Media (media_config.json)", check_config_sources("media_config.json", "media")))
    if args.module in (None, "gov"):
        all_reports.append(print_report("Módulo 3 — Gov (gov_config.json)", check_config_sources("gov_config.json", "gov")))
    if args.module in (None, "company"):
        all_reports.append(print_report("Módulo 4 — Company (company_config.json)", check_config_sources("company_config.json", "company")))
    if args.module in (None, "supplier"):
        all_reports.append(print_report("Módulo 6 — Supplier (supplier_config.json)", check_config_sources("supplier_config.json", "supplier")))
    if args.module in (None, "agenda"):
        all_reports.append(print_report("Módulo 7 — Agenda", check_agenda()))

    total_ok = sum(r["ok"] for r in all_reports)
    total_empty = sum(r["empty"] for r in all_reports)
    total_err = sum(r["error"] for r in all_reports)
    print(f"\n=== TOTAL: {total_ok} OK, {total_empty} EMPTY, {total_err} ERROR ===")

    out_path = Path("data/diagnose_sources_last_run.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(all_reports, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReporte completo guardado en {out_path}")


if __name__ == "__main__":
    main()
