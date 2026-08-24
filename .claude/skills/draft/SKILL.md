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
2. Find the article the user means in `dashboard_data.json` — by id if
   given, otherwise by matching company/ticker/headline text. If more
   than one plausible match exists, ask which one before drafting.
3. If the item has no `body` text, say so and ask whether to draft from
   the headline/metadata alone (much weaker) or stop — don't silently
   pad a thin draft to look complete.
4. Also check if the item has an `article_overrides.json` entry or a
   `review_note` — if so, that editorial context (why it matters, what
   kind of story it is) should inform the angle of the draft.
5. Write the draft following the reference file exactly: headline
   (≤64 characters), the four-paragraph lead, a to-be-sure paragraph
   where a genuine other side exists, and an explicit note if no usable
   quote was available (never invent one).
6. Also check other items in `dashboard_data.json` for the same company
   or a closely related one from the last few days — if something adds
   useful context (a prior trading update, a related M&A story), mention
   it as a possible addition, but keep the draft itself focused.
7. Save the draft to `drafts/` automatically as
   `drafts/<id>-<slugified-headline>.md` without asking — the user
   always wants it saved for the `/feedback` workflow. Tell the user
   the filename so they know where to find it.
8. Never commit or push draft files — `drafts/` is scratch space, not
   part of the published dataset.
