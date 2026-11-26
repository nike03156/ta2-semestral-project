"""Make the small sample of AI-generated reviews that is published in data/sample/.

All texts in this file were written by language models (Mistral-7B-Instruct-v0.3 or Qwen2.5-7B-Instruct),
not by Steam users. pair_id and review_id are left out on purpose: the pair_id is the Steam id of the
human review the AI twin was matched to, so it would point to that review and its author.

The sample is stratified: the same number of reviews per game and generator, picked at random (fixed seed).

Usage:
    python scripts/make_ai_sample.py
    python scripts/make_ai_sample.py --per-group 2 --in data/final/dataset_v1.csv

Output: data/sample/ai_reviews_sample.csv
"""

import argparse
from pathlib import Path

import pandas as pd

OUT_COLUMNS = ["generator", "game", "voted_up", "prompt_style", "target_words", "word_count", "length_fix", "label", "text"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--in", dest="in_path", type=Path, default=Path("data/final/dataset_v1.csv"))
    parser.add_argument("--out", type=Path, default=Path("data/sample/ai_reviews_sample.csv"))
    parser.add_argument("--per-group", type=int, default=2, help="reviews per game and generator")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = pd.read_csv(args.in_path)
    ai = df[df.label == 1]
    sample = (ai.sample(frac=1, random_state=args.seed)
                .groupby(["game", "generator"]).head(args.per_group)
                .sort_values(["game", "generator"])[OUT_COLUMNS])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(args.out, index=False, encoding="utf-8")
    print(f"{len(sample)} AI reviews ({sample.generator.value_counts().to_dict()}) -> {args.out}")


if __name__ == "__main__":
    main()
