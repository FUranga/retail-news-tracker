# Retail Wire — UK retail news tracker

Editorial tool for tracking UK retail news, built for a Retail Week journalist. Module 1 (LSE press releases) is live.

## How it works

The pipeline is split into two clear layers: automated data capture (no AI, no tokens) and on-demand editorial tools (AI only when you ask for it).

### Automated (runs without you)

| Time | What happens |
|---|---|
| 07:01 UK | GitHub Actions scrapes LSE News Explorer, filters by sector ICB, saves to repo |
| 07:15 UK | Second scrape, captures anything new since 07:01 |
| 07:11, 07:25, 11:10, 14:10, 16:10 | Task Scheduler pulls latest data to local machine |

### On-demand (you decide when)

Open Claude Code from the repo folder and use these skills:

| Command | What it does |
|---|---|
| `/draft <id>` | Drafts a story using Bloomberg method + Retail Week style. Saves to `drafts/` automatically. |
| `/recategorize` | Reviews ambiguous articles in `unmapped_categories.json`, assigns story types, pushes to GitHub after your confirmation. |
| `/feedback` | Compares your edited versions against original drafts, updates style preferences in `docs/retail_wire_drafting_reference.md`, pushes to GitHub after your confirmation. |
| `/update` | Pulls latest data from GitHub mid-session. |

## Repo structure

```
lse_scraper.py              Scraper — no AI
transform_to_dashboard.py   CSV → dashboard JSON — no AI
lse_config.json             Sectors, endpoint IDs, pagination
category_map.json           LSE category codes → story types
article_overrides.json      Per-article editorial overrides (written by /recategorize)
unmapped_categories.json    Queue of unclassified articles (read by /recategorize)
dashboard_data.json         Cumulative historical dataset
dashboard.html              Static dashboard — deploys via GitHub Pages
docs/
  retail_wire_drafting_reference.md   Bloomberg method + Retail Week style + learned preferences
.claude/skills/
  draft/        /draft skill
  recategorize/ /recategorize skill
  feedback/     /feedback skill
  update/       /update skill
.github/workflows/
  lse_scraper.yml   Scheduled GitHub Actions workflow
```

## Daily workflow

```
Morning
  → Dashboard updates automatically (GitHub Pages)
  → Local data updates automatically (Task Scheduler)

When you want to write
  → Double-click retail_wire.bat (pulls latest + opens Claude Code)
  → Find a story in the dashboard, copy its id
  → /draft 17754000

Mid-session refresh
  → /update

Categorise ambiguous items
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
| UK media scan | 🔜 Planned |
| Government data (ONS / GOV.UK) | 🔜 Planned |
| Company & supplier websites | 🔜 Planned |
| Events calendar (2-week agenda) | 🔜 Planned |
