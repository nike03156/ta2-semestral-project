"""Clean the raw Steam reviews collected by collect_steam_reviews.py.

Every rule runs in the order listed below and is counted, so the report shows how many
reviews each rule removed. The report goes into the "Data and methodology" section.

Usage:
    python scripts/clean_reviews.py
    python scripts/clean_reviews.py --in data/raw --out data/clean --min-words 3

Output:
    data/clean/reviews_clean.csv    cleaned human reviews, label 0 (human)
    data/clean/cleaning_report.json counts per rule
"""

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from statistics import median

# Same character 10+ times in a row: "aaaaaaaaaa", "!!!!!!!!!!", "==========".
REPEATED_CHARS = re.compile(r"(.)\1{9,}")
WORD = re.compile(r"[A-Za-z']+")
WHITESPACE = re.compile(r"\s+")

OUT_FIELDS = [
    "review_id", "appid", "text", "voted_up", "word_count",
    "playtime_at_review_min", "votes_up", "timestamp_created", "label",
]


def load_raw(in_dir):
    """Yield every review from every steam_<appid>.jsonl file in the folder."""
    for path in sorted(in_dir.glob("steam_*.jsonl")):
        with path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)


def duplicate_key(text):
    """Lowercase letters and digits only, so case, spacing and punctuation do not hide copies."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def is_mostly_symbols(text):
    """True when more than half of the non-space characters are symbols (ASCII art, emoji walls)."""
    visible = [c for c in text if not c.isspace()]
    if not visible:
        return True
    symbols = sum(1 for c in visible if not c.isalnum())
    return symbols / len(visible) > 0.5


def is_mostly_english(text):
    """True when at least 90% of the letters are plain ASCII letters.

    Catches reviews tagged 'english' that are really Russian, Chinese, etc.
    A few accented letters (Czech, French names) do not drop a review.
    """
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return True  # digits only: the length rule decides, not this one
    return sum(1 for c in letters if c.isascii()) / len(letters) >= 0.9


def clean(raw_reviews, min_words):
    """Apply the rules in order. Returns (kept rows, report counter)."""
    report = Counter()
    seen = set()
    kept = []

    for review in raw_reviews:
        report["input"] += 1

        text = WHITESPACE.sub(" ", review.get("text") or "").strip()
        if not text:
            report["dropped_empty"] += 1
            continue

        if REPEATED_CHARS.search(text):
            report["dropped_repeated_characters"] += 1
            continue

        if is_mostly_symbols(text):
            report["dropped_mostly_symbols"] += 1
            continue

        language = review.get("language")
        if language not in (None, "english"):
            report["dropped_other_language_tag"] += 1
            continue

        if not is_mostly_english(text):
            report["dropped_non_english_text"] += 1
            continue

        words = WORD.findall(text)
        if len(words) < min_words:
            report["dropped_too_short"] += 1
            continue

        key = duplicate_key(text)
        if key in seen:
            report["dropped_duplicate"] += 1
            continue
        seen.add(key)

        report["kept"] += 1
        kept.append({
            "review_id": review.get("review_id"),
            "appid": review.get("appid"),
            "text": text,
            "voted_up": review.get("voted_up"),
            "word_count": len(words),
            "playtime_at_review_min": review.get("playtime_at_review_min"),
            "votes_up": review.get("votes_up"),
            "timestamp_created": review.get("timestamp_created"),
            "label": 0,  # 0 = human; AI-generated reviews will get label 1
        })

    return kept, report


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--in", dest="in_dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--out", type=Path, default=Path("data/clean"))
    parser.add_argument("--min-words", type=int, default=3,
                        help="drop reviews with fewer words (short reviews are kept on purpose)")
    args = parser.parse_args()

    raw = list(load_raw(args.in_dir))
    if not raw:
        raise SystemExit(f"No steam_*.jsonl files found in {args.in_dir}")

    kept, report = clean(raw, args.min_words)

    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "reviews_clean.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        writer.writeheader()
        writer.writerows(kept)

    summary = dict(report)
    summary["min_words"] = args.min_words
    summary["median_word_count_kept"] = median(r["word_count"] for r in kept) if kept else None
    summary["kept_per_app"] = dict(Counter(r["appid"] for r in kept))
    (args.out / "cleaning_report.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
