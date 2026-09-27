"""Build the next EPL matchday's sheet data (epl_data.json)."""
import json, datetime as dt
import numpy as np, pandas as pd
from epl_engine import main, poisson_probs, MODELS

def uk_to_utc(date, time):
    d = dt.datetime.fromisoformat(f"{date.date()}T{time}")
    last_sun = lambda y, m: max(dt.datetime(y, m, day) for day in range(25, 32) if dt.datetime(y, m, day).weekday() == 6)
    bst = last_sun(d.year, 3) <= d < last_sun(d.year, 10)
    return (d - dt.timedelta(hours=1 if bst else 0)).strftime("%Y-%m-%dT%H:%M:00Z")

def table_and_form(df, season):
    s = df[(df.season == season) & df.hg.notna()]
    rows = {}
    for r in s.itertuples():
        for t, gf, ga in [(r.home, r.hg, r.ag), (r.away, r.ag, r.hg)]:
            x = rows.setdefault(t, {"p": 0, "pts": 0, "gd": 0, "gf": 0, "form": []})
            x["p"] += 1; x["gd"] += gf - ga; x["gf"] += gf
            res = "W" if gf > ga else "D" if gf == ga else "L"; x["pts"] += {"W": 3, "D": 1, "L": 0}[res]; x["form"].append(res)
    order = sorted(rows, key=lambda t: (-rows[t]["pts"], -rows[t]["gd"], -rows[t]["gf"]))
    for i, t in enumerate(order): rows[t]["pos"] = i + 1
    return rows

def build():
    df, fitted, probs, report, ntr, nte, elo = main()
    season = "2026-27"
    upcoming = df[(df.season == season) & df.hg.isna()]
    rnd = upcoming.iloc[0]["round"]
    wk = df[(df.season == season) & (df["round"] == rnd)]
    tab = table_and_form(df, season)
    mk = json.load(open("markets.json"))
    games = []
    for _, r in wk.iterrows():
        one = pd.DataFrame([r])
        p = {n: [round(float(v), 3) for v in probs(n, one)[0]] for n in ["elo", "goals", "comb"]}
        m = mk["games"].get(f"{r.home}|{r.away}")
        th, ta = tab.get(r.home, {}), tab.get(r.away, {})
        games.append({
            "id": f"{r.home}|{r.away}", "home": r.home, "away": r.away,
            "kickoff_utc": uk_to_utc(r.date, r.kick),
            "final": None if pd.isna(r.hg) else [int(r.hg), int(r.ag)],
            "probs": p, "xg": [round(float(r.xg_h), 2), round(float(r.xg_a), 2)],
            "market": [round(v / 100, 3) for v in m] if m else None,
            "features": {"elo_diff": round(float(r.elo_diff), 1), "xg_diff": round(float(r.xg_diff), 3),
                         "xg_total": round(float(r.xg_total), 3), "rest_diff": float(r.rest_diff)},
            "facts": {"league_position": {"home": th.get("pos"), "away": ta.get("pos")},
                      "points": {"home": th.get("pts"), "away": ta.get("pts")},
                      "last_results_oldest_first": {"home": "".join(th.get("form", [])[-5:]), "away": "".join(ta.get("form", [])[-5:])},
                      "newly_promoted": {"home": bool(r.home_promoted), "away": bool(r.away_promoted)},
                      "kickoff_uk": f"{r.date.date()} {r.kick}"},
        })
    lr = fitted["comb"]
    data = {"sport": "EPL", "season": season, "round": rnd, "market_source": mk["source"],
            "built_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "comb_model": {"features": MODELS["comb"], "coef": lr.coef_.round(5).tolist(), "intercept": lr.intercept_.round(5).tolist()},
            "backtest": {"season": "2025-26", "train_games": ntr, "test_games": nte, "rows": report},
            "games": games}
    json.dump(data, open("epl_data.json", "w"), indent=1, default=float)
    return data

if __name__ == "__main__":
    d = build(); print(d["round"], len(d["games"]))
    for g in d["games"]: print(g["id"], g["kickoff_utc"], g["probs"]["comb"], g["market"], g["xg"], g["facts"]["league_position"])
