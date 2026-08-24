---
name: feedback
description: Compares Claude's original drafts against the user's edited versions, identifies systematic style preferences, and updates docs/retail_wire_drafting_reference.md accordingly. Use when the user shares edited stories and wants to refine the drafting criteria.
---

# Update drafting criteria from edited stories

This skill learns from the difference between what Claude drafted and what
the user actually published. It updates `docs/retail_wire_drafting_reference.md`
so future `/draft` calls are closer to the user's real voice from the start.

## Process

1. Ask the user for their edited version and the article id (or filename
   in `drafts/`). Look for the original draft in `drafts/` — it should
   be saved there automatically by `/draft`. If it's not there, tell the
   user and offer to regenerate it from the article body before comparing.

2. For each pair, do a careful diff. Look for:
   - **Structural changes**: did they move paragraphs, cut the to-be-sure,
     shorten the nut graph?
   - **Tone changes**: did they make it terser, cut hedging language, remove
     "is pleased to announce" type phrases?
   - **Lead changes**: did they rewrite the first sentence, change the angle,
     lead with a different fact?
   - **Quote handling**: did they cut the quote, shorten it, or reframe it?
   - **Length**: systematically shorter or longer than Claude's version?

3. Identify patterns across all pairs — a change made in one story could be
   personal preference for that piece; the same change made in three stories
   is a rule. Only promote patterns to the reference document, not one-offs.

4. Read `docs/retail_wire_drafting_reference.md` in full before editing it.
   The document has two sections:
   - **Core method** (Bloomberg four-paragraph structure, Retail Week house
     style) — never touch this section. It's the foundation.
   - **Learned preferences** — this is where new rules go. If the section
     doesn't exist yet, create it at the bottom of the document.

5. Draft the proposed updates to the "Learned preferences" section and show
   them to the user BEFORE writing anything. Each rule should be:
   - Specific and actionable ("never use 'is pleased to announce'" not
     "avoid corporate language")
   - Attributed to evidence ("changed in 3 of 4 drafts reviewed")
   - Written as a positive instruction where possible ("lead with the
     percentage change" not "don't bury the number")

6. Only after the user confirms: update `docs/retail_wire_drafting_reference.md`
   with the approved changes. Then commit with a message like:
   `docs: update drafting preferences from [date] feedback session`
   and push to GitHub — so the learning is versioned and doesn't live
   only on this machine.

7. Summarise what was added, what was considered but rejected (and why),
   and what to watch for in the next feedback session.

## What NOT to do

- Don't update the core Bloomberg method section — that's the structure,
  not the style.
- Don't promote a change from a single story to a permanent rule.
- Don't commit without showing the proposed changes first.
- Don't push if the user says "save locally" — in that case, write the
  file but skip the git commit/push.
