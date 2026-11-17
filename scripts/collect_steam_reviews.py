"""Collect human-written Steam reviews from before ChatGPT existed, spread evenly over time.

Uses Valve's documented review endpoint (no API key needed):
https://partner.steamgames.com/doc/webapi/IUserReviewsService

History of this script (details in failure-journal.md):
  v1  one date window 2015-2022, newest 3,000 per game -> every review was from Jul-Nov 2022.
  v2  30-day windows, newest ~100 per window -> 77% of reviews from the last 3 days of a window.
  v3  (this version) one random 7-day slice inside every calendar month.

How it works, for every game:
  1. The period is cut into calendar months.
  2. Inside every month a random slice of --slice-days days (default 7) is drawn.
     Steam returns the newest reviews first, so we only ask for that slice: its position
     inside the month is random, so no part of the month (end, weekends, sales) is favoured.
  3. Pass 1: one page (up to 100 reviews) per slice. Empty slices = the game was not out yet,
     so we learn in how many months the game has reviews.
  4. The target (--per-game, default 3,000) is split evenly over those months; pass 2 fetches
     extra pages only where a slice needs more.
  5. Inside each slice the reviews are picked at random (fixed --seed, so the run can be repeated).
Every game ends with the same number of reviews, spread over its own lifetime on Steam.

Usage:
    # small test: one game, three months, 300 reviews
    python scripts/collect_steam_reviews.py --appids 620 --start 2016-01-01 --end 2016-03-31 --per-game 300 --out data/raw/test

    # full run: 12 default games, 3,000 reviews each
    python scripts/collect_steam_reviews.py

Output: one JSON-lines file per game in data/raw/v3/ (data/raw/ is git-ignored:
raw scraped data must not be published). Earlier collections stay untouched.
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

PAUSE_SECONDS = 1.5      # be polite: one request every 1.5 s
PAGE_SIZE = 100          # maximum the API allows
MAX_PAGES_PER_SLICE = 5  # safety stop: never more than 500 reviews fetched per slice
DAY = timedelta(days=1)


def parse_date(text):
    """'2016-03-01' -> datetime at midnight UTC."""
    return datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def months(start, end):
    """Yield (month_start, month_end) for every calendar month between start and end, clipped to them."""
    month_start = start.replace(day=1, hour=0, minute=0, second=0)
    while month_start <= end:
        next_month = (month_start + timedelta(days=32)).replace(day=1)
        yield max(month_start, start), min(next_month - timedelta(seconds=1), end)
        month_start = next_month


def random_slice(month_start, month_end, slice_days, rng):
    """A random slice of whole days inside one month, as (start_ts, end_ts) Unix timestamps.

    If the month is shorter than the slice (e.g. the last, cut-off month), the whole month is used.
    """
    days_in_month = (month_end - month_start).days + 1
    first_day = rng.randrange(max(1, days_in_month - slice_days + 1))
    slice_start = month_start + first_day * DAY
    slice_end = min(slice_start + slice_days * DAY - timedelta(seconds=1), month_end)
    return int(slice_start.timestamp()), int(slice_end.timestamp())


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


def in_slice(review, start_ts, end_ts):
    """Check on our side, not only trusting Steam's filter:
    written inside this slice AND never edited after the ChatGPT cutoff.

    A review written in 2020 but edited in 2024 could contain AI text, so it is dropped.
    """
    created = review.get("timestamp_created") or 0
    updated = review.get("timestamp_updated") or created
    return start_ts <= created <= end_ts and updated <= CUTOFF.timestamp()


def fetch_more(appid, part):
    """Fetch the next page of one slice and add its valid reviews to the slice's pool."""
    page = fetch_page(appid, part["cursor"], part["start"], part["end"])
    time.sleep(PAUSE_SECONDS)
    part["pages"] += 1
    reviews = page.get("reviews", [])
    for review in reviews:
        if in_slice(review, part["start"], part["end"]):
            part["pool"].append(review)
        else:
            part["skipped"] += 1
    next_cursor = page.get("cursor")
    # Stop asking this slice when Steam has nothing more, or after the safety limit.
    if not reviews or not next_cursor or next_cursor == part["cursor"] \
            or part["pages"] >= MAX_PAGES_PER_SLICE:
        part["exhausted"] = True
    part["cursor"] = next_cursor


