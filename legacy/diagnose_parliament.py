"""
Diagnóstico puntual — no es parte del pipeline, es solo para ver qué
devuelve la API real y ajustar agenda_parliament.py de acuerdo a eso.

Correr desde agenda/: python diagnose_parliament.py
"""
import requests
import json

HEADERS = {"User-Agent": "retail-news-tracker-agenda/1.0"}
API_BASE = "https://committees-api.parliament.uk/api"

SEARCH_TERMS = ["business and trade", "treasury", "levelling up housing"]

for term in SEARCH_TERMS:
    print(f"\n{'='*60}")
    print(f"Buscando comité: '{term}'")
    print('='*60)
    try:
        resp = requests.get(f"{API_BASE}/Committees", params={"SearchTerm": term}, headers=HEADERS, timeout=20)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(json.dumps(data, indent=2)[:1500])  # primeros 1500 caracteres, alcanza para ver la forma
    except Exception as e:
        print(f"ERROR: {e}")

print(f"\n{'='*60}")
print("Ahora probando el endpoint de Events con Business and Trade (id=365)")
print('='*60)
try:
    resp = requests.get(
        f"{API_BASE}/Events",
        params={"CommitteeId": 365, "FromDate": "2026-08-29", "ToDate": "2026-11-29"},
        headers=HEADERS, timeout=20,
    )
    print(f"Status: {resp.status_code}")
    print(resp.text[:2500])
except Exception as e:
    print(f"ERROR: {e}")
