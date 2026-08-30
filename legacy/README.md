# Legacy / debug scripts

Not part of the pipeline. Kept for reference, not deleted.

- `dashboard_old.html` — earlier version of the dashboard, superseded by `dashboard.html`.
- `lse_scraper_colab.ipynb` — original Colab prototype of the LSE scraper, superseded by `lse_scraper.py` + GitHub Actions.
- `check_agenda.ps1` — manual file-presence checklist from the agenda module's initial build. Superseded by `diagnose_sources.py` (repo root) and each scraper's own zero-items health check.
- `diagnose_parliament.py` — one-off exploration of the Parliament Committees API, used to figure out the real field names (`startDate`, etc.) now baked into `agenda/scrapers/agenda_parliament.py`. Superseded by `diagnose_sources.py`.
