"""Clean the raw Steam reviews collected by collect_steam_reviews.py.

Every rule runs in the order listed below and is counted, so the report shows how many
reviews each rule removed. The report goes into the "Data and methodology" section.

Rules, in this order:
    1. empty text
    2. the same character 10+ times in a row ("aaaaaaaaaa")
    3. more than half of the visible characters are symbols (ASCII art, emoji walls)
    4. Steam's language tag is not English
    5. fewer than 90% of the letters are plain Latin letters (Russian, Chinese... tagged English)
    6. fewer than --min-words words
    7. duplicate of an earlier review (ignoring case, spacing and punctuation)

Usage:
    python scripts/clean_reviews.py
    python scripts/clean_reviews.py --in data/raw/v2 --out data/clean/v2 --min-words 3

Output (data/clean/ is git-ignored: it contains scraped review text):
    reviews_clean.csv     cleaned human reviews, label 0 (human)
    cleaning_report.json  counts per rule, overall and per game
    dropped_examples.csv  a random sample of removed reviews per rule, to check by eye
                          that each rule removes what it should
"""

import argparse
import csv
import json
import random
import re
from collections import Counter, defaultdict
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
EXAMPLE_FIELDS = ["rule", "review_id", "appid", "text"]


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


def drop_reason(review, text, words, min_words, seen):
    """Return the name of the first rule that removes this review, or None to keep it."""
    if not text:
        return "dropped_empty"
    if REPEATED_CHARS.search(text):
        return "dropped_repeated_characters"
    if is_mostly_symbols(text):
        return "dropped_mostly_symbols"
    if review.get("language") not in (None, "english"):
        return "dropped_other_language_tag"
    if not is_mostly_english(text):
        return "dropped_non_english_text"
    if len(words) < min_words:
        return "dropped_too_short"
    if duplicate_key(text) in seen:
        return "dropped_duplicate"
    return None


def clean(raw_reviews, min_words):
    """Apply the rules in order. Returns (kept rows, report counter, per-game drops, dropped reviews)."""
    report = Counter()
    dropped_per_app = defaultdict(Counter)   # rule -> appid -> how many removed
    dropped = defaultdict(list)              # rule -> removed reviews (for the examples file)
    seen = set()
    kept = []

    for review in raw_reviews:
        report["input"] += 1
        text = WHITESPACE.sub(" ", review.get("text") or "").strip()
        words = WORD.findall(text)

        reason = drop_reason(review, text, words, min_words, seen)
        if reason:
            report[reason] += 1
            dropped_per_app[reason][review.get("appid")] += 1
            dropped[reason].append({"rule": reason, "review_id": review.get("review_id"),
                                    "appid": review.get("appid"), "text": text})
            continue

        seen.add(duplicate_key(text))
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

    return kept, report, dropped_per_app, dropped


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--in", dest="in_dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--out", type=Path, default=Path("data/clean"))
    parser.add_argument("--min-words", type=int, default=3,
                        help="drop reviews with fewer words (short reviews are kept on purpose)")
    parser.add_argument("--examples-per-rule", type=int, default=25,
                        help="how many removed reviews per rule go into dropped_examples.csv")
    parser.add_argument("--seed", type=int, default=42, help="random seed for picking the examples")
    args = parser.parse_args()

    raw = list(load_raw(args.in_dir))
    if not raw:
        raise SystemExit(f"No steam_*.jsonl files found in {args.in_dir}")

    kept, report, dropped_per_app, dropped = clean(raw, args.min_words)

    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "reviews_clean.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        writer.writeheader()
        writer.writerows(kept)

    # A random sample per rule (not the first ones), so every game can appear in it.
    rng = random.Random(args.seed)
    with (args.out / "dropped_examples.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EXAMPLE_FIELDS)
        writer.writeheader()
        for rule in sorted(dropped):
            reviews = dropped[rule]
            writer.writerows(rng.sample(reviews, min(args.examples_per_rule, len(reviews))))

    summary = dict(report)
    summary["min_words"] = args.min_words
    summary["median_word_count_kept"] = median(r["word_count"] for r in kept) if kept else None
    summary["kept_per_app"] = dict(Counter(r["appid"] for r in kept))
    summary["dropped_per_app"] = {rule: dict(counts) for rule, counts in sorted(dropped_per_app.items())}
    (args.out / "cleaning_report.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()