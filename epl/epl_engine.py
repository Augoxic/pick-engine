"""EPL pick engine: Elo, a time-weighted Poisson goals model, and a combined win/draw/loss model."""
import json, math, datetime as dt, warnings
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.linear_model import PoissonRegressor, LogisticRegression
warnings.filterwarnings("ignore")

HERE = Path(__file__).parent
TRAIN = [f"{y}-{str(y+1)[2:]}" for y in range(2012, 2025)]   # 2012-13 .. 2024-25
TEST = "2025-26"
HALF_LIFE = 240          # days: how fast old matches fade in the goals model
WINDOW = 3 * 365         # days of history the goals model looks at
OF_NAMES = {"AFC Bournemouth":"Bournemouth","Arsenal FC":"Arsenal","Aston Villa FC":"Aston Villa","Brentford FC":"Brentford",
    "Brighton & Hove Albion FC":"Brighton","Chelsea FC":"Chelsea","Coventry City FC":"Coventry","Crystal Palace FC":"Crystal Palace",
    "Everton FC":"Everton","Fulham FC":"Fulham","Hull City AFC":"Hull","Ipswich Town FC":"Ipswich","Leeds United FC":"Leeds",
    "Liverpool FC":"Liverpool","Manchester City FC":"Man City","Manchester United FC":"Man United","Newcastle United FC":"Newcastle",
    "Nottingham Forest FC":"Nott'm Forest","Sunderland AFC":"Sunderland","Tottenham Hotspur FC":"Tottenham"}

def load_matches():
    import premier_league_data as pl
    r = pl.load_results()
    hist = pd.DataFrame({"season": r.season, "date": pd.to_datetime(r.date), "home": r.home_team, "away": r.away_team,
                         "hg": r.fthg.astype(float), "ag": r.ftag.astype(float), "kick": "15:00"})
    cur = []
    for m in json.load(open(HERE / "en1_2627.json"))["matches"]:
        sc = m.get("score")
        ft = sc if isinstance(sc, list) and len(sc) == 2 else (sc or {}).get("ft") if isinstance(sc, dict) else None
        cur.append({"season": "2026-27", "date": pd.Timestamp(m["date"]), "home": OF_NAMES[m["team1"]], "away": OF_NAMES[m["team2"]],
                    "hg": ft[0] if ft else np.nan, "ag": ft[1] if ft else np.nan, "kick": m.get("time", "15:00"),
                    "round": m["round"]})
    df = pd.concat([hist, pd.DataFrame(cur)], ignore_index=True).sort_values(["date", "home"]).reset_index(drop=True)
    first = {}
    for s in sorted(df.season.unique()):
        teams = set(df[df.season == s].home)
        prev = set(df[df.season == first.get("_prev")].home) if first.get("_prev") else teams
        first[s] = teams - prev; first["_prev"] = s
    df["home_promoted"] = [h in first[s] for h, s in zip(df.home, df.season)]
    df["away_promoted"] = [a in first[s] for a, s in zip(df.away, df.season)]
    return df

# ---------------- Elo ----------------
def run_elo(df, k=20, hfa=60, mean=1500):
    elo, pre, season = {}, [], None
    for m in df.itertuples():
        if m.season != season:
            if season is not None:
                last = df[df.season == season]
                teams_now = set(df[df.season == m.season].home)
                gone = [t for t in set(last.home) if t not in teams_now]
                base = np.mean([elo[t] for t in gone]) if gone else mean
                for t in teams_now:
                    if t not in set(last.home): elo[t] = base          # promoted: start where relegated teams ended
                elo = {t: v + (mean - v) * 0.1 for t, v in elo.items()}
            season = m.season
        h, a = elo.get(m.home, mean), elo.get(m.away, mean)
        pre.append(h - a)
        if np.isnan(m.hg): continue
        exp = 1 / (1 + 10 ** (-(h + hfa - a) / 400))
        res = 1.0 if m.hg > m.ag else 0.0 if m.hg < m.ag else 0.5
        gd = abs(m.hg - m.ag); mult = 1 if gd <= 1 else 1.5 if gd == 2 else (11 + gd) / 8
        d = k * mult * (res - exp); elo[m.home] = h + d; elo[m.away] = a - d
    df = df.copy(); df["elo_diff"] = pre
    return df, elo

# ---------------- time-weighted Poisson goals model ----------------
def fit_goals(hist, asof):
    h = hist[(hist.date < asof) & (hist.date >= asof - pd.Timedelta(days=WINDOW))].dropna(subset=["hg"])
    teams = sorted(set(h.home) | set(h.away)); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
    w = np.exp(-math.log(2) * (asof - h.date).dt.days.values / HALF_LIFE)
    rows = len(h); X = np.zeros((2 * rows, 2 * n + 3)); y = np.r_[h.hg.values, h.ag.values]
    for r, (ht, at, hp, ap) in enumerate(zip(h.home, h.away, h.home_promoted, h.away_promoted)):
        X[r, ix[ht]] = 1; X[r, n + ix[at]] = 1; X[r, 2 * n] = 1; X[r, 2 * n + 1] = hp; X[r, 2 * n + 2] = ap
        X[rows + r, ix[at]] = 1; X[rows + r, n + ix[ht]] = 1; X[rows + r, 2 * n + 1] = ap; X[rows + r, 2 * n + 2] = hp
    m = PoissonRegressor(alpha=1e-3, max_iter=300).fit(X, y, sample_weight=np.r_[w, w])
    return {"ix": ix, "n": n, "coef": m.coef_, "icpt": m.intercept_}

