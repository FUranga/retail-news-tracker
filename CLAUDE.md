# Retail Wire — UK retail news tracker

Editorial tracking tool for UK retail news, built for a Retail Week journalist.
Module 1 (LSE press releases) is live. More modules (media scan, government
data, events calendar) are planned but not built yet.

## Hard rule: where AI is and isn't allowed

This is the most important thing to know about this repo. Read it before
touching anything.

- **The automated pipeline (GitHub Actions, `lse_scraper.py`,
  `transform_to_dashboard.py`) never calls any AI/LLM.** It is 100%
  deterministic: scraping, sector filtering (via `icbsectorcode`), and
  category mapping (via `category_map.json`) all run without judgement
  calls. This must stay true — do not add AI calls into the scheduled
  workflow.
- **AI judgement only happens through the two skills below, invoked
  explicitly by the user in an interactive session.** Never run them
  automatically, never chain them into the scraper, never suggest doing
  the categorization or drafting "for free" as part of an unrelated task
  unless the user asks for it in that session.
- The rationale: token cost and control. The user runs the scraper
  5-10x/day; running AI on every item would be wasteful and would remove
  human oversight from editorial judgement calls. The two skills exist
  precisely so those calls stay opt-in.

## Repo map

| File | What it does | Touches AI? |
|---|---|---|
| `lse_config.json` | Sectors, endpoint IDs, pagination — edit here, not in code | No |
| `lse_scraper.py` | Scrapes LSE News Explorer + article detail, filters by `icbsectorcode` | No |
| `category_map.json` | Code → (story type, is_noise). Deliberately excludes catch-all codes like `MSC` | No |
| `article_overrides.json` | Per-article id → editorial override. This is where skill output lands | Yes (written by `/recategorize`) |
| `unmapped_categories.json` | Auto-maintained queue of codes not yet in `category_map.json` | No (read by `/recategorize`) |
| `transform_to_dashboard.py` | CSV → `dashboard_data.json`, applies category_map + overrides, dedups by id | No |
| `dashboard_data.json` | Cumulative historical dataset the dashboard reads | No |
| `dashboard.html` | Static dashboard, no build step, deploys via GitHub Pages | No |
| `.github/workflows/lse_scraper.yml` | Runs scraper on schedule (07:01 / 07:15 UK time, weekdays), commits result | No |
| `docs/retail_wire_drafting_reference.md` | Bloomberg method + Retail Week house style — the drafting reference | Read by `/draft` |
| `drafts/` | Where `/draft` saves output. Gitignored by default — personal scratch space | Written by `/draft` |

## Conventions

- Config lives in JSON files, not hardcoded in scripts — if you're adding
  a new tunable value, it goes in a config file, not a Python constant.
- All dates/times in the codebase are UK local time in comments/docs, but
  GitHub Actions cron is UTC — see the DST note in the workflow file.
- Every story in the dashboard must carry a source URL. Never generate or
  guess a URL — only use one confirmed from the scraper.
- New LSE category codes will keep appearing over time. Don't guess their
  meaning and add them to `category_map.json` yourself — that's exactly
  what `/recategorize` is for, since it reads the actual article body
  before deciding.

## Skills

- `/recategorize` — reviews `unmapped_categories.json` against article
  bodies in `dashboard_data.json` and writes judgement calls to
  `article_overrides.json`. Read the full skill for the exact process.
- `/draft` — drafts a story for a given article id using the Bloomberg
  method + Retail Week style reference. Never runs automatically.
