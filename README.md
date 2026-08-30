# Retail Wire — UK retail news tracker

Editorial tool for tracking UK retail news, built for a Retail Week journalist. Six modules are live: LSE press releases, UK media scan, government/statistics data, retailer corporate press, supplier/FMCG press, and a forward-looking events agenda.

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
| Supplier press | 07:30, 10:00, 13:00, 16:00 | FMCG/fresh-food/wholesale suppliers to retailers via Google News RSS |
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
supplier_scraper.py           FMCG/fresh-food/wholesale supplier press scan — no AI
agenda/                       Events agenda module (own scraper + config) — no AI
diagnose_sources.py           Manual smoke-test: runs every RSS/scraper source live, reports OK/EMPTY/ERROR
transform_to_dashboard.py     LSE CSV → dashboard JSON, archives old items — no AI
lse_config.json                Sectors, endpoint IDs, pagination, retention
media_config.json / gov_config.json / company_config.json / supplier_config.json   Sources per module
retailers.json / sector_config.json   Shared retailer names + sector keywords
category_map.json             LSE category codes → story types
article_overrides.json        Per-article editorial overrides (written by /recategorize)
unmapped_categories.json      Queue of unclassified LSE articles (read by /recategorize)
dashboard_data.json           Live (recent-window) LSE dataset
data/archive/                 Older LSE items, moved out for dashboard performance — nothing deleted
media_data.json / gov_data.json / company_data.json / supplier_data.json / agenda_data.json   Live datasets for the other modules
dashboard.html                Static dashboard — deploys via GitHub Pages, reads all six data files
docs/
  retail_wire_drafting_reference.md   Bloomberg method + Retail Week style + learned preferences
.claude/skills/
  draft/        /draft skill
  recategorize/ /recategorize skill
  feedback/     /feedback skill
  update/       /update skill
.github/workflows/
  lse_scraper.yml, media_scraper.yml, gov_scraper.yml, company_scraper.yml, supplier_scraper.yml, agenda_scraper.yml
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
| Supplier / FMCG press | ✅ Live (2026-08-30) |
| Supplier / tech & AI vendors (payments, supply chain software, POS, last-mile) | ✅ Live (2026-08-30) |
| Retail tech trade press (Retail Technology Innovation Hub, Retail Systems) | ✅ Live (2026-08-30) |
| Events agenda (earnings, releases, committees) | ✅ Live |
| Judiciary (caselaw.nationalarchives.gov.uk, Competition Appeal Tribunal, employment tribunal coverage) | ✅ Live (2026-08-30) — gov_config.json, priority: medium |
| Media scan — trade press expansion (Talking Retail, Convenience Store, Insider Media, This Is Money, Marketing Week, FashionUnited UK) | ✅ Live (2026-08-30) — Essential Retail dropped, site unreachable |
| Media scan — major UK nationals missing (Independent, Sun, Mirror, Metro, i Paper, Evening Standard, MoneySavingExpert) | ✅ Live (2026-08-30) |
| Media scan — local/regional UK (Business Live, Manchester Evening News, Wales Online, Belfast Telegraph, The Scotsman) | ✅ Live (2026-08-30) — individual Reach plc regional titles beyond these mostly block RSS (202/empty); Business Live aggregates the gap |
| Media scan — other-sector trade referencing retail (Computer Weekly, UKTN, Campaign, Finextra, The Caterer, Just Style) | ✅ Live (2026-08-30) |
| Media scan — foreign press covering UK retailers (consolidated WSJ/NYT/CNBC/Bloomberg/Reuters query anchored to major UK retailer names, Chain Store Age, Retail Dive) | ✅ Live (2026-08-30) — single-outlet foreign queries mostly surfaced that outlet's own domestic retail news, not UK; the consolidated query was the fix |
| Other trade bodies (Usdaw, IGD, Local Data Company, Springboard, HSE, The Pensions Regulator) | ✅ Live (2026-08-30) — gov_config.json, priority: medium |
| Agenda expansion — BoE MPC dates, sector trade shows (Spring/Autumn Fair), National Living Wage effective date | ✅ Live (2026-08-30) |
| Agenda expansion — Budget/Autumn Statement date, business rates revaluation | ❌ Not automatable — HMT doesn't announce Budget dates on a fixed schedule/feed, and the current business rates revaluation cycle wasn't verified live. Add manually via the dashboard's manual-event form when announced. |
