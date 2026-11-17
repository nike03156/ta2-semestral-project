"""Collect human-written Steam reviews from before ChatGPT existed, spread evenly over time.

Uses Valve's documented review endpoint (no API key needed):
https://partner.steamgames.com/doc/webapi/IUserReviewsService

Why this version: the first version asked for the whole period 2015-2022 at once and
stopped at 3,000 reviews per game. Steam returns the newest reviews first, so every review
came from Jul-Nov 2022 (40% from the last 8 days, during the Steam Autumn Sale).

Now, for every game:
  1. The period is cut into windows of --window-days days (default 30).
  2. Pass 1: one page (up to 100 reviews) is requested for every window. Windows before
     the game came out are empty, so we learn how many windows the game has reviews in.
  3. The target (--per-game, default 3,000) is split evenly over those windows.
     A game with reviews in 97 windows needs about 31 per window, a game with 13 windows
     about 231, so pass 2 fetches extra pages only where a window needs more.
  4. Inside each window the reviews are picked at random (fixed --seed, so the result
     can be reproduced).
Every game ends with the same number of reviews, spread over its own lifetime on Steam.

Usage:
    # small test: one game, three months, 300 reviews
    python scripts/collect_steam_reviews.py --appids 620 --start 2016-01-01 --end 2016-03-31 --per-game 300 --out data/raw/test

    # full run: 12 default games, 3,000 reviews each
    python scripts/collect_steam_reviews.py

Output: one JSON-lines file per game in data/raw/v2/ (data/raw/ is git-ignored:
raw scraped data must not be published). The first collection stays untouched.
"""

import argparse
import json
import math
import random
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

API_URL = "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"

# Only reviews written AND last edited before this moment count as "human".
# ChatGPT was released on 30 Nov 2022, so we stop the day before.
CUTOFF = datetime(2022, 11, 29, 23, 59, 59, tzinfo=timezone.utc)

# Games from different genres, all released before the cutoff.
# Check each id against the store URL: store.steampowered.com/app/<appid>/
DEFAULT_APPIDS = [
    620,      # Portal 2 (puzzle)
    105600,   # Terraria (sandbox)
    413150,   # Stardew Valley (farming sim)
    292030,   # The Witcher 3 (RPG)
    367520,   # Hollow Knight (platformer)
    646570,   # Slay the Spire (card game)
    289070,   # Civilization VI (strategy)
    1145360,  # Hades (action)
    1091500,  # Cyberpunk 2077 (RPG)                - added for negative reviews
    1517290,  # Battlefield 2042 (shooter)          - added for negative reviews
    1151340,  # Fallout 76 (online RPG)             - added for negative reviews
    578080,   # PUBG: Battlegrounds (battle royale) - added for negative reviews
]

PAUSE_SECONDS = 1.5       # be polite: one request every 1.5 s
PAGE_SIZE = 100           # maximum the API allows
MAX_PAGES_PER_WINDOW = 5  # safety stop: never more than 500 reviews fetched per window


def parse_date(text):
    """'2016-03-01' -> datetime at midnight UTC."""
    return datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def time_windows(start, end, days):
    """Cut [start, end] into consecutive windows of `days` days.

    Yields (start_ts, end_ts) as Unix timestamps. The last window is shorter if needed.
    """
    window_start = start
    while window_start <= end:
        window_end = min(window_start + timedelta(days=days) - timedelta(seconds=1), end)
        yield int(window_start.timestamp()), int(window_end.timestamp())
        window_start = window_end + timedelta(seconds=1)


def fetch_page(appid, cursor, start_ts, end_ts):
    """Request one page of reviews written between start_ts and end_ts."""
    query = {
        "appid": appid,
        "filter": 1,                  # 1 = Recent (newest first inside the date range)
        "languages": ["english"],
        "purchase_type": 1,           # 1 = all purchase types
        "num_per_page": PAGE_SIZE,
        "cursor": cursor,
        "date_range_start": start_ts,
        "date_range_end": end_ts,
    }
    for attempt in range(5):
        response = requests.get(API_URL, params={"input_json": json.dumps(query)}, timeout=30)
        if response.status_code == 429:           # rate limited: wait longer each time
            time.sleep(30 * (attempt + 1))
            continue
        response.raise_for_status()
        body = response.json()
        return body.get("response", body)         # service APIs wrap the result in "response"
    raise RuntimeError(f"Still rate limited after 5 attempts (appid {appid})")


def keep_fields(review, appid):
    """Keep only what the project needs. The author's Steam id is dropped on purpose."""
    author = review.get("author", {})
    return {
        "review_id": review.get("recommendationid"),
        "appid": appid,
        "text": review.get("review", ""),
        "voted_up": review.get("voted_up"),
        "timestamp_created": review.get("timestamp_created"),
        "timestamp_updated": review.get("timestamp_updated"),
        "language": review.get("language"),
        "playtime_at_review_min": author.get("playtime_at_review"),
        "votes_up": review.get("votes_up"),
        "received_for_free": review.get("received_for_free"),
    }


