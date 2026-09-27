"""Render every sport's sheet data, plus any saved Claude nudges, into one site with a tab per sport."""
import json, sys
from pathlib import Path
from nudge import SPORTS
root = Path(__file__).parent

def with_nudges(sport):
    cfg = SPORTS[sport]; data = json.loads(cfg["data"].read_text())
    f = root / "nudges" / sport / f"{cfg['slate'](data)}.json"
    data["nudges"] = json.loads(f.read_text()) if f.exists() else {}
    return json.dumps(data)

html = (root / "site_template.html").read_text()
html = html.replace("__NFL__", with_nudges("nfl")).replace("__EPL__", with_nudges("epl"))
out = sys.argv[1] if len(sys.argv) > 1 else "pick_sheets.html"
Path(out).write_text(html); print("wrote", out)
