# Retail Wire — UK retail news tracker

Editorial tracking tool for UK retail news, built for a Retail Week journalist.
Six modules are live and feed `dashboard.html`: LSE press releases, UK media
scan, government/statistics data, retailer corporate press, supplier/FMCG
press, and an events agenda. See README "Modules" table for the full backlog
of proposed-but-not-built modules (judiciary, expanded media, other trade
bodies, more agenda event types).

## Hard rule: where AI is and isn't allowed

This is the most important thing to know about this repo. Read it before
touching anything.

- **The automated pipeline never calls any AI/LLM.** That covers all six
  scrapers (`lse_scraper.py`, `media_scraper.py`, `gov_scraper.py`,
  `company_scraper.py`, `supplier_scraper.py`, `agenda/agenda_scraper.py`) and
  `transform_to_dashboard.py` — every one of them, not just the LSE module.
  It is 100% deterministic: scraping, relevance filtering (via
  `icbsectorcode`, retailer-name/keyword matching, or RSS source
  allowlists), and category mapping (via `category_map.json`) all run
  without judgement calls. This must stay true — do not add AI calls into
  any scheduled workflow, present or future.
- **AI judgement only happens through the skills below, invoked explicitly
  by the user in an interactive session.** Never run them automatically,
  never chain them into a scraper, never suggest doing the categorization
  or drafting "for free" as part of an unrelated task unless the user asks
  for it in that session.
- The rationale: token cost and control. The scrapers run 10-20x/day across
  all six modules combined; running AI on every item would be wasteful and
  would remove human oversight from editorial judgement calls. The skills
  exist precisely so those calls stay opt-in.

## Repo map

| File | What it does | Touches AI? |
|---|---|---|
| `schedule_guard.py` | Shared UK-local-time guard so cron doesn't need manual BST/GMT edits — see "Scheduling & DST" below | No |
| `lse_config.json` | Sectors, endpoint IDs, pagination, retention/archive settings — edit here, not in code | No |
| `lse_scraper.py` | Scrapes LSE News Explorer + article detail, filters by `icbsectorcode` | No |
| `category_map.json` | Code → (story type, is_noise). Deliberately excludes catch-all codes like `MSC` | No |
| `article_overrides.json` | Per-article id → editorial override (LSE items only). This is where `/recategorize` output lands | Yes (written by `/recategorize`) |
| `unmapped_categories.json` | Auto-maintained queue of LSE codes not yet in `category_map.json` | No (read by `/recategorize`) |
| `transform_to_dashboard.py` | LSE CSV → `dashboard_data.json`, applies category_map + overrides, dedups by id, archives items older than `keep_days_live` to `data/archive/` | No |
| `dashboard_data.json` | Live (recent-window) LSE dataset the dashboard reads | No |
| `data/archive/dashboard_data_archive.json` | Older LSE items moved out of the live file — nothing is deleted, just split for dashboard performance | No |
| `media_config.json` / `media_scraper.py` | UK media scan (trade press + nationals), filtered against `retailers.json` | No |
| `gov_config.json` / `gov_scraper.py` | Government/statistics/parliament sources, filtered by priority + retailer/keyword match | No |
| `company_config.json` / `company_scraper.py` | Retailer corporate press pages via Google News RSS — everything from these sources is relevant by definition | No |
| `supplier_config.json` / `supplier_scraper.py` | FMCG/fresh-food/wholesale suppliers to retailers (not retailers themselves) via Google News RSS — same "everything is relevant" pattern as company | No |
| `agenda/agenda_config.json` / `agenda/agenda_scraper.py` + `agenda/scrapers/*.py` | Forward-looking events calendar (ONS releases, earnings dates, parliamentary committees, BRC reports, BoE MPC dates, sector trade shows, National Living Wage effective date) + manual events | No |
| `retailers.json` / `sector_config.json` | Shared retailer name lists (with ambiguous-name/context-keyword handling), sector/category keyword maps, and `tech_signal` keyword pairs (partnership + tech/AI) used by media/company/supplier scrapers | No |
| `dashboard.html` | Static dashboard, no build step, deploys via GitHub Pages, reads all six data files | No |
| `.github/workflows/*.yml` | One workflow per module, each schedules both BST and GMT UTC times (see below) and commits its own data file | No |
| `docs/retail_wire_drafting_reference.md` | Bloomberg method + Retail Week house style — the drafting reference | Read by `/draft` |
| `drafts/` | Where `/draft` saves output. Gitignored by default — personal scratch space | Written by `/draft` |

## Scheduling & DST

All six workflows target fixed UK local times (e.g. LSE at 07:01/07:15).
GitHub Actions cron only understands UTC, so each `.yml` schedules **both**
the BST-correct and the GMT-correct UTC time for every target. At the top of
each scraper's `run()`, `schedule_guard.should_run(config["schedule"]["runs_uk"])`
checks the real Europe/London wall-clock time and does nothing (no fetch, no
commit) on the half of the doubled cron that doesn't currently apply.
**Consequence: nobody ever needs to hand-edit a cron schedule for DST again.**
If you add a new scheduled time, add it to the module's config `schedule.runs_uk`
list (human-readable UK local time) and add both UTC cron lines to the `.yml`.
A manual `workflow_dispatch` run always executes regardless of time (via the
`FORCE_RUN=true` env var set in each workflow for that trigger).

