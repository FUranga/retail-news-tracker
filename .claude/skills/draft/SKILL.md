---
name: draft
description: Drafts a news story for a given article id from dashboard_data.json, following the Bloomberg four-paragraph method and Retail Week house style. Use when the user asks to draft, write up, or turn into a story a specific article, by id, ticker, or headline text.
---

# Draft a story

This is an on-demand, explicitly-invoked task. Never draft automatically
as a side effect of scraping, recategorizing, or any other task.

## Process

1. Read `docs/retail_wire_drafting_reference.md` in full — this is the
   method and style reference. Do not draft from memory of a previous
   session; re-read it each time in case it's been edited.
2. Find the article the user means. There are five possible data sources,
   and the id scheme differs between them:
   - `dashboard_data.json` (stream: LSE press releases) — has a numeric
     `id`. If the user gives a bare number, look here first.
   - `media_data.json`, `gov_data.json`, `company_data.json`,
     `supplier_data.json` — no numeric id, only a `url`. Match by company
     name, headline text, or a pasted URL. If the user's request doesn't
     obviously point at an LSE id, search all four files for the best
     text match rather than assuming LSE.
   - If more than one plausible match exists (in one file or across
     files), list the candidates (source, company, headline, date) and
     ask which one before drafting.
3. If the item has no `body` text, say so and ask whether to draft from
   the headline/summary/metadata alone (much weaker) or stop — don't
   silently pad a thin draft to look complete. This is more likely for
   `company_data.json`/`supplier_data.json` items, where body-fetching is
   intentionally disabled (too slow for corporate press pages) — the
   skill should still work from `summary` in that case, just flag that
   it's thinner sourcing than an LSE item with a full RNS body.
4. Also check for editorial context before drafting:
   - LSE items: an `article_overrides.json` entry or `review_note` on
     the item — if present, that judgement call (why it matters, what
     kind of story it is) should inform the angle of the draft.
   - Media/gov/company/supplier items: `story_type` is `null` by design
     (these streams aren't run through the LSE category-code classifier) — a
     `match_reason` field (e.g. `retailer:tesco`, `keyword:business
     rates`) is the closest thing to editorial context; use it to
     understand why the item was captured at all.
5. Write the draft following the reference file exactly: headline
   (≤64 characters), the four-paragraph lead, a to-be-sure paragraph
   where a genuine other side exists, and an explicit note if no usable
   quote was available (never invent one).
6. Also check other items — across all five data files, not just the one
   the source article came from — for the same company or a closely
   related one from the last few days. If something adds useful context
   (a prior trading update, a related M&A story, government data that
   bears on the story), mention it as a possible addition, but keep the
   draft itself focused.
7. Save the draft to `drafts/` automatically without asking — the user
   always wants it saved for the `/feedback` workflow:
   - LSE items: `drafts/<id>-<slugified-headline>.md`
   - Media/gov/company/supplier items (no numeric id): `drafts/<stream>-<slugified-headline>.md`
     (e.g. `drafts/media-tesco-half-year-results.md`)
   Tell the user the filename so they know where to find it.
8. Never commit or push draft files — `drafts/` is scratch space, not
   part of the published dataset.
