# Adding a sport

1. Data: find free historical results plus closing odds for backtesting, and a current-season fixture source.
2. Engine: `<sport>/<sport>_engine.py` with pre-game-only features, a train/validation/test split by season,
   and a backtest against the market. Report honestly.
3. Build: `<sport>/<sport>_build.py` writing `<sport>_data.json` in the contract from architecture.md.
4. Nudges: add an entry to `SPORTS` in `nudge.py` (data path, clamp, slate name, payload, v4 and v5 prompts).
   Payloads must not contain odds.
5. Page: add a sport block in `site_template.html` with `build` and `render`, flip its tab from "soon" to live,
   and add `__<SPORT>__` in render.py.
6. Test in the sandboxed iframe with the injected `claude` global, desktop and mobile.

## Plans per sport
- La Liga, Serie A, Bundesliga, Ligue 1: reuse the EPL engine with the league's data; football-data.co.uk
  covers all four with odds.
- Champions League: cross-league, so club Elo must span leagues (ClubElo-style) rather than per-league ratings.
- Nations League: international Elo (eloratings.net style) from martj42/international_results on GitHub.
- Liga MX: thinner data; Apertura/Clausura split seasons and a playoff (Liguilla).
- UFC: fighter-level Elo from fight history; few fights per fighter, so expect noisy predictions and wide uncertainty.
