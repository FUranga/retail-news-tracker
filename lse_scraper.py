"""
Scraper LSE News Explorer — Módulo 1 del tracker de retail UK
Config separada en lse_config.json.

Estrategia (actualizada tras validar en la práctica que el filtro de
sector del endpoint de listado NO funciona — se ignora silenciosamente):

1. Bajamos el listado del día/ventana SIN intentar filtrar por sector
   (ese parámetro no existe o se llama distinto — no vale la pena
   seguir adivinando).
2. Por cada artículo del listado, pedimos el detalle completo a un
   segundo endpoint (GET /api/v1/pages?path=news-article&...), que
   trae el body completo Y la clasificación ICB oficial de la empresa
   (icbsectorcode). Filtramos ahí, contra la lista de sectores de la
   config — es la fuente de verdad real, no un parámetro adivinado.
3. Como bonus, en el mismo request ya tenemos el texto completo del
   comunicado, así que no hace falta un tercer paso para eso.

Costo: 1 request extra por artículo del listado (no por artículo ya
filtrado). Para la ventana angosta de las 7:01/7:15 son ~15-30 
requests — perfectamente razonable. Si el volumen crece mucho (backfill
histórico, por ejemplo), conviene primero descartar por company_overrides
o categorías de ruido antes de pedir el detalle — no implementado
todavía, ver nota al final del archivo.

Corre 100% con `requests` — sin browser/Playwright, sin AI, sin tokens.
"""

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from schedule_guard import should_run

CONFIG_PATH = Path("lse_config.json")

LIST_URL = "https://api.londonstockexchange.com/api/v1/components/refresh"
DETAIL_URL = "https://api.londonstockexchange.com/api/v1/pages"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "origin": "https://www.londonstockexchange.com",
    "referer": "https://www.londonstockexchange.com/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
}


