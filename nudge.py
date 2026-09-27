"""Ask four Claude setups to nudge this week's predictions, and lock the results before kickoff.

    export ANTHROPIC_API_KEY=sk-ant-...
    python nudge.py nfl          # or: python nudge.py epl
    python nudge.py all

Nudges are saved in nudges/<sport>/<slate>.json. A game's nudge is written once, only
before kickoff, and never overwritten, so the sheet can be graded honestly afterwards.
"""
import json, os, re, sys, time, datetime as dt, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).parent
API = "https://api.anthropic.com/v1/messages"

# key, model id, prompt version, extra request settings
SETUPS = [
    ("haiku_v4", "claude-haiku-4-5-20251001", "v4", {"temperature": 0}),   # no thinking
    ("haiku",    "claude-haiku-4-5-20251001", "v5", {"temperature": 0}),   # no thinking
    ("sonnet",   "claude-sonnet-5",           "v5", {}),                   # adaptive thinking on by default, effort high
    ("opus",     "claude-opus-5-5",           "v5", {}),                   # adaptive thinking always on, effort medium
]

NFL_TEAMS = {"ARI":"Cardinals","ATL":"Falcons","BAL":"Ravens","BUF":"Bills","CAR":"Panthers","CHI":"Bears","CIN":"Bengals","CLE":"Browns",
    "DAL":"Cowboys","DEN":"Broncos","DET":"Lions","GB":"Packers","HOU":"Texans","IND":"Colts","JAX":"Jaguars","KC":"Chiefs","LA":"Rams",
    "LAC":"Chargers","LV":"Raiders","MIA":"Dolphins","MIN":"Vikings","NE":"Patriots","NO":"Saints","NYG":"Giants","NYJ":"Jets",
    "PHI":"Eagles","PIT":"Steelers","SEA":"Seahawks","SF":"49ers","TB":"Buccaneers","TEN":"Titans","WAS":"Commanders"}

REPLY = ('Reply with ONLY a JSON array, no other text: [{"id": "<id>", "nudge": <number, positive moves toward the home side>, '
         '"reason": "<one or two plain sentences citing the fact>"}] with one entry per game.')

SPORTS = {
    "nfl": {
        "data": ROOT / "sheet_data.json", "clamp": 7,
        "slate": lambda d: f"{d['season']}-week{d['week']:02d}",
        "payload": lambda g: {"id": g["id"], "away": NFL_TEAMS.get(g["away"], g["away"]), "home": NFL_TEAMS.get(g["home"], g["home"]),
                              "math_margin_home": g["preds"]["comb"]["margin"], "math_breakdown_points_toward_home": g["breakdown"], "facts": g["facts"]},
        "prompts": {
            "v4": """You review NFL game predictions. A statistical model predicts each game's margin from the home team's view (positive = home wins by that many). You are not shown betting lines.

For each game, adjust the model's margin by between -7 and +7 points based on the facts provided, and explain why.

Games (JSON): {games}

""" + REPLY,
            "v5": """You review NFL game predictions. A statistical model predicts each game's margin from the home team's view (positive = home wins by that many). It already accounts for: Elo team strength, offensive and defensive efficiency (EPA per play), success rate, special teams, penalties, days of rest, and home field. You are not shown betting lines and must not guess them.

For each game, nudge the model's margin by between -7 and +7 points ONLY for things the model cannot see in the facts provided. The main one is a starting quarterback change (compare starting_qb with qb_last_game): a backup replacing an established starter is usually worth several points; a starter returning or an equal swap is worth little. Extreme wind or cold can also matter. Do not re-count rest, home field or anything in the breakdown. Most games should get a nudge of 0. Luck and small samples are not reasons to nudge.

Games (JSON): {games}

""" + REPLY,
        },
    },
    "epl": {
        "data": ROOT / "epl" / "epl_data.json", "clamp": 1,
        "slate": lambda d: f"{d['season']}-{d['round'].replace(' ', '').lower()}",
        "payload": lambda g: {"id": g["id"], "home": g["home"], "away": g["away"], "expected_goals": {"home": g["xg"][0], "away": g["xg"][1]},
                              "model_probs_home_draw_away": g["probs"]["comb"], "facts": g["facts"]},
        "prompts": {
            "v4": """You review Premier League match predictions. A statistical model gives each match an expected goal difference from the home side's view and win/draw/loss probabilities. You are not shown betting odds.

For each match, adjust the expected goal difference by between -1.0 and +1.0 goals based on the facts provided, and explain why.

Matches (JSON): {games}

""" + REPLY,
            "v5": """You review Premier League match predictions. A statistical model gives each match an expected goal difference from the home side's view and win/draw/loss probabilities. It already accounts for: Elo club strength (including a penalty for newly promoted clubs), a time-weighted goals model of each club's attack and defence, home advantage and days of rest between league matches. You are not shown betting odds and must not guess them.

For each match, nudge the expected goal difference by between -1.0 and +1.0 goals ONLY for things the model cannot see in the facts provided. Early-season league position and recent results are small samples: do not nudge for form or table position alone. Most matches should get a nudge of 0. If you have no real information beyond the facts, return 0.

Matches (JSON): {games}

""" + REPLY,
        },
    },
}

