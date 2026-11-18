"""Combine the human and the AI reviews into one dataset with a fixed split, used by every later notebook.

Input:
    data/clean/v3/reviews_clean.csv              all cleaned human reviews (27,691)
    data/ai/v1/ai_reviews_clean_lengthfix.csv    AI reviews after the length fix (notebook 02b)

Output (data/final/ is git-ignored: it contains review text):
    dataset_v1.csv        one row per review, with a `split` column
    dataset_report.json   counts per split, class, generator and game

Splits:
    train / val / test   Mistral pairs, 70 / 15 / 15, split BY PAIR and stratified by game:
                         a human review and its AI twin always land in the same split, so a model
                         cannot learn the pair (same game, thumbs, length) instead of the writing style.
    heldout_qwen         Qwen pairs: never used for training or tuning, only as a test of an unseen LLM.
    reserve_human        every other human review (never paired): a human-only test of the false-positive
                         rate, i.e. how often a real player is flagged as AI.

Only complete pairs are used for train/val/test/heldout_qwen. A human review whose AI twin was removed by
cleaning goes to the reserve, so every paired split stays exactly 50 / 50.

Usage:
    python scripts/build_dataset.py
    python scripts/build_dataset.py --human data/clean/v3/reviews_clean.csv \
        --ai data/ai/v1/ai_reviews_clean_lengthfix.csv --out data/final
"""

import argparse
import json
import re
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

GAMES = {
    620: "Portal 2", 105600: "Terraria", 292030: "The Witcher 3: Wild Hunt", 413150: "Stardew Valley",
    289070: "Sid Meier's Civilization VI", 367520: "Hollow Knight", 578080: "PUBG: Battlegrounds",
    646570: "Slay the Spire", 1145360: "Hades", 1151340: "Fallout 76", 1091500: "Cyberpunk 2077",
    1517290: "Battlefield 2042",
}

# Qwen sometimes slips into Chinese; a few characters survive the "90% Latin letters" rule.
CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯]")

COLUMNS = ["review_id", "pair_id", "split", "label", "generator", "appid", "game", "voted_up", "text",
           "word_count", "target_words", "prompt_style", "length_fix", "year"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--human", type=Path, default=Path("data/clean/v3/reviews_clean.csv"))
    parser.add_argument("--ai", type=Path, default=Path("data/ai/v1/ai_reviews_clean_lengthfix.csv"))
    parser.add_argument("--out", type=Path, default=Path("data/final"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    human = pd.read_csv(args.human)
    ai = pd.read_csv(args.ai)
    report = {"human_input": len(human), "ai_input": len(ai)}

    # 1. Drop AI reviews that still contain East Asian characters (and with them their pair).
    cjk = ai.text.str.contains(CJK)
    report["ai_dropped_cjk_characters"] = int(cjk.sum())
    ai = ai[~cjk]

    # 2. Complete pairs only: every AI review has its human twin (checked), every paired human has an AI twin.
    assert ai.pair_id.isin(human.review_id).all(), "an AI review points to an unknown human review"
    paired_human = human[human.review_id.isin(ai.pair_id)].copy()
    reserve = human[~human.review_id.isin(ai.pair_id)].copy()

    # 3. Which pairs go where. Split the PAIR ids, then both reviews of a pair follow.
    pairs = ai[["pair_id", "generator", "appid"]]
    mistral = pairs[pairs.generator == "mistral"]
    train_ids, rest = train_test_split(mistral, test_size=0.30, stratify=mistral.appid, random_state=args.seed)
    val_ids, test_ids = train_test_split(rest, test_size=0.50, stratify=rest.appid, random_state=args.seed)
    split_of = {**dict.fromkeys(train_ids.pair_id, "train"), **dict.fromkeys(val_ids.pair_id, "val"),
                **dict.fromkeys(test_ids.pair_id, "test"),
                **dict.fromkeys(pairs[pairs.generator == "qwen"].pair_id, "heldout_qwen")}

    # 4. Same columns for both classes.
    paired_human = paired_human.assign(
        pair_id=paired_human.review_id, generator="human", target_words=paired_human.word_count,
        prompt_style=None, length_fix=False)
    paired_human["split"] = paired_human.pair_id.map(split_of)
    ai = ai.assign(split=ai.pair_id.map(split_of), year=None)
    reserve = reserve.assign(pair_id=None, split="reserve_human", generator="human",
                             target_words=None, prompt_style=None, length_fix=False)

    df = pd.concat([paired_human, ai, reserve], ignore_index=True)
    df["game"] = df.appid.map(GAMES)
    df["voted_up"] = df.voted_up.astype(str).str.lower().eq("true")
    # year of writing, human reviews only (AI reviews were written in 2026)
    if "timestamp_created" in df:
        df["year"] = pd.to_datetime(df.timestamp_created, unit="s").dt.year.astype("Int64")
    # whole numbers stay whole numbers (the reserve has no pair_id / target, which would turn them into floats)
    for col in ["pair_id", "target_words"]:
        df[col] = pd.to_numeric(df[col]).astype("Int64")
    df = df[COLUMNS]

    # 5. Sanity checks: no pair is spread over two splits, paired splits are balanced.
    paired = df[df.split != "reserve_human"]
    assert paired.groupby("pair_id").split.nunique().max() == 1, "a pair is split across sets"
    assert (paired.groupby("split").label.mean() == 0.5).all(), "a paired split is not 50/50"
    assert df.review_id.is_unique

    args.out.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out / "dataset_v1.csv", index=False)

    report["rows"] = len(df)
    report["per_split"] = {s: {"human": int((g.label == 0).sum()), "ai": int((g.label == 1).sum())}
                           for s, g in df.groupby("split")}
    report["per_split_and_game"] = df[df.label == 1].groupby(["split", "game"]).size().unstack(0).to_dict()
    (args.out / "dataset_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({k: v for k, v in report.items() if k != "per_split_and_game"}, indent=2))


if __name__ == "__main__":
    main()
