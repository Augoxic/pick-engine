"""NFL pick engine: Elo + efficiency + combined model, backtest, and weekly predictions."""
import json, math, sys
import numpy as np, pandas as pd
from pathlib import Path

DATA = Path(__file__).parent / "data"
TRAIN_SEASONS = range(2014, 2025)   # fit weights on these
TEST_SEASON = 2025                  # never seen in training
PRIOR_GAMES = 4                     # how fast current-season stats override last season
REGRESS = 0.5                       # how far last season's stats shrink toward average

# ---------------- Elo ----------------
def run_elo(games, k=20, hfa=48, revert=1/3, mean=1505):
    elo, pre, last_season = {}, [], None
    for g in games.itertuples():
        if g.season != last_season:
            elo = {t: v + (mean - v) * revert for t, v in elo.items()}
            last_season = g.season
        h, a = elo.get(g.home_team, mean), elo.get(g.away_team, mean)
        adv = 0 if g.location == "Neutral" else hfa
        pre.append((h - a) / 25.0)           # Elo gap in points, no home field
        if pd.isna(g.result):
            continue
        diff = h + adv - a
        exp_h = 1 / (1 + 10 ** (-diff / 400))
        mov = g.result
        actual = 1.0 if mov > 0 else 0.0 if mov < 0 else 0.5
        wdiff = diff if mov > 0 else -diff
        mult = math.log(abs(mov) + 1) * 2.2 / (wdiff * 0.001 + 2.2)
        delta = k * mult * (actual - exp_h)
        elo[g.home_team] = h + delta
        elo[g.away_team] = a - delta
    games = games.copy(); games["elo_pts"] = pre
    return games, elo

# ---------------- per-game team stats from play-by-play ----------------
def team_game_stats(season):
    cols = ["game_id","week","season_type","posteam","defteam","play_type","epa","success",
            "penalty","penalty_team","penalty_yards"]
    d = pd.read_parquet(DATA / f"pbp_{season}.parquet", columns=cols)
    scrim = d[d.play_type.isin(["pass","run"]) & d.epa.notna()]
    off = scrim.groupby(["game_id","posteam"]).agg(off_epa=("epa","mean"), off_sr=("success","mean"), plays=("epa","size"))
    dfn = scrim.groupby(["game_id","defteam"]).agg(def_epa=("epa","mean"), def_sr=("success","mean"))
    off.index.names = dfn.index.names = ["game_id","team"]
    st = d[d.play_type.isin(["kickoff","punt","field_goal","extra_point"]) & d.epa.notna()]
    st_for = st.groupby(["game_id","posteam"]).epa.sum(); st_for.index.names = ["game_id","team"]
    st_ag = st.groupby(["game_id","defteam"]).epa.sum(); st_ag.index.names = ["game_id","team"]
    pen = d[d.penalty == 1].groupby(["game_id","penalty_team"]).penalty_yards.sum(); pen.index.names = ["game_id","team"]
    s = off.join(dfn, how="outer")
    s["st_epa"] = st_for.reindex(s.index).fillna(0) - st_ag.reindex(s.index).fillna(0)
    s["pen_yds"] = pen.reindex(s.index).fillna(0)
    s = s.reset_index()
    wk = d.drop_duplicates("game_id").set_index("game_id").week
    s["week"] = s.game_id.map(wk); s["season"] = season
    return s

STATS = ["off_epa","def_epa","off_sr","def_sr","st_epa","pen_yds"]

def pregame_ratings(seasons):
    """For every (season, week, team): stats known BEFORE that week, blended with last season."""
    out, prior = [], {}
    for season in seasons:
        s = team_game_stats(season).sort_values("week")
        league = s[STATS].mean()
        weeks = sorted(s.week.unique()) + [s.week.max() + 1]
        teams = s.team.unique()
        for w in weeks:
            past = s[s.week < w]
            for t in teams:
                tp = past[past.team == t]; n = len(tp)
                cur = tp[STATS].mean() if n else league
                pr = prior.get(t, league) * (1 - REGRESS) + league * REGRESS
                wt = n / (n + PRIOR_GAMES)
                row = (cur * wt + pr * (1 - wt)).to_dict()
                row.update(season=season, week=w, team=t)
                out.append(row)
        final = s.groupby("team")[STATS].mean()
        prior = {t: final.loc[t] for t in final.index}
    return pd.DataFrame(out)

# ---------------- assemble model table ----------------
FEATURES = {
    "elo":          ["elo_pts", "home"],
    "eff":          ["elo_pts", "net_epa", "home"],
    "comb":         ["elo_pts", "net_epa", "net_sr", "st", "pen", "rest", "home"],
}
LABELS = {"elo_pts":"Elo","net_epa":"Efficiency","net_sr":"Success rate","st":"Special teams",
          "pen":"Penalties","rest":"Rest","home":"Home field"}