def expect(model, home, away, hp, ap, neutral=False):
    ix, n, c, b = model["ix"], model["n"], model["coef"], model["icpt"]
    def rate(att, dfn, is_home, att_p, def_p):
        v = b + (c[ix[att]] if att in ix else 0) + (c[n + ix[dfn]] if dfn in ix else 0)
        return math.exp(v + (c[2 * n] if is_home else 0) + c[2 * n + 1] * att_p + c[2 * n + 2] * def_p)
    return rate(home, away, not neutral, hp, ap), rate(away, home, False, ap, hp)

def poisson_probs(lh, la, cap=10):
    ph = [math.exp(-lh) * lh ** i / math.factorial(i) for i in range(cap)]
    pa = [math.exp(-la) * la ** i / math.factorial(i) for i in range(cap)]
    M = np.outer(ph, pa)
    return float(np.tril(M, -1).sum()), float(np.trace(M)), float(np.triu(M, 1).sum())

def add_goal_features(df):
    df = df.copy(); df["xg_h"] = np.nan; df["xg_a"] = np.nan
    df["week"] = df.date.dt.to_period("W-MON")
    for wk, idx in df[df.season.isin(TRAIN + [TEST, "2026-27"])].groupby("week").groups.items():
        asof = df.loc[idx, "date"].min()
        model = fit_goals(df, asof)
        for i in idx:
            r = df.loc[i]; df.loc[i, ["xg_h", "xg_a"]] = expect(model, r.home, r.away, r.home_promoted, r.away_promoted)
    last_match = {}; rest_h, rest_a = [], []
    for r in df.itertuples():
        rest_h.append((r.date - last_match.get(r.home, r.date - pd.Timedelta(days=7))).days)
        rest_a.append((r.date - last_match.get(r.away, r.date - pd.Timedelta(days=7))).days)
        last_match[r.home] = r.date; last_match[r.away] = r.date
    df["rest_diff"] = np.clip(np.array(rest_h) - np.array(rest_a), -7, 7)
    df["xg_diff"] = df.xg_h - df.xg_a; df["xg_total"] = df.xg_h + df.xg_a
    df["outcome"] = np.select([df.hg > df.ag, df.hg == df.ag], [0, 1], 2)   # 0 home, 1 draw, 2 away
    return df

MODELS = {"elo": ["elo_diff"], "comb": ["elo_diff", "xg_diff", "xg_total", "rest_diff"]}

def devig(o):
    inv = 1 / o; return inv / inv.sum(axis=1, keepdims=True)

def scores(P, y):
    Y = np.eye(3)[y]
    return {"acc": float(np.mean(P.argmax(1) == y)), "brier": float(np.mean(((P - Y) ** 2).sum(1))),
            "logloss": float(-np.mean(np.log(np.clip(P[np.arange(len(y)), y], 1e-9, 1))))}

def main():
    df = load_matches(); df, current_elo = run_elo(df); df = add_goal_features(df)
    done = df[df.hg.notna()]
    tr, te = done[done.season.isin(TRAIN)], done[done.season == TEST].copy()
    fitted = {}
    for name, cols in MODELS.items():
        fitted[name] = LogisticRegression(C=10, max_iter=1000).fit(tr[cols].values, tr.outcome.values)
    def probs(name, d):
        if name == "goals": return np.array([poisson_probs(a, b) for a, b in zip(d.xg_h, d.xg_a)])
        return fitted[name].predict_proba(d[MODELS[name]].values)
    import premier_league_data as pl
    odds = pl.load_results_with_odds(TEST)
    odds = odds.assign(date=pd.to_datetime(odds.date))[["home_team", "away_team", "market_avg_1x2_home_close", "market_avg_1x2_draw_close", "market_avg_1x2_away_close"]]
    te = te.merge(odds, left_on=["home", "away"], right_on=["home_team", "away_team"], how="left")
    O = te[["market_avg_1x2_home_close", "market_avg_1x2_draw_close", "market_avg_1x2_away_close"]].values
    y = te.outcome.values; report = [dict(name="market", **scores(devig(O), y))]
    for name in ["elo", "goals", "comb"]:
        P = probs(name, te); row = dict(name=name, **scores(P, y))
        edge = P - devig(O); pick = edge.argmax(1); k = edge.max(1) >= 0.03      # bet the outcome the model likes most, if 3+ pts over market
        payout = np.where(pick == y, O[np.arange(len(y)), pick] - 1, -1.0)[k]
        row.update(bets=int(k.sum()), roi=float(payout.mean()) if k.any() else None)
        report.append(row)
    report.append(dict(name="home", acc=float(np.mean(y == 0)), brier=None, logloss=None))
    return df, fitted, probs, report, len(tr), len(te), current_elo

if __name__ == "__main__":
    df, fitted, probs, report, ntr, nte, _ = main()
    print(ntr, nte)
    for r in report: print(r)
