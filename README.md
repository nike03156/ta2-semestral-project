# Human or AI? Detecting AI-generated reviews

Text Analytics 2 semestral project. We test whether a classifier can tell from the text alone whether a short review was written by a person or by an LLM.

**Team:** Vojtěch Hrdina, Eliška Nikolova, Šimon Bartek, Anna Šnevajsová, Kryštof Žák

## Status

Last updated: 14 November 2026.

| Part | State |
| --- | --- |
| Human review collection | done: 36,000 Steam reviews from 12 games |
| Cleaning | done: 24,296 reviews kept (67.5%) |
| AI review generation | not started |
| Exploration and train/validation/test split | not started |
| Models (dummy, MLP + TF-IDF, CNN, BiLSTM, DistilBERT) | not started |
| Error analysis | not started |

## Where to find what

| Path | Content |
| --- | --- |
| `scripts/collect_steam_reviews.py` | collects human reviews written before 30 Nov 2022 |
| `scripts/clean_reviews.py` | cleans the raw reviews and counts what each rule removes |
| `failure-journal.md` | dated list of what we tried and what did not work |
| `data/sample/` | small anonymised sample of the data (the full data is not published) |
| `data/raw/`, `data/clean/` | collected and cleaned reviews, kept locally only (git-ignored) |
| `notebooks/` | exploration, training and evaluation notebooks |
| `results/` | metrics table, confusion matrices, analysed failure cases |

## Data

### Human reviews

Human reviews come from Steam, through Valve's documented review endpoint (`IUserReviewsService/GetAppReviews`). A review counts as human-written only if it was created **and last edited** before ChatGPT was released on 30 November 2022. The collection window is 1 January 2015 to 29 November 2022, English only, 3,000 reviews per game, newest first.

| Game | App ID | Genre | Collected | Kept after cleaning |
| --- | --- | --- | --- | --- |
| Portal 2 | 620 | Puzzle | 3,000 | 1,875 |
| Terraria | 105600 | Sandbox | 3,000 | 1,760 |
| Stardew Valley | 413150 | Farming sim | 3,000 | 1,993 |
| The Witcher 3: Wild Hunt | 292030 | RPG | 3,000 | 1,842 |
| Hollow Knight | 367520 | Platformer | 3,000 | 1,980 |
| Slay the Spire | 646570 | Card game | 3,000 | 2,114 |
| Civilization VI | 289070 | Strategy | 3,000 | 2,084 |
| Hades | 1145360 | Action | 3,000 | 2,160 |
| Cyberpunk 2077 | 1091500 | RPG | 3,000 | 2,219 |
| Battlefield 2042 | 1517290 | Shooter | 3,000 | 2,343 |
| Fallout 76 | 1151340 | Online RPG | 3,000 | 2,407 |
| PUBG: Battlegrounds | 578080 | Battle royale | 3,000 | 1,519 |
| **Total** | | | **36,000** | **24,296** |

### Cleaning

Rules are applied in this order, and every removal is counted:

| Rule | Removed | Share of collected |
| --- | --- | --- |
| Empty text | 148 | 0.4% |
| Same character repeated 10+ times (`aaaaaaaaaa`) | 352 | 1.0% |
| More than half of the characters are symbols (ASCII art, emoji walls) | 489 | 1.4% |
| Text mostly in a non-Latin script although tagged English | 228 | 0.6% |
| Fewer than 3 words (`good game`) | 9,360 | 26.0% |
| Duplicate of an earlier review, ignoring case, spacing and punctuation | 1,127 | 3.1% |
| **Kept** | **24,296** | **67.5%** |

The median kept review is 13 words long. Reviews under 3 words are excluded because they carry too little text to classify; this is a known limit of the detector.

### AI reviews

Not generated yet. Plan: one AI review per human review, matched on game, recommendation and length, from several LLMs, with one LLM kept out of training as a generalization test.

## Data schema

Raw reviews (`data/raw/steam_<appid>.jsonl`):

| Field | Meaning |
| --- | --- |
| `review_id` | Steam review id |
| `appid` | game the review is about |
| `text` | review text |
| `voted_up` | true = recommended, false = not recommended |
| `timestamp_created`, `timestamp_updated` | Unix time written / last edited |
| `language` | review language |
| `playtime_at_review_min` | minutes the author had played when writing |
| `votes_up` | helpful votes |
| `received_for_free` | author got the game for free |

Cleaned reviews (`data/clean/reviews_clean.csv`) keep `review_id`, `appid`, `text`, `voted_up`, `playtime_at_review_min`, `votes_up`, `timestamp_created` and add:

| Field | Meaning |
| --- | --- |
| `word_count` | number of words in the review |
| `label` | 0 = human, 1 = AI-generated |

Author ids are never stored. Raw and cleaned review text is not published in this repository.

## Reproduce

```
pip install -r requirements.txt
python scripts/collect_steam_reviews.py --appids 620 105600 413150 292030 367520 646570 289070 1145360 1091500 1517290 1151340 578080 --max-per-app 3000
python scripts/clean_reviews.py
```

The cleaning step writes `reviews_clean.csv`, `cleaning_report.json` (counts per rule) and `dropped_examples.csv` (first 25 removed reviews per rule) into `data/clean/`.
