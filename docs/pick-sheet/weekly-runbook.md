# Weekly runbook

Run before the first kickoff of each slate.

## NFL (Thursday before the week, or Sunday morning at the latest)
    python fetch_data.py
    python fetch_player_data.py   # rosters, injury reports, depth charts (run again Sunday morning for final statuses)
    python build.py
    python props_build.py

## EPL (before each matchday)
    cd epl
    curl -sL -o en1_2627.json https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/en.1.json
    # update markets.json with current home/draw/away prices for the matchday
    python epl_build.py
    cd ..

## Nudges and page
    python nudge.py all        # needs ANTHROPIC_API_KEY
    python render.py

Then open or publish `pick_sheets.html`. Commit `nudges/` so the locked record is kept.

## After games finish
Rebuild the same week to show finals; the page marks each predictor right (green) or wrong (red).
Consider keeping a season log of nudge accuracy per setup (not built yet).
