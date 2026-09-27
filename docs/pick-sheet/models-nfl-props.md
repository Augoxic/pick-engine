# NFL anytime TD model

Predicts the chance each active QB/RB/WR/TE scores a rushing or receiving TD (passing TDs don't count for QBs).

## Data (all nflverse)
- Play-by-play 2014 onward: carries, targets, red-zone (inside the 20) carries and targets, goal-line (inside the 5)
  carries, and TDs per player per game, plus team red-zone totals.
- Weekly rosters (`roster_weekly_<year>`): candidates are status ACT, regular season.
- Injury reports (`injuries_<year>`): Out and Doubtful removed, Questionable flagged.
- games.csv: implied team points = (total_line +/- spread_line) / 2, and the listed starting QB id.

## Features (all known before kickoff)
Exponentially weighted (4-game half-life) carries, targets, red-zone carries and targets, goal-line carries, TD rate;
red-zone carry share and target share of the team; implied team points and its product with each share; games of
history; position; `played_share` = share of the team's games this season in which the player touched the ball
(catches backups and players who changed roles). Only the team's listed starting QB is a candidate.

## Model and results
Gradient-boosted trees (chosen over logistic regression on the 2024 validation season). Trained 2016-2024,
tested on 2025 (6,505 player-games, 17% scored).

| Predictor | Brier | Log loss |
|---|---|---|
| TD model | 0.121 | 0.389 |
| Position average | 0.138 | 0.448 |
| Player's recent TD rate | 0.136 | 0.446 |

Well calibrated in every band. The top 10 per week scored 58% of the time (predicted 53%).
No historical prop odds are available in nflverse, so the page shows fair odds instead of a market comparison:
a bet only has value when the book pays longer than the fair price.

## Run
    python props_build.py      # after build.py; writes props_data.json for the same week
    python render.py           # adds it to the NFL tab under "Anytime TD"
