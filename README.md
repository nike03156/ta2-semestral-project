# Human or AI? Detecting AI-generated reviews

Text Analytics 2 semestral project. We test whether a classifier can tell from the text alone whether a short review was written by a person or by an LLM.

**Team:** Vojtěch Hrdina, Eliška Nikolova, Šimon Bartek, Anna Šnevajsová, Kryštof Žák

## Status

| Part | State |
| --- | --- |
| Human review collection | script written, not yet run |
| AI review generation | not started |
| Models (dummy, MLP + TF-IDF, CNN, BiLSTM, DistilBERT) | not started |
| Error analysis | not started |

## Where to find what

| Path | Content |
| --- | --- |
| `scripts/collect_steam_reviews.py` | collects human reviews written before 30 Nov 2022 |
| `data/sample/` | small anonymised sample of the data (the raw data is not published) |
| `data/raw/` | raw collected data, git-ignored |
| `notebooks/` | exploration, training and evaluation notebooks |
| `results/` | metrics table, confusion matrices, analysed failure cases |
| `failure-journal.md` | dated list of what we tried and what did not work |

## Data schema (human reviews)

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

Author ids are not stored.

## Reproduce

```
pip install -r requirements.txt
python scripts/collect_steam_reviews.py
```