def split_evenly(pool_sizes, target):
    """How many reviews to take from each slice.

    The target is split as evenly as possible. A slice cannot give more than it has,
    so what a small slice cannot give is shared among the others.
    Example: pools [10, 100, 100], target 90 -> [10, 40, 40].
    """
    quotas = [0] * len(pool_sizes)
    remaining = target
    open_parts = [i for i, size in enumerate(pool_sizes) if size > 0]
    while remaining > 0 and open_parts:
        share = max(1, remaining // len(open_parts))
        still_open = []
        for i in open_parts:
            give = min(share, pool_sizes[i] - quotas[i], remaining)
            quotas[i] += give
            remaining -= give
            if quotas[i] < pool_sizes[i]:
                still_open.append(i)
            if remaining == 0:
                break
        open_parts = still_open
    return quotas


def collect_app(appid, month_bounds, target, slice_days, seed, out_dir):
    rng = random.Random(seed + appid)   # own random numbers per game: different slices for each game
    parts = []
    for month_start, month_end in month_bounds:
        start_ts, end_ts = random_slice(month_start, month_end, slice_days, rng)
        parts.append({"start": start_ts, "end": end_ts, "pool": [], "cursor": "*",
                      "pages": 0, "skipped": 0, "exhausted": False})

    # Pass 1: one page per slice. Empty slices = the game was not out yet (or no reviews).
    for part in parts:
        fetch_more(appid, part)
    active = [p for p in parts if p["pool"]]
    if not active:
        print(f"appid {appid}: no reviews in any slice (skipped {sum(p['skipped'] for p in parts)}). "
              "Check the app id and that Steam respects the date filter.")
        return

    # Pass 2: slices that need more than one page (games with few active months).
    share = math.ceil(target / len(active))
    for part in active:
        while len(part["pool"]) < share and not part["exhausted"]:
            fetch_more(appid, part)

    # Pick at random inside each slice.
    quotas = split_evenly([len(p["pool"]) for p in parts], target)
    chosen = []
    for part, quota in zip(parts, quotas):
        chosen.extend(rng.sample(part["pool"], quota))
    chosen.sort(key=lambda r: r["timestamp_created"])

    out_path = out_dir / f"steam_{appid}.jsonl"
    with out_path.open("w", encoding="utf-8") as out_file:
        for review in chosen:
            out_file.write(json.dumps(keep_fields(review, appid), ensure_ascii=False) + "\n")

    first = datetime.fromtimestamp(active[0]["start"], timezone.utc).date()
    skipped = sum(p["skipped"] for p in parts)
    pages = sum(p["pages"] for p in parts)
    print(f"appid {appid}: kept {len(chosen)}/{target} from {len(active)}/{len(parts)} months "
          f"(first slice with reviews starts {first}), {pages} requests, "
          f"skipped {skipped} outside the slice -> {out_path}")
    if len(chosen) < target:
        print("  NOTE: fewer reviews than the target; try a longer --slice-days for this game.")
    if skipped > len(chosen):
        print("  WARNING: more reviews skipped than kept. Check that Steam respects the date filter.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--appids", type=int, nargs="+", default=DEFAULT_APPIDS)
    parser.add_argument("--start", default="2015-01-01", help="first day, YYYY-MM-DD")
    parser.add_argument("--end", default="2022-11-29", help="last day, YYYY-MM-DD (max 2022-11-29)")
    parser.add_argument("--slice-days", type=int, default=7, help="length of the random slice in each month")
    parser.add_argument("--per-game", type=int, default=3000, help="reviews to keep per game")
    parser.add_argument("--seed", type=int, default=42, help="random seed, for reproducibility")
    parser.add_argument("--out", type=Path, default=Path("data/raw/v3"))
    args = parser.parse_args()

    start = parse_date(args.start)
    end = min(parse_date(args.end) + DAY - timedelta(seconds=1), CUTOFF)  # include the whole last day
    month_bounds = list(months(start, end))
    print(f"{len(month_bounds)} months from {start.date()} to {end.date()}, a random {args.slice_days}-day "
          f"slice in each, target {args.per_game} reviews per game")

    args.out.mkdir(parents=True, exist_ok=True)
    for appid in args.appids:
        collect_app(appid, month_bounds, args.per_game, args.slice_days, args.seed, args.out)


if __name__ == "__main__":
    main()
