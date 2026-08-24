---
name: update
description: Pulls the latest changes from GitHub and shows how many new stories arrived since the last update. Use when the user wants to refresh data mid-session without restarting Claude Code.
---

# Pull latest data from GitHub

Run this at any point during a session to make sure you have the freshest
data before drafting or recategorizing.

## Process

1. Run `git pull` in the repo root.
2. If nothing changed ("Already up to date"), tell the user and stop.
3. If there were changes, check `dashboard_data.json` for items added
   since the previous `generated_at` timestamp:
   - How many new stories arrived
   - Which companies / story types
4. Show a brief summary so the user can decide whether to draft something
   new before continuing.