def build_table():
    g = pd.read_csv(DATA / "games.csv")
    rename = {"SD": "LAC", "STL": "LA", "OAK": "LV"}   # relocated franchises keep their history
    g["home_team"] = g.home_team.replace(rename); g["away_team"] = g.away_team.replace(rename)
    g = g[g.season >= 1999].sort_values(["season","week","gameday","gametime"]).reset_index(drop=True)
    g, current_elo = run_elo(g)
    seasons = sorted(int(p.stem.split("_")[1]) for p in DATA.glob("pbp_*.parquet"))
    r = pregame_ratings(seasons).set_index(["season","week","team"])
    g = g[g.season >= min(seasons)].copy()
    def pull(side):
        idx = list(zip(g.season, g.week, g[side + "_team"]))
        return r.reindex(idx).reset_index(drop=True)
    H, A = pull("home"), pull("away")
    g = g.reset_index(drop=True)
    g["net_epa"] = (H.off_epa - H.def_epa) - (A.off_epa - A.def_epa)
    g["net_sr"]  = (H.off_sr - H.def_sr) - (A.off_sr - A.def_sr)
    g["st"]      = H.st_epa - A.st_epa
    g["pen"]     = A.pen_yds - H.pen_yds          # + means the away team commits more
    g["rest"]    = (g.home_rest - g.away_rest).clip(-7, 7)
    g["home"]    = (g.location != "Neutral").astype(float)
    return g, current_elo

def fit(train, cols):
    X = np.column_stack([train[c].values for c in cols]); y = train.result.values
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    sigma = np.std(y - X @ coef)
    return coef, sigma

def predict(df, cols, coef):
    return np.column_stack([df[c].values for c in cols]) @ coef

def phi(x): return 0.5 * (1 + np.vectorize(math.erf)(x / math.sqrt(2)))

def devig(ml_home, ml_away):
    def imp(ml):
        ml = np.asarray(ml, float)
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(ml < 0, -ml / (-ml + 100), 100 / (ml + 100))
    h, a = imp(ml_home), imp(ml_away); return h / (h + a)

def main():
    g, current_elo = build_table()
    done = g[g.result.notna()]
    train = done[done.season.isin(TRAIN_SEASONS)].dropna(subset=sum(FEATURES.values(), []))
    test = done[done.season == TEST_SEASON].dropna(subset=sum(FEATURES.values(), []))
    models, report = {}, []
    for name, cols in FEATURES.items():
        coef, sigma = fit(train, cols); models[name] = (cols, coef, sigma)
        m = predict(test, cols, coef); p = phi(m / sigma)
        win = np.mean((m > 0) == (test.result > 0))
        brier = np.mean((p - (test.result > 0)) ** 2)
        ats_res = test.result - test.spread_line
        mask = (ats_res != 0) & (m != test.spread_line)
        ats_w = int(np.sum(((m > test.spread_line) == (ats_res > 0))[mask])); ats_n = int(mask.sum())
        report.append(dict(name=name, win=win, brier=brier, ats_w=ats_w, ats_l=ats_n - ats_w))
    vp = devig(test.home_moneyline.values, test.away_moneyline.values)
    report.insert(0, dict(name="vegas", win=np.mean((vp > .5) == (test.result > 0)),
                          brier=np.mean((vp - (test.result > 0)) ** 2), ats_w=None, ats_l=None))
    report.append(dict(name="home", win=np.mean(test.result > 0), brier=0.25, ats_w=None, ats_l=None))
    # ATS by size of disagreement with the line (combined model), test season
    cols, coef, sigma = models["comb"]
    m = predict(test, cols, coef); edge = np.abs(m - test.spread_line); res = test.result - test.spread_line
    buckets = []
    for lo, hi in [(0,1.5),(1.5,3),(3,5),(5,99)]:
        k = (edge >= lo) & (edge < hi) & (res != 0)
        w = int(np.sum(((m > test.spread_line) == (res > 0))[k])); buckets.append(dict(lo=lo, hi=hi, w=w, l=int(k.sum()) - w))
    return g, models, report, buckets, len(train), len(test)

if __name__ == "__main__":
    g, models, report, buckets, ntr, nte = main()
    print("train games", ntr, "test games", nte)
    for r in report: print(r)
    for b in buckets: print(b)
    for n,(c,coef,s) in models.items(): print(n, dict(zip(c, np.round(coef,3))), round(s,2))
