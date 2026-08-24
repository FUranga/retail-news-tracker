---
name: recategorize
description: Reviews items in unmapped_categories.json against their article body in dashboard_data.json, assigns an editorial story_type and noise judgement, and writes the result to article_overrides.json. Use when the user asks to recategorize, review ambiguous items, clear the review queue, or work through unmapped_categories.json.
---

# Recategorize ambiguous items

This is an on-demand, explicitly-invoked task. Never run this as part of
scraping or any automated flow — only when the user asks for it in this
session.

## Process

1. Read `unmapped_categories.json`. If it's empty (`{}`), tell the user
   the review queue is clear and stop — nothing else to do.
2. For each code in the queue, look at its `examples` (article ids and
   titles). For each example id, find the matching item in
   `dashboard_data.json` and read its full `body` text — the code alone
   is not enough context, the title alone is not enough either.
3. For each article, decide:
   - `story_type`: a short, specific label (e.g. "Partnership", "Product
     Launch", "Strategy", "Restructuring") — not a repeat of "Other".
   - `is_noise`: true only if this is regulatory boilerplate unlikely to
     ever be a story (compare against the existing noise categories in
     `category_map.json` — POS, HOL, AGM, TVR — as the bar for "noise").
   - A one-to-two sentence `note` explaining the call in plain English,
     referencing something specific from the body (a figure, a quote, a
     deal detail) — not a generic justification.
4. Write each decision to `article_overrides.json`, keyed by article id
   as a string, with `reviewed_by: "claude-code"` and the note. Preserve
   any existing entries already in the file — this is an update, not an
   overwrite of the whole file.
5. Do NOT edit `category_map.json` directly unless the user explicitly
   asks you to promote a code to a permanent mapping (e.g. "always treat
   XYZ as a Dividend story") — by default, overrides stay per-article,
   because catch-all codes like MSC don't reliably mean the same thing
   twice.
6. After writing `article_overrides.json`, run:
   `python transform_to_dashboard.py lse_latest.csv`
   (or the most recent CSV in `data/raw/` if `lse_latest.csv` isn't
   present) to regenerate `dashboard_data.json` with the overrides
   applied, and confirm `unmapped_categories.json` is now empty or
   reduced.
7. Summarize what was reclassified — one line per article, story_type,
   and a short reason — so the user can review the calls before pushing.
   Do not `git commit` or `git push` automatically; ask first, since this
   changes editorial judgement, not just data.

## If the same code recurs across many unrelated stories

If you notice a code (e.g. MSC) keeps appearing for stories that all turn
out to be genuinely the same type — flag this to the user explicitly and
suggest promoting it to `category_map.json` instead of continuing to
override it article-by-article. Don't make that call unilaterally.
