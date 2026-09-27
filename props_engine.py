"""NFL anytime-touchdown model: player usage from nflverse play-by-play, weekly rosters and injury reports.

For every active QB/RB/WR/TE before each game, predict the chance they score a rushing or receiving TD.
Trained on 2016-2024, tested on 2025.
"""
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

DATA = Path(__file__).parent / "data"
RENAME = {"SD": "LAC", "STL": "LA", "OAK": "LV"}
POS = ["QB", "RB", "WR", "TE"]
HALF_LIFE = 4          # games: how fast older usage fades
TRAIN = range(2016, 2025); VALID = 2024; TEST = 2025

def player_games(season):
    cols = ["game_id", "season", "week", "season_type", "posteam", "rush_attempt", "pass_attempt", "sack",
            "rusher_player_id", "receiver_player_id", "td_player_id", "rush_touchdown", "pass_touchdown", "yardline_100"]
    p = pd.read_parquet(DATA / f"pbp_{season}.parquet", columns=cols)
    p = p[p.posteam.notna()]
    rz, gl = p.yardline_100 <= 20, p.yardline_100 <= 5
    ru = p[(p.rush_attempt == 1) & p.rusher_player_id.notna()].assign(player=lambda d: d.rusher_player_id, car=1, tgt=0)
    re_ = p[(p.pass_attempt == 1) & (p.sack != 1) & p.receiver_player_id.notna()].assign(player=lambda d: d.receiver_player_id, car=0, tgt=1)
    u = pd.concat([ru, re_])
    u["rz_car"] = u.car * (u.yardline_100 <= 20); u["rz_tgt"] = u.tgt * (u.yardline_100 <= 20); u["gl_car"] = u.car * (u.yardline_100 <= 5)
    g = u.groupby(["game_id", "season", "week", "posteam", "player"])[["car", "tgt", "rz_car", "rz_tgt", "gl_car"]].sum().reset_index()
    tds = p[((p.rush_touchdown == 1) | (p.pass_touchdown == 1)) & p.td_player_id.notna()].groupby(["game_id", "td_player_id"]).size()
    g["td"] = [int(tds.get((gid, pl), 0) > 0) for gid, pl in zip(g.game_id, g.player)]
    team = g.groupby(["game_id", "posteam"])[["rz_car", "rz_tgt"]].sum().rename(columns={"rz_car": "team_rz_car", "rz_tgt": "team_rz_tgt"})
    g = g.join(team, on=["game_id", "posteam"])
    g["posteam"] = g.posteam.replace(RENAME)
    return g

def usage_history(seasons):
    g = pd.concat([player_games(s) for s in seasons], ignore_index=True)
    g["key"] = g.season * 100 + g.week
    g = g.sort_values(["player", "key"])
    ew = lambda c: g.groupby("player")[c].transform(lambda s: s.ewm(halflife=HALF_LIFE).mean())
    for c in ["car", "tgt", "rz_car", "rz_tgt", "gl_car", "td", "team_rz_car", "team_rz_tgt"]:
        g["ew_" + c] = ew(c)
    g["n_games"] = g.groupby("player").cumcount() + 1
    return g

def candidates(seasons, games):
    rows = []
    for s in seasons:
        r = pd.read_parquet(DATA / f"roster_weekly_{s}.parquet", columns=["season", "week", "team", "position", "status", "gsis_id", "full_name", "game_type"])
        r = r[(r.status == "ACT") & r.position.isin(POS) & (r.game_type == "REG") & r.gsis_id.notna()]
        inj = pd.read_parquet(DATA / f"injuries_{s}.parquet", columns=["week", "gsis_id", "report_status"])
        out = set(zip(inj[inj.report_status.isin(["Out", "Doubtful"])].week, inj[inj.report_status.isin(["Out", "Doubtful"])].gsis_id))
        q = inj[inj.report_status == "Questionable"]; ques = set(zip(q.week, q.gsis_id))
        r = r[[(w, p) not in out for w, p in zip(r.week, r.gsis_id)]].copy()
        r["questionable"] = [(w, p) in ques for w, p in zip(r.week, r.gsis_id)]
        rows.append(r)
    c = pd.concat(rows, ignore_index=True).rename(columns={"gsis_id": "player"})
    c["team"] = c.team.replace(RENAME)
    c = c.drop_duplicates(["season", "week", "player"])
    # attach the game and the market's implied team points
    gm = games[games.game_type == "REG"]
    home = gm.assign(team=gm.home_team, opp=gm.away_team, is_home=1, pts=(gm.total_line + gm.spread_line) / 2, qb_id=gm.home_qb_id)
    away = gm.assign(team=gm.away_team, opp=gm.home_team, is_home=0, pts=(gm.total_line - gm.spread_line) / 2, qb_id=gm.away_qb_id)
    side = pd.concat([home, away])[["season", "week", "team", "opp", "is_home", "pts", "game_id", "gameday", "gametime", "qb_id"]]
    return c.merge(side, on=["season", "week", "team"], how="inner")

