"""Download nflverse weekly rosters and injury reports used by the anytime-TD model."""
import sys, urllib.request
from pathlib import Path
DATA = Path(__file__).parent / "data"; DATA.mkdir(exist_ok=True)
BASE = "https://github.com/nflverse/nflverse-data/releases/download/{0}/{0}_{1}.parquet"

if __name__ == "__main__":
    current = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    for kind, name in [("weekly_rosters", "roster_weekly"), ("injuries", "injuries")]:
        for y in range(2015, current + 1):
            f = DATA / f"{name}_{y}.parquet"
            if y == current or not f.exists():
                url = f"https://github.com/nflverse/nflverse-data/releases/download/{kind}/{name}_{y}.parquet"
                print("downloading", f.name); urllib.request.urlretrieve(url, f)
