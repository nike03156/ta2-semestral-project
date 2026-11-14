"""Collect human-written Steam reviews from before ChatGPT existed.

Uses Valve's documented review endpoint (no API key needed):
https://partner.steamgames.com/doc/webapi/IUserReviewsService

Usage:
    python scripts/collect_steam_reviews.py                       # default games
    python scripts/collect_steam_reviews.py --appids 620 105600   # chosen games
    python scripts/collect_steam_reviews.py --max-per-app 2000

Output: one JSON-lines file per game in data/raw/ (this folder is git-ignored:
raw scraped data must not be published).
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

API_URL = "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"

# Only reviews written in this window count as "human".
# ChatGPT was released on 30 Nov 2022, so we stop the day before.
DATE_START = int(datetime(2015, 1, 1, tzinfo=timezone.utc).timestamp())
DATE_END = int(datetime(2022, 11, 29, 23, 59, 59, tzinfo=timezone.utc).timestamp())

# Games from different genres, all released well before the cutoff.
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
]

PAUSE_SECONDS = 1.5   # be polite: one request every 1.5 s
PAGE_SIZE = 100       # maximum the API allows


def fetch_page(appid, cursor):
    """Request one page of reviews. Returns the parsed JSON body."""
    query = {
        "appid": appid,
        "filter": 1,                  # 1 = Recent (newest first inside the date range)
        "languages": ["english"],
        "purchase_type": 1,           # 1 = all purchase types
        "num_per_page": PAGE_SIZE,
        "cursor": cursor,
        "date_range_start": DATE_START,
        "date_range_end": DATE_END,
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


def in_window(review):
    """Second safety check on our side: written AND last edited inside the window.

    A review written in 2020 but edited in 2024 could contain AI text, so it is dropped.
    """
    created = review.get("timestamp_created") or 0
    updated = review.get("timestamp_updated") or created
    return DATE_START <= created <= DATE_END and updated <= DATE_END


def collect_app(appid, max_reviews, out_dir):
    out_path = out_dir / f"steam_{appid}.jsonl"
    cursor, seen_cursors, kept, skipped = "*", set(), 0, 0

    with out_path.open("w", encoding="utf-8") as out_file:
        while kept < max_reviews and cursor not in seen_cursors:
            seen_cursors.add(cursor)
            page = fetch_page(appid, cursor)
            reviews = page.get("reviews", [])
            if not reviews:
                break
            for review in reviews:
                if not in_window(review):
                    skipped += 1
                    continue
                out_file.write(json.dumps(keep_fields(review, appid), ensure_ascii=False) + "\n")
                kept += 1
                if kept >= max_reviews:
                    break
            cursor = page.get("cursor") or cursor
            time.sleep(PAUSE_SECONDS)

    print(f"appid {appid}: kept {kept}, skipped {skipped} outside the date window -> {out_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--appids", type=int, nargs="+", default=DEFAULT_APPIDS)
    parser.add_argument("--max-per-app", type=int, default=1500)
    parser.add_argument("--out", type=Path, default=Path("data/raw"))
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    for appid in args.appids:
        collect_app(appid, args.max_per_app, args.out)


if __name__ == "__main__":
    main()