def add_features(c, hist):
    c = c.copy(); c["key"] = c.season * 100 + c.week
    h = hist[["player", "key"] + [x for x in hist.columns if x.startswith("ew_")] + ["n_games"]].rename(columns={"key": "hkey"}).sort_values("hkey")
    c = c.sort_values("key")
    c = pd.merge_asof(c, h, left_on="key", right_on="hkey", by="player", allow_exact_matches=False, direction="backward")
    c = c[c.hkey.notna() & (c.key - c.hkey < 200)]          # used within roughly the last two seasons
    c["rz_car_share"] = c.ew_rz_car / c.ew_team_rz_car.replace(0, np.nan)
    c["rz_tgt_share"] = c.ew_rz_tgt / c.ew_team_rz_tgt.replace(0, np.nan)
    c[["rz_car_share", "rz_tgt_share"]] = c[["rz_car_share", "rz_tgt_share"]].fillna(0)
    c["pts_x_car"] = c.pts * c.rz_car_share; c["pts_x_tgt"] = c.pts * c.rz_tgt_share
    c["n_games"] = c.n_games.clip(upper=16)
    for p in POS: c["is_" + p] = (c.position == p).astype(float)
    # only the team's listed starting quarterback is a candidate
    c = c[(c.position != "QB") | (c.player == c.qb_id)]
    # role check: share of this team's games so far this season in which the player touched the ball
    played = hist.groupby(["season", "posteam", "player"]).week.apply(sorted).to_dict()
    team_weeks = hist.groupby(["season", "posteam"]).week.apply(lambda w: sorted(set(w))).to_dict()
    def share(s, t, pl, w):
        tw = [x for x in team_weeks.get((s, t), []) if x < w]
        if not tw: return np.nan
        return sum(1 for x in played.get((s, t, pl), []) if x < w) / len(tw)
    c["played_share"] = [share(s, t, pl, w) for s, t, pl, w in zip(c.season, c.team, c.player, c.week)]
    c["new_season"] = c.played_share.isna().astype(float)
    c["played_share"] = c.played_share.fillna(0.5)
    return c

FEATS = ["ew_car", "ew_tgt", "ew_rz_car", "ew_rz_tgt", "ew_gl_car", "ew_td", "rz_car_share", "rz_tgt_share",
         "pts", "pts_x_car", "pts_x_tgt", "n_games", "is_QB", "is_RB", "is_WR", "is_TE", "played_share", "new_season"]

def label(c, hist):
    scored = set(zip(hist.game_id, hist.player, hist.td))
    tdset = {(g, p) for g, p, t in scored if t}
    c["y"] = [int((g, p) in tdset) for g, p in zip(c.game_id, c.player)]
    return c

def scores(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {"brier": float(np.mean((p - y) ** 2)), "logloss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))}

def main():
    games = pd.read_csv(DATA / "games.csv")
    games["home_team"] = games.home_team.replace(RENAME); games["away_team"] = games.away_team.replace(RENAME)
    hist = usage_history(range(2014, 2027))
    c = label(add_features(candidates(range(2016, 2027), games), hist), hist)
    c = c.dropna(subset=["pts"])
    done = c[c.season < 2026]
    # choose the model on a validation season, then refit on all training seasons
    tr, va = done[done.season.isin(range(2016, VALID))], done[done.season == VALID]
    cands = {"logistic": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0)),
             "boosted": HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, l2_regularization=1.0)}
    val = {}
    for name, m in cands.items():
        m.fit(tr[FEATS], tr.y); val[name] = scores(m.predict_proba(va[FEATS])[:, 1], va.y.values)
    best = min(val, key=lambda k: val[k]["logloss"])
    tr, te = done[done.season.isin(TRAIN)], done[done.season == TEST].copy()
    model = cands[best].fit(tr[FEATS], tr.y)
    te["p"] = model.predict_proba(te[FEATS])[:, 1]
    pos_rate = tr.groupby("position").y.mean(); base = te.position.map(pos_rate).values
    naive = np.clip(te.ew_td.values, 0.01, 0.9)
    report = {"model": best, "validation": val, "train_rows": len(tr), "test_rows": len(te), "test_rate": float(te.y.mean()),
              "test": scores(te.p.values, te.y.values), "baseline_position": scores(base, te.y.values), "baseline_recent_td_rate": scores(naive, te.y.values)}
    # calibration and "top picks each week" hit rates on the test season
    te["bin"] = pd.cut(te.p, [0, .1, .2, .3, .4, .5, 1])
    report["calibration"] = [{"range": str(k), "n": int(len(v)), "predicted": float(v.p.mean()), "actual": float(v.y.mean())} for k, v in te.groupby("bin", observed=True)]
    top = te.sort_values("p", ascending=False).groupby("week").head(10)
    report["top10_weekly_hit"] = float(top.y.mean()); report["top10_weekly_pred"] = float(top.p.mean())
    return c, model, report

if __name__ == "__main__":
    c, model, rep = main()
    import json; print(json.dumps(rep, indent=1))