def call(model, prompt, extra, key, tries=3):
    body = {"model": model, "max_tokens": 16000, "messages": [{"role": "user", "content": prompt}], **extra}
    req = urllib.request.Request(API, data=json.dumps(body).encode(), method="POST",
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                out = json.load(r)
            text = "".join(b.get("text", "") for b in out.get("content", []) if b.get("type") == "text")
            return parse(text)
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:300]
            if e.code in (429, 500, 529) and attempt < tries - 1:
                time.sleep(10 * (attempt + 1)); continue
            raise SystemExit(f"{model}: HTTP {e.code} {msg}")

def parse(text):
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("["), text.rfind("]")
    return json.loads(text[start:end + 1]) if start >= 0 else []

def run(sport, key):
    cfg = SPORTS[sport]; data = json.loads(cfg["data"].read_text())
    path = ROOT / "nudges" / sport / f"{cfg['slate'](data)}.json"; path.parent.mkdir(parents=True, exist_ok=True)
    saved = json.loads(path.read_text()) if path.exists() else {}
    now = dt.datetime.now(dt.timezone.utc)
    for k, model, version, extra in SETUPS:
        mine = saved.setdefault(k, {})
        todo = [g for g in data["games"] if g["id"] not in mine and dt.datetime.fromisoformat(g["kickoff_utc"].replace("Z", "+00:00")) > now]
        if not todo:
            print(f"{sport} {k}: nothing to do"); continue
        prompt = cfg["prompts"][version].replace("{games}", json.dumps([cfg["payload"](g) for g in todo]))
        print(f"{sport} {k}: asking {model} (prompt {version}) about {len(todo)} games…")
        added = 0
        for r in call(model, prompt, extra, key):
            if r.get("id") in {g["id"] for g in todo} and isinstance(r.get("nudge"), (int, float)):
                c = cfg["clamp"]
                mine[r["id"]] = {"nudge": round(max(-c, min(c, float(r["nudge"]))), 2), "reason": str(r.get("reason", ""))[:400],
                                 "model": model, "prompt": version, "saved_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
                added += 1
        path.write_text(json.dumps(saved, indent=1))   # save after every model so nothing is lost
        print(f"  saved {added}")
    return path

def load_env():
    """Read KEY=value lines from a local .env file (kept out of git) without extra packages."""
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"'))

if __name__ == "__main__":
    load_env()
    key = os.environ.get("ANTHROPIC_API_KEY") or sys.exit("Set ANTHROPIC_API_KEY first.")
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for s in (SPORTS if which == "all" else [which]):
        print("wrote", run(s, key))
