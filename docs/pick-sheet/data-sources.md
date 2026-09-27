# Data sources

| Sport | What | Source |
|---|---|---|
| NFL | Schedules, scores, closing spread and moneylines, starting QBs, rest, roof, weather | nflverse `nfldata/data/games.csv` (GitHub) |
| NFL | Play-by-play with EPA and success rate, 2013 onward | nflverse-data releases `pbp/play_by_play_<year>.parquet` |
| EPL | Results since 1993-94, closing odds by season | `premier-league-data` package (football-data.co.uk data), `load_results`, `load_results_with_odds(season)` |
| EPL | Current season fixtures and results | openfootball `football.json/<season>/en.1.json` |
| EPL | Upcoming match prices | entered by hand in `epl/markets.json` (percent, key "Home|Away") |

Notes
- nflverse `spread_line` is positive when the home team is favored.
- For EPL closing odds use the `market_avg_1x2_*_close` columns; Pinnacle columns are missing for many 2025-26 matches.
- openfootball uses full club names ("Arsenal FC"); `OF_NAMES` in `epl_engine.py` maps them to football-data names.
- Current-season openfootball files are updated by volunteers; re-download before each matchday.
