"""Make the small anonymised sample of human reviews that is published in data/sample/.

The full data must not be published (scraped text, Steam terms), so the repository holds
only this sample. It is stratified: the same number of positive and negative reviews from
every game, picked at random (fixed seed, so the same sample comes out every time).

Anonymised: review_id is left out (it would lead back to the review and its author on Steam),
the exact time is reduced to the year, and playtime and helpful votes are left out.
Author ids were never collected.

Usage:
    python scripts/make_sample.py
    python scripts/make_sample.py --per-group 2 --in data/clean/v3/reviews_clean.csv

Output: data/sample/human_reviews_sample.csv
"""

import argparse
from pathlib import Path

import pandas as pd

GAMES = {
    620: "Portal 2", 105600: "Terraria", 413150: "Stardew Valley", 292030: "Witcher 3",
    367520: "Hollow Knight", 646570: "Slay the Spire", 289070: "Civilization VI",
    1145360: "Hades", 1091500: "Cyberpunk 2077", 1517290: "Battlefield 2042",
    1151340: "Fallout 76", 578080: "PUBG",
}
OUT_COLUMNS = ["game", "appid", "year", "voted_up", "word_count", "label", "text"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--in", dest="in_path", type=Path, default=Path("data/clean/v3/reviews_clean.csv"))
    parser.add_argument("--out", type=Path, default=Path("data/sample/human_reviews_sample.csv"))
    parser.add_argument("--per-group", type=int, default=2,
                        help="reviews per game and recommendation (2 -> 2 positive + 2 negative per game)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = pd.read_csv(args.in_path)
    df["game"] = df["appid"].map(GAMES)
    df["year"] = pd.to_datetime(df["timestamp_created"], unit="s", utc=True).dt.year

    # Shuffle once (fixed seed), then take the first rows of every (game, positive/negative) group:
    # the same number from each group, fewer if a group is smaller.
    shuffled = df.sample(frac=1, random_state=args.seed)
    sample = shuffled.groupby(["appid", "voted_up"]).head(args.per_group)
    sample = sample.sort_values(["game", "voted_up", "year"])[OUT_COLUMNS]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(args.out, index=False, encoding="utf-8")
    print(f"{len(sample)} reviews from {sample['game'].nunique()} games "
          f"({int(sample['voted_up'].sum())} positive, {int((~sample['voted_up'].astype(bool)).sum())} negative) "
          f"-> {args.out}")


if __name__ == "__main__":
    main()
