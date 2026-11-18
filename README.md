# Human or AI? Detecting AI-generated reviews

Text Analytics 2 semestral project. We test whether a classifier can tell from the text alone whether a short review was written by a person or by an LLM.

**Team:** Vojtěch Hrdina, Eliška Nikolova, Šimon Bartek, Anna Šnevajsová, Kryštof Žák

## Status

Last updated: 18 November 2026.

| Part | State |
| --- | --- |
| Human review collection | done (v3): 36,000 Steam reviews from 12 games, spread over 2015 – Nov 2022 |
| Cleaning | done: 27,691 reviews kept (76.9%) |
| Exploration of the human reviews | done: `notebooks/01_explore_human_reviews.ipynb` |
| AI review generation | not started (waiting for API access) |
| Train/validation/test split | not started |
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

Human reviews come from Steam, through Valve's documented review endpoint (`IUserReviewsService/GetAppReviews`), English reviews only. A review counts as human-written only if it was created **and last edited** before ChatGPT was released on 30 November 2022; reviews edited later are skipped (about 4,000 in this run).

**How the reviews are sampled (v3).** For every game, each calendar month from January 2015 (or the game's release) to 29 November 2022 gets one random 7-day slice. The 3,000 reviews per game are split evenly over the months in which the game has reviews and picked at random inside each slice (seed 42). So every game has the same number of reviews, spread over its own lifetime on Steam, and no period (a sale, a launch, an award vote) dominates. The collector waits 1.5 s between requests; the full run made about 1,240 requests.

This is the third version of the collection. The first two were biased, which we only found by checking the dates (details in `failure-journal.md`, 17 Nov 2026):

| | v1: newest 3,000 per game | v2: 30-day windows | **v3: 7-day slice per month** |
| --- | --- | --- | --- |
| Kept reviews | 24,296 | 27,292 | **27,691** |
| Period covered | 8 Jul – 29 Nov 2022 | 2015 – Nov 2022 | **2015 – Nov 2022** |
| Share from 22–29 Nov 2022 | 39.7% | 2.1% | **0.6%** |
| Share from days 21–31 of a month | 58.2% | 48.4% | **37.5%** |
| Median words | 13 | 19 | **19** |
| Positive (thumbs up) | 86.7% | 84.1% | **83.2%** |

v1 and v2 were cleaned with the earlier rules, so their counts are not fully comparable.

| Game | App ID | Genre | Months with reviews | Collected | Kept after cleaning |
| --- | --- | --- | --- | --- | --- |
| Portal 2 | 620 | Puzzle | 95 | 3,000 | 2,198 |
| Terraria | 105600 | Sandbox | 95 | 3,000 | 2,147 |
| The Witcher 3: Wild Hunt | 292030 | RPG | 90 | 3,000 | 2,321 |
| Stardew Valley | 413150 | Farming sim | 81 | 3,000 | 2,379 |
| Civilization VI | 289070 | Strategy | 73 | 3,000 | 2,401 |
| Hollow Knight | 367520 | Platformer | 70 | 3,000 | 2,375 |
| PUBG: Battlegrounds | 578080 | Battle royale | 69 | 3,000 | 1,923 |
| Slay the Spire | 646570 | Card game | 61 | 3,000 | 2,363 |
| Hades | 1145360 | Action | 36 | 3,000 | 2,349 |
| Fallout 76 | 1151340 | Online RPG | 32 | 3,000 | 2,444 |
| Cyberpunk 2077 | 1091500 | RPG | 24 | 3,000 | 2,397 |
| Battlefield 2042 | 1517290 | Shooter | 13 | 3,000 | 2,394 |
| **Total** | | | | **36,000** | **27,691** |

Games are ordered by when they came out on Steam. Cyberpunk 2077, Battlefield 2042, Fallout 76 and PUBG were added for their negative reviews: 83.2% of kept reviews are positive (4,646 negative), and most negative reviews come from these games and Civilization VI.

### Cleaning

Rules are applied in this order; a review is counted under the first rule that removes it. All checks use a Unicode-normalised copy of the text (NFKC), so English written in decorative characters counts as English; the saved text is the original.

| Rule | Removed | Share of collected |
| --- | --- | --- |
| Empty text | 101 | 0.3% |
| More than half of the visible characters are symbols (ASCII art, braille pictures, ".", ":)") | 409 | 1.1% |
| Text mostly in a non-Latin script although tagged English | 180 | 0.5% |
| Fewer than 3 words ("good game", "10/10") | 6,706 | 18.6% |
| Duplicate of an earlier review, ignoring case, spacing and punctuation | 913 | 2.5% |
| **Kept** | **27,691** | **76.9%** |

The median kept review is 19 words long. We read a random sample of 25 removed reviews per rule: 2 of 125 were genuine English reviews (a review followed by a large braille picture; a review written in Unicode small capitals). An earlier rule, "same character 10+ times", was removed because 17 of 25 sampled removals were genuine reviews with emphasis ("damnnnnnnnn", "I love it!!!!!!!!!!"). Details and examples are in notebook 01, section 1.

### Known limits of the human data

- Very short reviews (under 3 words, 18.6% of collected) are excluded, so the detector says nothing about them.
- Days 1–10 of a month hold 23.7% of the reviews instead of about 33%, because the 7-day slice must fit inside the month.
- The month a game came out can be missing when its random slice fell before the release day.
- Year and game are linked: 2015–2016 reviews come only from the oldest games.
- The human reviews are from 2015–2022, the AI reviews will be from 2026, so the model could partly learn "old vs new" language. We will check errors by year.
- Mixed-language reviews and reviews edited after 29 Nov 2022 are excluded.
- The language check only catches non-Latin scripts: a non-English review written in plain Latin letters passes (e.g. Vietnamese without accents: "game hay vcl du ma no'").

### AI reviews

Not generated yet. Plan: one AI review per human review, matched on game, recommendation and length, from several LLMs, with one LLM kept out of training as a generalization test.

## Data schema

Raw reviews (`data/raw/v3/steam_<appid>.jsonl`):

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

Cleaned reviews (`data/clean/v3/reviews_clean.csv`) keep `review_id`, `appid`, `text`, `voted_up`, `playtime_at_review_min`, `votes_up`, `timestamp_created` and add:

| Field | Meaning |
| --- | --- |
| `word_count` | number of words in the review |
| `label` | 0 = human, 1 = AI-generated |

Author ids are never stored. Raw and cleaned review text is not published in this repository.

## Reproduce

```
pip install -r requirements.txt
python scripts/collect_steam_reviews.py      # about 1 hour; writes data/raw/v3/
python scripts/clean_reviews.py              # writes data/clean/v3/
```

Then run `notebooks/01_explore_human_reviews.ipynb`. The cleaning step writes `reviews_clean.csv`, `cleaning_report.json` (counts per rule, overall and per game) and `dropped_examples.csv` (25 randomly picked removed reviews per rule) into `data/clean/v3/`.

Steam changes over time (reviews get deleted or edited), so a new run will not return exactly the same reviews. The team works on one shared copy of the data from 17 November 2026.
