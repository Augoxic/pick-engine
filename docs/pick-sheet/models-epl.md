# Premier League models

Soccer has three outcomes, so every model outputs [home win, draw, away win].

## Elo
- All Premier League matches since 1993-94. K = 20, home advantage 60, goal-difference multiplier
  (1 for 0-1 goals, 1.5 for 2, (11 + gd) / 8 above that), 10% pull toward 1500 each summer.
- Newly promoted clubs start at the average end-of-season Elo of the clubs that were relegated.

## Goals model
Poisson regression refit each week on the last 3 years of matches, weighted with a 240-day half-life.
Features: attack one-hot, opponent defence one-hot, home, and flags for newly promoted attacker/defender.
Output: expected goals for each side; probabilities from independent Poisson scorelines (0 to 9 goals).

## Combined
Multinomial logistic regression on [elo_diff, xg_diff, xg_total, rest_diff]. Coefficients are exported into the
sheet JSON so the page can recompute probabilities when Claude nudges xg_diff.

## Training and test
Fit on 2012-13 to 2024-25 (4,940 matches). Validated feature choices on 2023-25, then tested once on 2025-26 (380).

| Predictor | Picked the result | Brier (3-way) | Value bets vs closing odds |
|---|---|---|---|
| Market (closing average, de-vigged) | 49.5% | 0.608 | |
| Elo | 47.1% | 0.626 | 270 bets, -10.6% |
| Goals model | 47.1% | 0.620 | 263 bets, -7.1% |
| Combined | 47.6% | 0.623 | 258 bets, -9.0% |

Value bet = back the outcome the model rates 3+ points above the market. The market beat every model; the page
says so. Uniform guessing scores a Brier of 0.667.

## Known gaps
- Current-season data (openfootball) has goals but no shots, so there is no shots or xG feature yet.
- No European or cup fixtures, so rest only counts league matches.
- Market prices for the upcoming matchday are entered by hand in `epl/markets.json`.
