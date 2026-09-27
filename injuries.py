"""Injury report and expected starters for each NFL game, from nflverse injury reports and depth charts.

Used by build.py (facts for the page and the Claude nudges) so nobody has to hunt for who is out.
"""
import pandas as pd
from pathlib import Path

DATA = Path(__file__).parent / "data"
RENAME = {"SD": "LAC", "STL": "LA", "OAK": "LV"}
SKILL = {"QB", "RB", "WR", "TE"}
ORDER = {"Out": 0, "Doubtful": 1, "Questionable": 2}

def load(season, week):
    inj = pd.read_parquet(DATA / f"injuries_{season}.parquet")
    inj = inj[(inj.week == week) & inj.report_status.isin(ORDER)].copy()
    inj["team"] = inj.team.replace(RENAME)
    dc = pd.read_parquet(DATA / f"depth_charts_{season}.parquet")
    dc = dc[dc.dt == dc.groupby("team").dt.transform("max")].copy()      # latest depth chart per team
    dc["team"] = dc.team.replace(RENAME)
    return inj, dc

def team_report(team, listed_qb, inj, dc):
    """Returns (expected starting QB, note or None, list of notable injuries)."""
    ti, td = inj[inj.team == team], dc[dc.team == team]
    status = dict(zip(ti.full_name, ti.report_status))
    starters = set(td[td.pos_rank == 1].player_name)
    rank = {(r.player_name): r.pos_rank for r in td.itertuples()}
    # starting quarterback: the schedule's listed QB, unless the injury report rules him out
    qb, note = listed_qb, None
    if listed_qb and status.get(listed_qb) in ("Out", "Doubtful"):
        backups = td[(td.pos_abb == "QB")].sort_values("pos_rank").player_name.tolist()
        nxt = next((q for q in backups if q != listed_qb and status.get(q) not in ("Out", "Doubtful")), None)
        qb = nxt or listed_qb
        note = f"{listed_qb} is {status[listed_qb]}; {nxt or 'backup'} expected to start"
    notable = []
    for r in ti.itertuples():
        key = r.position in SKILL and rank.get(r.full_name, 9) <= (3 if r.position == "WR" else 2)
        if r.full_name in starters or key:
            role = "starter" if r.full_name in starters else "key reserve"
            notable.append({"name": r.full_name, "pos": r.position, "status": r.report_status,
                            "injury": None if pd.isna(r.report_primary_injury) else r.report_primary_injury, "role": role})
    notable.sort(key=lambda x: (ORDER[x["status"]], x["pos"] not in SKILL, x["name"]))
    return qb, note, notable

def game_reports(season, week, games):
    inj, dc = load(season, week)
    out = {}
    for r in games.itertuples():
        a = team_report(r.away_team, r.away_qb_name, inj, dc)
        h = team_report(r.home_team, r.home_qb_name, inj, dc)
        out[r.game_id] = {"qb": {"away": a[0], "home": h[0]}, "qb_note": {"away": a[1], "home": h[1]},
                          "injuries": {"away": a[2], "home": h[2]}}
    return out

if __name__ == "__main__":
    g = pd.read_csv(DATA / "games.csv"); g = g[(g.season == 2026) & (g.week == 3)]
    for gid, rep in game_reports(2026, 3, g).items():
        print(gid, rep["qb"], rep["qb_note"])
        for side in ("away", "home"):
            for x in rep["injuries"][side]: print("   ", side, x)
