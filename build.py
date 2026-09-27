"""Build this week's pick sheet data (sheet_data.json) from the engine."""
import json, datetime as dt
import numpy as np, pandas as pd
from engine import main, predict, phi, LABELS

def last_qb(g, team, season, before_week):
    prev = g[(g.season == season) & (g.week < before_week) & g.result.notna() &
             ((g.home_team == team) | (g.away_team == team))].sort_values("week")
    if prev.empty: return None
    r = prev.iloc[-1]
    return r.home_qb_name if r.home_team == team else r.away_qb_name

def et_to_utc(day, time):
    # ET is UTC-4 during the NFL regular season until early November, UTC-5 after
    d = dt.datetime.fromisoformat(f"{day}T{time}")
    off = 4 if d < dt.datetime(d.year, 11, 1) + dt.timedelta(days=(6 - dt.datetime(d.year, 11, 1).weekday()) % 7) else 5
    return (d + dt.timedelta(hours=off)).strftime("%Y-%m-%dT%H:%M:00Z")

def build(season=None, week=None):
    g, models, report, buckets, ntr, nte = main()
    season = season or int(g.season.max())
    if week is None:
        open_ = g[(g.season == season) & g.result.isna()]
        week = int(open_.week.min())
    wk = g[(g.season == season) & (g.week == week)].copy()
    out = []
    for _, r in wk.iterrows():
        preds = {}
        for name, (cols, coef, sigma) in models.items():
            m = float(predict(pd.DataFrame([r]), cols, coef)[0])
            preds[name] = {"margin": round(m, 1), "home_prob": round(float(phi(m / sigma)), 3)}
        cols, coef, _ = models["comb"]
        breakdown = {LABELS[c]: round(float(r[c] * k), 2) for c, k in zip(cols, coef)}
        facts = {
            "kickoff_et": f"{r.weekday} {r.gameday} {r.gametime} ET",
            "neutral_site": r.location == "Neutral",
            "divisional_game": bool(r.div_game),
            "roof": None if pd.isna(r.roof) else r.roof,
            "rest_days": {"away": int(r.away_rest), "home": int(r.home_rest)},
            "starting_qb": {"away": r.away_qb_name, "home": r.home_qb_name},
            "qb_last_game": {"away": last_qb(g, r.away_team, season, week), "home": last_qb(g, r.home_team, season, week)},
        }
        if not pd.isna(r.temp): facts["temp_f"] = r.temp
        if not pd.isna(r.wind): facts["wind_mph"] = r.wind
        out.append({
            "id": r.game_id, "away": r.away_team, "home": r.home_team,
            "neutral": bool(r.location == "Neutral"),
            "kickoff_utc": et_to_utc(r.gameday, r.gametime),
            "market": None if pd.isna(r.spread_line) else float(r.spread_line),
            "final": None if pd.isna(r.result) else [int(r.away_score), int(r.home_score)],
            "preds": preds, "breakdown": breakdown, "facts": facts,
        })
    data = {"sport": "NFL", "season": season, "week": week,
            "sigma": round(float(models["comb"][2]), 2), "built_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "backtest": {"season": 2025, "train_games": ntr, "test_games": nte,
                         "rows": [{k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in r.items()} for r in report],
                         "edge_buckets": buckets},
            "games": out}
    json.dump(data, open("sheet_data.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    return data

if __name__ == "__main__":
    d = build()
    print(d["season"], d["week"], len(d["games"]))
    for x in d["games"]:
        c = x["preds"]["comb"]; print(x["id"], x["market"], c, x["preds"]["eff"]["margin"], x["preds"]["elo"]["margin"], x["facts"]["qb_last_game"], x["facts"]["starting_qb"])