## Conventions

- Config lives in JSON files, not hardcoded in scripts — if you're adding
  a new tunable value, it goes in a config file, not a Python constant.
- Scheduled UK local times live in each config's `schedule.runs_uk` — see
  "Scheduling & DST" above. Don't hardcode times in Python or reintroduce
  manual DST-offset comments in the workflow files.
- Every story in the dashboard must carry a source URL. Never generate or
  guess a URL — only use one confirmed from the scraper.
- New LSE category codes will keep appearing over time. Don't guess their
  meaning and add them to `category_map.json` yourself — that's exactly
  what `/recategorize` is for, since it reads the actual article body
  before deciding. Media/gov/company items don't go through this
  code-based classification at all (they have no RNS category code) —
  they carry `story_type: null` until a future skill covers them (see
  README backlog).
- Each scraper fails loudly (non-zero exit) if it fetches **zero** raw
  items across **every** configured source in a run — that's a signal the
  scraper broke (site/feed changed), not that there was no news. Don't
  swallow that exit code in a workflow edit.
- For Google News RSS sources (company/supplier configs): use free-text
  queries (`"Company Name" announces OR launches OR results`), not
  `site:domain.com/path`. Confirmed by diagnosis on 2026-08-30 across 30+
  sources: Google News' `site:` operator ignores subpaths entirely (always
  0 results), and a bare domain returns generic site crawl (product/careers
  pages) instead of press content. Run `diagnose_sources.py` after adding
  a new source to confirm it actually returns on-topic results before
  committing it.
- For any multinational supplier/vendor (not UK-headquartered, or with
  major non-UK operations — Diageo, Reckitt, Coca-Cola Europacific
  Partners, RELEX Solutions, etc.), add `+UK+` to the query. This is
  necessary but **not sufficient**: Google News RSS does relevance
  ranking, not strict boolean AND — confirmed 2026-08-30 that even with
  `+UK+` in the query, an occasional clearly-non-UK item (a US "Dollar
  General" deal, for RELEX Solutions) still surfaces. Don't try to
  post-filter this away with a stricter keyword rule — it trades false
  negatives (dropping real UK stories that don't happen to say "UK") for
  a small reduction in already-rare false positives. Treat it the same
  as any other Google News source: a strong signal, not a guarantee, and
  the source_name on every item makes an obviously-irrelevant one easy
  for a human to skip.
- `gov_scraper.py` and `media_scraper.py` both split retailer names into
  "clear" vs. `retailers.json`'s `ambiguous: true` set, and require an
  `ambiguous_context_keywords` hit before an ambiguous name counts as a
  match (e.g. "Next" only counts with retail context nearby). This
  matters more than it looks: confirmed 2026-08-30 that without it, a
  high-volume generic source (the caselaw.nationalarchives.gov.uk
  firehose, added that day) produced a false positive — "Next Friend" (a
  legal term) matched the retailer "Next" in a case with zero UK retail
  relevance. If you add a new scraper that filters by retailer name
  against a "medium"/"low" priority firehose-style source, port this
  same clear/ambiguous split — don't just flatten all names into one set.
- Never invent a date for an agenda event. `agenda_boe.py` and
  `agenda_tradeshows.py` parse a real page for the date and return
  nothing if the expected pattern isn't found (see their docstrings).
  `agenda_nlw.py` calculates a fixed statutory date (1 April) but
  deliberately omits the wage rate, since that's announced separately
  with no fixed date. The Budget/Autumn Statement date and the business
  rates revaluation cycle were left out of the agenda module entirely
  for the same reason — no reliable live source was found; don't add a
  guessed date for either without verifying a real source first.
- `tech_signal` (on company/media/supplier items) is a deterministic tag —
  title/summary matches a partnership keyword AND a tech/AI keyword
  (`sector_config.json` -> `tech_signal`), both lists. It exists to surface
  retailer tech vendor deals and AI rollouts without AI judgement in the
  pipeline. If it's too noisy or misses real stories, tune the keyword
  lists — don't replace it with an AI classification call.
- `git pull` in the commit step of each workflow uses `--rebase` (not
  `--strategy=ours`). Each workflow only ever touches its own data file, so
  a plain rebase is safe and — unlike `--strategy=ours` — won't silently
  discard another workflow's commit if two pushes race.

## Skills

- `/recategorize` — reviews `unmapped_categories.json` against article
  bodies in `dashboard_data.json` and writes judgement calls to
  `article_overrides.json`. LSE-only (the RNS category-code queue doesn't
  exist for the other modules). Read the full skill for the exact process.
- `/draft` — drafts a story for an article, searchable across
  `dashboard_data.json` (LSE, by id), and `media_data.json` /
  `gov_data.json` / `company_data.json` / `supplier_data.json` (by
  company/headline match, no numeric id). Never runs automatically.
- `/feedback` — compares edited drafts against originals to refine
  `docs/retail_wire_drafting_reference.md`.
- `/update` — pulls latest data from GitHub mid-session.