def in_window(review, start_ts, end_ts):
    """Check on our side, not only trusting Steam's filter:
    written inside this window AND never edited after the ChatGPT cutoff.

    A review written in 2020 but edited in 2024 could contain AI text, so it is dropped.
    """
    created = review.get("timestamp_created") or 0
    updated = review.get("timestamp_updated") or created
    return start_ts <= created <= end_ts and updated <= CUTOFF.timestamp()


def fetch_more(appid, window):
    """Fetch the next page of one window and add its valid reviews to the window's pool."""
    page = fetch_page(appid, window["cursor"], window["start"], window["end"])
    time.sleep(PAUSE_SECONDS)
    window["pages"] += 1
    reviews = page.get("reviews", [])
    for review in reviews:
        if in_window(review, window["start"], window["end"]):
            window["pool"].append(review)
        else:
            window["skipped"] += 1
    next_cursor = page.get("cursor")
    # Stop asking this window when Steam has nothing more, or after the safety limit.
    if not reviews or not next_cursor or next_cursor == window["cursor"] \
            or window["pages"] >= MAX_PAGES_PER_WINDOW:
        window["exhausted"] = True
    window["cursor"] = next_cursor


def split_evenly(pool_sizes, target):
    """How many reviews to take from each window.

    The target is split as evenly as possible. A window cannot give more than it has,
    so what a small window cannot give is shared among the others.
    Example: pools [10, 100, 100], target 90 -> [10, 40, 40].
    """
    quotas = [0] * len(pool_sizes)
    remaining = target
    open_windows = [i for i, size in enumerate(pool_sizes) if size > 0]
    while remaining > 0 and open_windows:
        share = max(1, remaining // len(open_windows))
        still_open = []
        for i in open_windows:
            give = min(share, pool_sizes[i] - quotas[i], remaining)
            quotas[i] += give
            remaining -= give
            if quotas[i] < pool_sizes[i]:
                still_open.append(i)
            if remaining == 0:
                break
        open_windows = still_open
    return quotas


def collect_app(appid, window_bounds, target, seed, out_dir):
    windows = [{"start": s, "end": e, "pool": [], "cursor": "*", "pages": 0,
                "skipped": 0, "exhausted": False} for s, e in window_bounds]

    # Pass 1: one page per window. Empty windows = the game was not out yet (or no reviews).
    for window in windows:
        fetch_more(appid, window)
    active = [w for w in windows if w["pool"]]
    skipped = sum(w["skipped"] for w in windows)
    if not active:
        print(f"appid {appid}: no reviews in any window (skipped {skipped}). "
              "Check the app id and that Steam respects the date filter.")
        return

    # Pass 2: windows that need more than one page (games with few active windows).
    share = math.ceil(target / len(active))
    for window in active:
        while len(window["pool"]) < share and not window["exhausted"]:
            fetch_more(appid, window)

    # Pick at random inside each window. The seed makes the run reproducible.
    quotas = split_evenly([len(w["pool"]) for w in windows], target)
    rng = random.Random(seed + appid)
    chosen = []
    for window, quota in zip(windows, quotas):
        chosen.extend(rng.sample(window["pool"], quota))
    chosen.sort(key=lambda r: r["timestamp_created"])

    out_path = out_dir / f"steam_{appid}.jsonl"
    with out_path.open("w", encoding="utf-8") as out_file:
        for review in chosen:
            out_file.write(json.dumps(keep_fields(review, appid), ensure_ascii=False) + "\n")

    first = datetime.fromtimestamp(active[0]["start"], timezone.utc).date()
    skipped = sum(w["skipped"] for w in windows)
    pages = sum(w["pages"] for w in windows)
    print(f"appid {appid}: kept {len(chosen)}/{target} from {len(active)}/{len(windows)} windows "
          f"(first window with reviews starts {first}), {pages} requests, "
          f"skipped {skipped} outside the window -> {out_path}")
    if len(chosen) < target:
        print("  NOTE: fewer reviews than the target; Steam has no more in these windows.")
    if skipped > len(chosen):
        print("  WARNING: more reviews skipped than kept. Check that Steam respects the date filter.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--appids", type=int, nargs="+", default=DEFAULT_APPIDS)
    parser.add_argument("--start", default="2015-01-01", help="first day, YYYY-MM-DD")
    parser.add_argument("--end", default="2022-11-29", help="last day, YYYY-MM-DD (max 2022-11-29)")
    parser.add_argument("--window-days", type=int, default=30, help="length of one time window")
    parser.add_argument("--per-game", type=int, default=3000, help="reviews to keep per game")
    parser.add_argument("--seed", type=int, default=42, help="random seed, for reproducibility")
    parser.add_argument("--out", type=Path, default=Path("data/raw/v2"))
    args = parser.parse_args()

    start = parse_date(args.start)
    end = min(parse_date(args.end) + timedelta(days=1, seconds=-1), CUTOFF)  # include the whole last day
    window_bounds = list(time_windows(start, end, args.window_days))
    print(f"{len(window_bounds)} windows of {args.window_days} days from {start.date()} to {end.date()}, "
          f"target {args.per_game} reviews per game")

    args.out.mkdir(parents=True, exist_ok=True)
    for appid in args.appids:
        collect_app(appid, window_bounds, args.per_game, args.seed, args.out)


if __name__ == "__main__":
    main()
