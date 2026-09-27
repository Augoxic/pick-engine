# Pick Engine (NFL, v1)

A weekly NFL pick sheet in the style of the college football sheet: three math models,
optional Claude nudges that never see the betting line, and Vegas shown for comparison.

## Run it each week

    pip install -r requirements.txt
    python fetch_data.py        # refreshes schedule, lines, results and this season's play-by-play
    python build.py             # trains, backtests on 2025, predicts the next unplayed week -> sheet_data.json
    python render.py            # writes pick_sheet.html

Publish or open `pick_sheet.html`. When it is opened in claude.ai, the "Get Claude nudges"
button asks Claude at three effort levels to review the games and saves the nudges the first time.

## The models

- **Elo**: team strength from every game since 1999, with margin of victory and a pull back toward average each offseason.
- **Elo + efficiency**: adds offensive minus defensive EPA per play.
- **Combined**: adds success rate, special teams EPA, penalty yards, rest days and home field.
  Weights are fit by least squares on 2014 to 2024 and tested on 2025.

Current-season stats are blended with last season's (shrunk halfway to average) until a team has a few games.

## Data

nflverse (github.com/nflverse): `games.csv` has schedules, scores, closing spreads, moneylines,
starting QBs and rest days. Play-by-play files supply EPA and success rate.
Spread convention: positive `spread_line` means the home team is favored.

## Adding sports

The page and nudge flow are sport-agnostic. Each new sport needs its own data fetch and model:
soccer needs win/draw/loss probabilities (Elo plus a goals model), and UFC needs fighter-level ratings.

# Premier League (v1)

    pip install scikit-learn git+https://github.com/AnishKhetani/premier-league-data
    cd epl
    curl -sLO https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/en.1.json && mv en.1.json en1_2627.json
    # update markets.json with the coming matchday's win/draw/loss prices (percent, home|away keys)
    python epl_build.py         # trains on 2012-13 to 2024-25, tests on 2025-26, predicts the next matchday
    cd .. && python render.py   # writes pick_sheets.html with a tab per sport

## The EPL models

- **Elo**: club strength since 1993-94, weighted by goal difference. Promoted clubs start where the relegated clubs finished.
- **Goals model**: a Poisson model of each club's attack and defence over the last three years, with older matches fading
  (240-day half-life) and an extra adjustment for newly promoted clubs.
- **Combined**: a win/draw/loss model that blends the Elo gap, expected goal difference, expected total goals and rest.

Historical results and closing odds: football-data.co.uk via the premier-league-data package.
Current season results and fixtures: openfootball.

# Claude nudges (all sports)

Four setups review every slate, matching the original college football sheet:

| Row on the sheet       | Model id                    | Prompt | Settings                                  |
|------------------------|-----------------------------|--------|-------------------------------------------|
| Haiku 4.5 (prompt v4)  | claude-haiku-4-5-20251001   | v4     | temperature 0, no thinking                |
| Haiku 4.5              | claude-haiku-4-5-20251001   | v5     | temperature 0, no thinking                |
| Sonnet 5               | claude-sonnet-5             | v5     | adaptive thinking, default effort (high)  |
| Opus 5.5               | claude-opus-5-5             | v5     | adaptive thinking, default effort (medium)|

    export ANTHROPIC_API_KEY=sk-ant-...
    python nudge.py all      # before the first kickoff of the slate
    python render.py

Nudges land in nudges/<sport>/<slate>.json. Each game is written once, only before kickoff, and never overwritten.
Prompts live in nudge.py; adding a sport means adding one entry to SPORTS there.
