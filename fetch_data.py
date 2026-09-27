"""Download schedules, results, betting lines and play-by-play from nflverse (free, public)."""
import sys, urllib.request
from pathlib import Path
DATA = Path(__file__).parent / "data"; DATA.mkdir(exist_ok=True)
BASE = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{}.parquet"

def get(url, dest):
    print("downloading", dest.name); urllib.request.urlretrieve(url, dest)

if __name__ == "__main__":
    current = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    get("https://github.com/nflverse/nfldata/raw/master/data/games.csv", DATA / "games.csv")
    for y in range(2013, current + 1):
        f = DATA / f"pbp_{y}.parquet"
        if y == current or not f.exists():   # past seasons never change; always refresh the current one
            get(BASE.format(y), f)
