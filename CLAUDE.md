# Pick Engine

Multi-sport betting pick sheet, modeled on a friend's college football sheet. Each sport gets math models,
four Claude "nudge" reviewers that never see the betting line, and the market shown for comparison only.
Output is one self-contained HTML site with a tab per sport.

Live today: NFL, Premier League (EPL). Planned tabs: La Liga, Serie A, Bundesliga, Ligue 1, Champions League,
Liga MX, Nations League, UFC.

## Read first
Detailed knowledge lives in `docs/pick-sheet/`. Read the file that matches the task before changing code:
- `architecture.md`: folders, data flow, how the pieces fit
- `models-nfl.md`, `models-nfl-props.md`, `models-epl.md`: features, training windows, backtest results
- `nudges.md`: the four Claude setups, prompt v4 vs v5, locking rules
- `site.md`: page design and the viewer gotchas that caused blank pages
- `data-sources.md`: where every dataset comes from
- `weekly-runbook.md`: the commands to run each week
- `adding-a-sport.md`: checklist for new tabs

## Commands
    pip install -r requirements.txt
    python fetch_data.py                 # NFL data (nflverse)
    python build.py                      # NFL: train, backtest, predict next week -> sheet_data.json
    python fetch_player_data.py          # NFL rosters, injury reports, depth charts (used by injuries.py)
    python props_build.py                # NFL anytime TD -> props_data.json
    cd epl && python epl_build.py && cd ..   # EPL -> epl/epl_data.json
    python nudge.py all                  # Claude nudges (needs ANTHROPIC_API_KEY)
    python render.py                     # -> pick_sheets.html

## Rules
- API key: read `ANTHROPIC_API_KEY` from the environment or a `.env` file. Never hardcode it, print it, or commit it.
  Keep `.env` in `.gitignore`.
- Injury reports and expected starters come from `injuries.py`; refresh them close to kickoff, since statuses change late in the week.
- Nudge models never receive betting lines or odds. Keep market data out of every prompt payload.
- A saved nudge is never overwritten, and games that have kicked off are skipped. Do not add a "force" option.
- Train only on seasons before the test season. Report backtests honestly, including when the market wins.
- Spread convention everywhere: positive = home team favored (nflverse `spread_line`). Model margins are home minus away.
- Keep `site_template.html` self-contained: inline CSS/JS, no external scripts except the Google Fonts stylesheet.
- In the page script, wrap everything in one IIFE and never declare a top-level name `claude`
  (the claude.ai viewer defines it, and a clash blanks the page). Wrap `history`/`location` calls in try/catch.
- After changing the page, test it in a sandboxed iframe with an injected `const claude` global before publishing.
- Write in plain English on the page. No em dashes in user-facing text.
