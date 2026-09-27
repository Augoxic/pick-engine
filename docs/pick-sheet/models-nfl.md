# NFL models

## Elo
- Every game since 1999 from nflverse `games.csv`. K = 20, home field 48 Elo points, margin-of-victory multiplier
  `ln(|mov|+1) * 2.2 / (winner_elo_diff * 0.001 + 2.2)`, each team pulled 1/3 back toward 1505 each offseason.
- Feature: Elo gap in points = (home Elo - away Elo) / 25, without home field.
- Relocated franchises keep their history: SD -> LAC, STL -> LA, OAK -> LV.

## Team efficiency (from play-by-play, 2013 onward)
Per team per game: offensive and defensive EPA per play and success rate (pass and run plays), special teams EPA
(kickoffs, punts, field goals, extra points; for minus against), penalty yards committed.
Pre-game rating for week W = mean of that season's games before W, blended with last season's final value shrunk
halfway to league average. Weight on current season = n / (n + 4), where n = games played.

## Models (least squares on home margin)
- Elo: [elo_pts, home]
- Elo + efficiency: [elo_pts, net_epa, home]
- Combined: [elo_pts, net_epa, net_sr, special teams, penalties, rest (capped +/-7), home]
  `net_x = (home off - home def) - (away off - away def)`. Home = 0 at neutral sites.
- Win probability = normal CDF(margin / sigma), sigma = residual std on training data (about 13.2).

## Training and test
Fit on 2014 to 2024 (about 3,000 games). Test on 2025 (285 games).

| Predictor | Winners | Brier | Against the spread |
|---|---|---|---|
| Vegas closing | 66.3% | 0.210 | |
| Elo | 64.6% | 0.222 | 143-141 |
| Elo + efficiency | 65.3% | 0.220 | 139-145 |
| Combined | 64.6% | 0.218 | 147-137 (51.8%) |

Key lesson: when Combined disagreed with the spread by 5+ points it went 10-18 ATS. Large gaps usually mean the
market knows something (injury, QB change). The page states this plainly.

## Facts passed to Claude
Kickoff, neutral site, division game, roof, rest days, this week's listed starting QBs and each team's QB from its
previous game (a mismatch flags a QB change), temperature and wind when known.
