"""
Transforms the LSE scraper CSV into the JSON that dashboard.html consumes.
100% Colab, no AI — the category -> story_type mapping is deterministic.

LSE category codes (POS, HOL, FR, ACQ...) map directly to editorial story
types. Only the ones left unmapped ("Other") would be candidates for
Claude to disambiguate later — but that's optional and on-demand, not
on every run.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# LSE code -> (readable story type, is_noise)
# is_noise = True flags regulatory boilerplate that is rarely a real story.
# Can be shown/hidden from the dashboard without deleting it from history.
CATEGORY_MAP = {
    "POS": ("Buyback", True),            # Transaction in Own Shares
    "HOL": ("Holding", True),            # Holding(s) in Company
    "DSH": ("Director Dealing", False),  # Director/PDMR Shareholding
    "MSC": ("Other", False),             # Miscellaneous (this is where the TikTok story landed!)
    "NOR": ("Notice of Results", False), # Notice of Results
    "FR":  ("Results", False),
    "IR":  ("Results", False),
    "TST": ("Trading Update", False),
    "ACQ": ("M&A", False),
    "DIS": ("M&A", False),
    "MSCU":("Strategy", False),
    "AGM": ("AGM", True),
    "TVR": ("Voting Rights", True),
    "DIV": ("Dividend", False),
    "BOA": ("Board Change", False),
    "IOE": ("Equity Issue", False),
}


def map_category(code):
    if code in CATEGORY_MAP:
        return CATEGORY_MAP[code]
    return ("Other", False)


def transform(csv_path, out_path="dashboard_data.json"):
    df = pd.read_csv(csv_path)

    new_items = []
    for _, r in df.iterrows():
        code = r.get("category")
        story_type, is_noise = map_category(code)
        new_items.append({
            "id": int(r["id"]) if pd.notna(r.get("id")) else None,
            "datetime": str(r.get("datetime")),
            "title": (r.get("title") or "").strip(),
            "companyname": r.get("companyname") if pd.notna(r.get("companyname")) else None,
            "companycode": r.get("companycode") if pd.notna(r.get("companycode")) else None,
            "category": code if pd.notna(code) else None,
            "icbsector": r.get("icbsector") if pd.notna(r.get("icbsector")) else None,
            "source": "LSE",
            "stream": "press_release",
            "story_type": story_type,
            "is_noise": is_noise,
            "paywall": False,
            "url": r.get("url") if pd.notna(r.get("url")) else None,
        })

    # Acumular contra lo que ya existe (registro histórico), dedup por id.
    # Si un id se repite (re-fetch), la versión nueva pisa a la vieja.
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
    print(f"{len(new_items)} items nuevos procesados, {len(items)} items totales en {out_path}")
    noise = sum(1 for i in items if i["is_noise"])
    print(f"  {noise} flagged as regulatory noise, {len(items)-noise} as potential news")
    return payload


if __name__ == "__main__":
    csv = sys.argv[1] if len(sys.argv) > 1 else "lse_latest.csv"
    transform(csv)
