# Architecture

## Folder layout
    CLAUDE.md
    requirements.txt           pandas, numpy, pyarrow, scikit-learn, premier-league-data (git)
    fetch_data.py              downloads NFL data into data/
    engine.py                  NFL: Elo, features, model fitting, backtest
    build.py                   NFL: picks the next unplayed week, writes sheet_data.json
    epl/epl_engine.py          EPL: Elo, Poisson goals model, combined model, backtest
    epl/epl_build.py           EPL: next matchday, writes epl/epl_data.json
    epl/markets.json           EPL market prices, entered by hand each matchday
    epl/en1_2627.json          current-season EPL fixtures and results (openfootball)
    nudge.py                   calls the four Claude setups, saves nudges/<sport>/<slate>.json
    render.py                  merges sheet data + nudges into site_template.html -> pick_sheets.html
    site_template.html         the whole site (tabs, one panel per sport)
    nudges/<sport>/<slate>.json    locked nudges (commit these; they are the record)
    docs/pick-sheet/           this knowledge base

## Data flow
1. Fetch raw data (nflverse, premier-league-data, openfootball).
2. Engine builds pre-game features using only information available before each game.
3. Models are fit on training seasons, scored on the held-out test season, then used to predict the next slate.
4. Build scripts write one JSON per sport: games, predictions, breakdown, facts, market, backtest.
5. nudge.py sends each sport's facts and model output (never the market) to four Claude setups and locks the replies.
6. render.py injects each sport's JSON (with nudges) into the template as `__NFL__`, `__EPL__`, etc.

## Sheet JSON contract (per sport)
- `games[]`: `id`, `home`, `away`, `kickoff_utc` (ISO, Z), `final` (null or scores), `market`, plus sport-specific
  prediction fields. NFL: `preds.{elo,eff,comb}.{margin,home_prob}`, `breakdown`, `facts`, `neutral`.
  EPL: `probs.{elo,goals,comb}` as [home, draw, away], `xg`, `features`, `facts`.
- `backtest`: training/test counts and a `rows` table for the page.
- `nudges`: added by render.py, `{setup_key: {game_id: {nudge, reason, model, prompt, saved_utc}}}`.
