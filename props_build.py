"""Build anytime-TD picks for the current NFL week (props_data.json)."""
import json, datetime as dt
import numpy as np, pandas as pd
from props_engine import main, FEATS

def fair_american(p):
    return int(round(-100 * p / (1 - p))) if p >= 0.5 else int(round(100 * (1 - p) / p))

def build(season=2026, week=None):
    c, model, rep = main()
    wk = c[c.season == season]
    week = week or int(json.load(open("sheet_data.json"))["week"])
    sheet = json.load(open("sheet_data.json"))
    open_ids = {g["id"] for g in sheet["games"] if not g["final"]}
    wk = wk[(wk.week == week) & wk.game_id.isin(open_ids)].copy()
    wk["p"] = model.predict_proba(wk[FEATS])[:, 1]
    players = []
    for r in wk.sort_values("p", ascending=False).itertuples():
        players.append({"game_id": r.game_id, "team": r.team, "opp": r.opp, "name": r.full_name, "pos": r.position,
                        "p": round(float(r.p), 3), "fair": fair_american(float(r.p)), "questionable": bool(r.questionable),
                        "rz_car_share": round(float(r.rz_car_share), 2), "rz_tgt_share": round(float(r.rz_tgt_share), 2),
                        "team_pts": round(float(r.pts), 1), "recent_td_rate": round(float(r.ew_td), 2)})
    out = {"season": season, "week": week, "built_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
           "backtest": rep, "players": players}
    json.dump(out, open("props_data.json", "w"), indent=1, default=float)
    return out

if __name__ == "__main__":
    d = build(); print(d["backtest"]["model"], d["backtest"]["validation"], len(d["players"]))
    for p in d["players"][:25]: print(p["name"], p["team"], p["pos"], p["p"], p["fair"], p["questionable"], p["team_pts"])