def load_config(path=CONFIG_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def slugify(title: str) -> str:
    s = (title or "").strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def build_article_url(companycode, title, article_id):
    if not companycode or not article_id:
        return None
    slug = slugify(title)
    return f"https://www.londonstockexchange.com/news-article/{companycode}/{slug}/{article_id}"


def strip_html(raw_html):
    """Convierte el body HTML del comunicado en Markdown legible.
    Los comunicados del LSE tienen estructura mínima (párrafos <p>, negritas
    <strong>, tablas ocasionales) — los convertimos a Markdown para que
    el dashboard pueda renderizarlos con estructura y Claude Code los lea bien.
    """
    if not raw_html:
        return ""
    from markdownify import markdownify as md
    # Convertir HTML a Markdown preservando párrafos, negritas y tablas
    result = md(
        raw_html,
        heading_style="ATX",
        bullets="-",
        strip=["script", "style", "img"],
    )
    # Limpiar el comentario inicial típico de los RNS /* */
    result = re.sub(r"^/\*.*?\*/\s*", "", result, flags=re.DOTALL)
    # Colapsar más de dos saltos de línea consecutivos
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


# ---------- Listado (sin filtro de sector — no funciona en este endpoint) ----------

def fetch_list_page(config, page=0):
    endpoint = config["endpoint"]
    size = config["request"]["page_size"]

    top_params = f"tab=news-explorer&tabId={endpoint['tab_id']}"
    component_params = f"page={page}&size={size}&sort=datetime,desc"

    body = {
        "path": "news",
        "parameters": top_params,
        "components": [
            {"componentId": endpoint["component_id"], "parameters": component_params}
        ],
    }
    resp = requests.post(LIST_URL, headers=HEADERS, json=body, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _find_search_block(payload):
    for block in payload:
        for item in block.get("content", []):
            if item.get("name") == "newsexplorersearch" and item.get("value"):
                return item["value"]
    return None


def fetch_all_list(config):
    all_articles = []
    page = 0
    max_pages = config["request"]["max_pages"]
    sleep_seconds = config["request"]["sleep_seconds"]

    while page < max_pages:
        payload = fetch_list_page(config, page=page)
        block = _find_search_block(payload)
        if not block:
            print(f"[WARN] No se encontró bloque de resultados en page={page}")
            break

        all_articles.extend(block.get("content", []))

        total_pages = block.get("totalPages", 1)
        if page + 1 >= total_pages:
            break

        page += 1
        time.sleep(sleep_seconds)

    return all_articles


def to_dataframe(articles):
    rows = []
    for a in articles:
        rows.append(
            {
                "id": a.get("id"),
                "datetime": a.get("datetime"),
                "title": a.get("title"),
                "companyname": a.get("companyname"),
                "companycode": a.get("companycode"),
                "category": a.get("category"),
                "source": a.get("source"),
                "rnsnumber": a.get("rnsnumber"),
                "url": build_article_url(
                    a.get("companycode"), a.get("title"), a.get("id")
                ),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("datetime", ascending=False).reset_index(drop=True)
    return df


# ---------- Detalle por artículo: body real + sector ICB oficial ----------

def fetch_article_detail(article_id):
    params = {"path": "news-article", "parameters": f"newsId={article_id}"}
    resp = requests.get(DETAIL_URL, headers=HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def parse_article_detail(payload):
    """Devuelve (body_text, icb_sector_code, icb_sector) buscando en todos
    los bloques de la respuesta, porque newsarticle e issuerreferencedata
    pueden venir en bloques distintos."""
    body_text = None
    icb_sector_code = None
    icb_sector = None
    for block in payload.get("components", []):
        for item in (block.get("content") or []):
            name = item.get("name")
            value = item.get("value")
            if not value:
                continue
            if name == "newsarticle":
                body_text = strip_html(value.get("body"))
            elif name == "issuerreferencedata":
                icb_sector_code = value.get("icbsectorcode")
                icb_sector = value.get("icbsector")
    return body_text, icb_sector_code, icb_sector


def enrich_and_filter(df, config):
    """Baja el detalle de cada artículo, filtra por icbsectorcode contra
    la config, y agrega body + sector al resultado final."""
    sectors_wanted = set(config["filters"]["sectors"])
    include_tickers = set(config["company_overrides"].get("include", []))
    exclude_tickers = set(config["company_overrides"].get("exclude", []))
    sleep_seconds = config["request"]["sleep_seconds"]

    kept_rows = []
    for _, row in df.iterrows():
        if row.get("companycode") in exclude_tickers:
            continue

        try:
            detail = fetch_article_detail(row["id"])
            body_text, icb_code, icb_sector = parse_article_detail(detail)
        except Exception as e:
            print(f"[WARN] No se pudo bajar detalle de id={row['id']}: {e}")
            body_text, icb_code, icb_sector = None, None, None

        is_wanted_sector = icb_code in sectors_wanted
        is_included_ticker = row.get("companycode") in include_tickers

        if is_wanted_sector or is_included_ticker:
            new_row = row.to_dict()
            new_row["body"] = body_text
            new_row["icbsectorcode"] = icb_code
            new_row["icbsector"] = icb_sector
            kept_rows.append(new_row)

        time.sleep(sleep_seconds)

    return pd.DataFrame(kept_rows)


def _set_github_output(key, value):
    """Escribe una salida para que el workflow de Actions pueda condicionar
    pasos siguientes (ej. saltear transform_to_dashboard.py si no hay CSV
    nuevo). No-op fuera de Actions (uso local/manual)."""
    path = __import__("os").environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{key}={value}\n")


def run(config_path=CONFIG_PATH, save_csv=True):
    config = load_config(config_path)

    if not should_run(config.get("schedule", {}).get("runs_uk", [])):
        print("[lse_scraper] fuera de ventana horaria UK, no corro esta vez")
        _set_github_output("did_work", "false")
        return None

    articles = fetch_all_list(config)
    df_all = to_dataframe(articles)
    print(f"{len(df_all)} artículos en la ventana (sin filtrar todavía)")

    if df_all.empty:
        print("[HEALTH] El endpoint de listado del LSE no devolvió NINGÚN artículo "
              "en la ventana — puede ser una ventana genuinamente vacía (fin de "
              "semana/feriado) o el endpoint/API puede haber cambiado. Revisar.")
        _set_github_output("did_work", "false")
        sys.exit(1)

    df = enrich_and_filter(df_all, config)
    print(f"{len(df)} artículos retail/grocery confirmados (icbsectorcode + overrides)")

    if not df.empty:
        print(df[["datetime", "companyname", "icbsector", "title", "url"]].head(20).to_string())

    if save_csv and not df.empty:
        # Archivo timestamped para el histórico crudo
        archive_dir = Path("data/raw")
        archive_dir.mkdir(parents=True, exist_ok=True)
        fname = archive_dir / f"lse_retail_news_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        df.to_csv(fname, index=False)
        print(f"Guardado en {fname}")

        # Puntero de nombre fijo, para que el siguiente paso del pipeline
        # (transform_to_dashboard.py) no tenga que adivinar el nombre.
        df.to_csv("lse_latest.csv", index=False)
        print("Guardado también en lse_latest.csv (puntero fijo)")
        _set_github_output("did_work", "true")
    else:
        # Ventana real (no un salteo de horario) pero sin retail/grocery
        # confirmado — no hay CSV nuevo, no tiene sentido correr el transform.
        _set_github_output("did_work", "false")

    return df


if __name__ == "__main__":
    run()

# NOTA para más adelante: si el volumen de la ventana crece mucho (ej.
# backfill histórico de meses), conviene agregar un pre-filtro barato
# ANTES de pedir el detalle de cada artículo — por ejemplo, descartar
# categorías puramente regulatorias (HOL, POS, DSH, MSC, TVR, PDI, STA)
# que casi nunca esconden una mención real de retailer. Por ahora, con
# ventanas de 15-30 artículos por corrida, no hace falta esa optimización.
