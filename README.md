# Retail Wire — UK retail news tracker

Editorial tool for tracking UK retail news, built for a Retail Week journalist. Five modules are live: LSE press releases, UK media scan, government/statistics data, retailer corporate press, and a forward-looking events agenda.

## How it works

The pipeline is split into two clear layers: automated data capture (no AI, no tokens) and on-demand editorial tools (AI only when you ask for it).

### Automated (runs without you)

Each module has its own GitHub Actions workflow, targeting fixed UK local times. GitHub Actions cron only runs in UTC, so every workflow schedules both the BST and GMT UTC equivalent of each target — `schedule_guard.py` checks the real London time at run time and does nothing on the half that doesn't apply. **Nobody needs to hand-edit crons for the DST switch.**

| Module | UK local times | What happens |
|---|---|---|
| LSE press releases | 07:01, 07:15 | Scrapes LSE News Explorer, filters by sector ICB |
| UK media scan | 06:15, 06:45, 07:30, 11:15, 14:15, 16:15 | Scrapes trade press + nationals, filters by `retailers.json` |
| Government / statistics | 07:00, 09:45, 12:30, 14:30, 17:30 | ONS, GOV.UK, Parliament — filtered by priority + retailer/keyword match |
| Company press | 07:00, 09:00, 12:00, 15:00, 17:00 | Retailer corporate press pages via Google News RSS |
| Events agenda | 07:00 | ONS release calendar, LSE earnings dates, parliamentary committees, BRC reports |

Each scraper fails loudly if it fetches zero items from every one of its sources in a run — that's a broken feed, not a quiet day.

Local Task Scheduler pulls (`setup_task_scheduler.ps1`) additionally sync the latest data to your machine at 07:11, 07:25, 11:10, 14:10, 16:10.

### On-demand (you decide when)

Open Claude Code from the repo folder and use these skills:

| Command | What it does |
|---|---|
| `/draft <id or headline>` | Drafts a story using Bloomberg method + Retail Week style. Works across LSE, media, gov, and company items. Saves to `drafts/` automatically. |
| `/recategorize` | Reviews ambiguous LSE articles in `unmapped_categories.json`, assigns story types, pushes to GitHub after your confirmation. |
| `/feedback` | Compares your edited versions against original drafts, updates style preferences in `docs/retail_wire_drafting_reference.md`, pushes to GitHub after your confirmation. |
| `/update` | Pulls latest data from GitHub mid-session. |

## Repo structure

```
schedule_guard.py            Shared UK-local-time guard (handles BST/GMT) — no AI
lse_scraper.py                LSE scraper — no AI
media_scraper.py              UK media scan — no AI
gov_scraper.py                Government/statistics scan — no AI
company_scraper.py            Retailer corporate press scan — no AI
agenda/                       Events agenda module (own scraper + config) — no AI
transform_to_dashboard.py     LSE CSV → dashboard JSON, archives old items — no AI
lse_config.json                Sectors, endpoint IDs, pagination, retention
media_config.json / gov_config.json / company_config.json   Sources per module
retailers.json / sector_config.json   Shared retailer names + sector keywords
category_map.json             LSE category codes → story types
article_overrides.json        Per-article editorial overrides (written by /recategorize)
unmapped_categories.json      Queue of unclassified LSE articles (read by /recategorize)
dashboard_data.json           Live (recent-window) LSE dataset
data/archive/                 Older LSE items, moved out for dashboard performance — nothing deleted
media_data.json / gov_data.json / company_data.json / agenda_data.json   Live datasets for the other modules
dashboard.html                Static dashboard — deploys via GitHub Pages, reads all five data files
docs/
  retail_wire_drafting_reference.md   Bloomberg method + Retail Week style + learned preferences
.claude/skills/
  draft/        /draft skill
  recategorize/ /recategorize skill
  feedback/     /feedback skill
  update/       /update skill
.github/workflows/
  lse_scraper.yml, media_scraper.yml, gov_scraper.yml, company_scraper.yml, agenda_scraper.yml
```

## Daily workflow

```
Morning
  → Dashboard updates automatically (GitHub Pages)
  → Local data updates automatically (Task Scheduler)

When you want to write
  → Double-click retail_wire.bat (pulls latest + opens Claude Code)
  → Find a story in the dashboard
  → /draft 17754000                    (LSE, by id)
  → /draft "Tesco half-year results"   (any module, by headline/company)

Mid-session refresh
  → /update

Categorise ambiguous LSE items
  → /recategorize

End of day — teach Claude your edits
  → /feedback
```

## Setup (one-time)

**GitHub Actions**: Settings → Actions → General → Workflow permissions → Read and write permissions.

**GitHub Pages**: Settings → Pages → Branch: main → Save.

**Local**: run `setup_task_scheduler.ps1` once to register the scheduled pull tasks on your machine.

**Claude Code**: install from https://claude.ai/install, then `claude` from inside the repo folder.

## Modules

| Module | Status |
|---|---|
| LSE press releases | ✅ Live |
| UK media scan | ✅ Live |
| Government data (ONS / GOV.UK / Parliament) | ✅ Live |
| Retailer corporate press | ✅ Live |
| Events agenda (earnings, releases, committees) | ✅ Live |
| Suppliers / FMCG brands | 🔜 Planned |
