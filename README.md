# Human or AI? Detecting AI-generated reviews

Text Analytics 2 semestral project. We test whether a classifier can tell from the text alone whether a short review was written by a person or by an LLM.

**Team:** Vojtěch Hrdina, Eliška Nikolova, Šimon Bartek, Anna Šnevajsová, Kryštof Žák

## Status

Last updated: 26 November 2026.

| Part | State |
| --- | --- |
| Human review collection | done (v3): 36,000 Steam reviews from 12 games, spread over 2015 – Nov 2022 |
| Cleaning | done: 27,691 reviews kept (76.9%) |
| Exploration of the human reviews | done: `notebooks/01_explore_human_reviews.ipynb` |
| AI review generation | done: `notebooks/02_generate_ai_reviews.ipynb` + length fix `02b_fix_lengths.ipynb`: 11,609 AI reviews (Mistral 8,843, Qwen 2,766 held out) |
| Train/validation/test split | done: `scripts/build_dataset.py` → `data/final/dataset_v1.csv` (one file for all later steps) |
| Simple features and baselines | done: `notebooks/03_features_and_baselines.ipynb` |
| Models (MLP + ablation, CNN, BiLSTM, DistilBERT) | done: `notebooks/04_keras_models.ipynb`, `05_distilbert.ipynb` |
| Error analysis | done: `scripts/error_analysis.py` → `results/06_error_analysis/`, summary in [Analysed failure cases](#analysed-failure-cases) |

## Results

All models are trained on the Mistral `train` split only. **Test** = Mistral reviews never seen in training; **Qwen** = reviews from an LLM never seen at all; **FPR** = share of the 16,090 human-only reserve reviews flagged as AI (real players falsely accused).

| Model | val | test | Qwen | Qwen recall | FPR |
| --- | --- | --- | --- | --- | --- |
| Dummy (always "human") | 50.0% | 50.0% | 50.0% | 0.0% | 0.0% |
| Length only | 52.8% | 53.0% | 47.8% | 40.5% | 44.6% |
| 15 simple features (logistic regression) | 90.5% | 91.6% | 81.3% | 71.3% | 11.9% |
| TF-IDF + logistic regression | 99.0% | 99.0% | 82.8% | 67.1% | 1.1% |
| MLP, TF-IDF, lowercase, no punctuation | 98.7% | 98.6% | 86.9% | 75.4% | 1.7% |
| MLP, TF-IDF, case and punctuation kept | 99.3% | 99.3% | 84.9% | 70.6% | 0.7% |
| MLP, TF-IDF, stopwords removed | 98.3% | 98.1% | 81.1% | 63.2% | 1.0% |
| CNN | 98.6% | 98.8% | 81.9% | 65.0% | 1.0% |
| BiLSTM | 98.9% | 98.7% | 78.4% | 57.9% | 1.1% |
| **DistilBERT (cased)** | **99.4%** | **99.4%** | **88.2%** | **77.1%** | 1.1% |

- **The known generator is easy:** every reasonable model reaches 98–99% on Mistral; length alone is useless (53%), so the length fix worked.
- **The unseen generator is the real problem:** on Qwen the models range from 78% to 88%. The pre-trained DistilBERT and the simple MLP generalise best; the more complex models trained from scratch generalise worst (CNN 82%, BiLSTM 78%): they learn the training generator's style. Even the best model misses about a quarter of Qwen reviews.
- **Simple giveaways:** humans start with a lowercase letter (21%), write a lowercase "i" (10%) or skip apostrophes (8%); Mistral and Qwen never do. AI writes about the game's known features (*mind-bending*, *Appalachia*, *Geralt*), people about their purchase and patches (*refund*, *sale*, *fixed*, *edit*).
- **Accuracy is not enough:** the simple features reach 91.6% but would flag 12% of real players.
- Each neural model was trained once; differences of 1–2 points may be noise. No hyperparameter tuning (see notebook 04 for why). The model architectures (MLP, CNN, BiLSTM, DistilBERT settings) are adapted from Kryštof Žák's earlier coursework (4IZ175, sentiment classification); what was changed for this task and why is listed at the start of notebook 04.

## Analysed failure cases

All numbers come from `results/06_error_analysis/` (script `scripts/error_analysis.py`). It uses the saved predictions of notebooks 04 and 05 and refits the two scikit-learn baselines; nothing is retrained on a GPU.

**1. Qwen reviews that start with "This game" are taken for human.** DistilBERT misses 632 of the 2,758 Qwen reviews, and it is sure about it: the median AI score of a missed review is 0.000. Mistral never starts a review with "This game" (0.0%), so in training every review that does is human. 41.1% of the missed Qwen reviews start this way (13.2% of all Qwen reviews, 4.8% of human ones). Example, AI score 0.000:

> *This game is so relaxing and fun!* (Qwen, Stardew Valley, plain style)

The detector learned Mistral's habits ("Can't wait…" in 12.0% of Mistral reviews, 0.2% of Qwen ones), not AI writing in general. A lower threshold does not help: at the threshold that flags 1% of validation humans (0.127), Qwen recall rises only from 77.1% to 78.7%.

**2. Short, enthusiastic human reviews are flagged as AI.** The real players DistilBERT is surest about (AI score 1.000) write like Mistral:

> *Perfection! A must-have!* (The Witcher 3, 2016)

Reviews of five words or fewer are flagged 1.93% of the time, against 0.32% at 100–300 words. Reviews with few common English words (mostly non-English text that passed cleaning) are flagged 3.1% of the time, against 0.9% for the rest.

**3. Small edits fool the baselines.** Lowercasing the first letter, writing "i", dropping apostrophes and the final full stop lowers TF-IDF + logistic regression's Qwen recall from 67.1% to 47.7%. The simple-features model drops from 71.3% to 0.0% (`stress_test.csv`).

**What did not hold up:** we expected old human reviews to look "more human" than recent ones, but DistilBERT's false-positive rate is flat across 2015–2022 (`reserve_fpr_by_group.csv`).

## Where to find what

| Path | Content |
| --- | --- |
| `scripts/collect_steam_reviews.py` | collects human reviews written before 30 Nov 2022 |
| `scripts/clean_reviews.py` | cleans the raw reviews and counts what each rule removes |
| `scripts/build_dataset.py` | combines human and AI reviews into `data/final/dataset_v1.csv` with a fixed split |
| `failure-journal.md` | dated list of what we tried and what did not work |
| `data/sample/` | small samples: 48 human reviews (anonymised) and 48 AI-generated reviews (24 Mistral, 24 Qwen, no ids); the full data is not published |
| `scripts/make_sample.py`, `scripts/make_ai_sample.py` | make the two samples |
| `scripts/error_analysis.py` | error analysis for the report: missed Qwen reviews, flagged players, stress test, thresholds, confidence intervals |
| `results/06_error_analysis/` | its output tables and a few short failure quotes |
| `data/raw/`, `data/clean/` | collected and cleaned reviews, kept locally only (git-ignored) |
| `notebooks/` | `01` exploration of human reviews, `02`/`02b` AI generation and length fix, `03` simple features and baselines, `04` Keras models, `05` DistilBERT (all run in Colab) |
| `data/ai/` | generated AI reviews, kept on the team's Google Drive (git-ignored) |
| `results/` | metrics tables, run log, charts and confusion matrices per notebook (`03_baselines/`, `04_models/`) |

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
- The human reviews are from 2015–2022 and the AI reviews were generated in 2026, so the model could partly learn "old vs new" language. We checked the human side: the false-positive rate does not rise or fall with the year (`results/06_error_analysis/reserve_fpr_by_group.csv`).
- Mixed-language reviews and reviews edited after 29 Nov 2022 are excluded.
- The language check only catches non-Latin scripts: a non-English review written in plain Latin letters passes (e.g. Vietnamese without accents: "game hay vcl du ma no'").

### AI reviews

Generated in Google Colab on a GPU (the notebook also runs on the free T4; the timings in this README and the failure journal were measured on an L4) with two open models from Hugging Face, loaded in 4-bit:

| Generator | Model | Reviews | Role |
| --- | --- | --- | --- |
| `mistral` | `mistralai/Mistral-7B-Instruct-v0.3` | 9,000 | training, validation, test |
| `qwen` | `Qwen/Qwen2.5-7B-Instruct` | 3,000 | **held out**: only a test of an LLM the detector never saw |

- **Pairs.** 1,000 human reviews per game (12,000) are sampled at random (seed 42) from reviews with at most 300 words. Each gets one AI twin with the same game, thumbs up/down and target length. `pair_id` is the human `review_id`. Human reviews over 300 words (2.6%) are not paired.
- **Why 12,000 and not all 27,691.** A fixed 1,000 per game gives every game the same weight; generation takes about 2.5 hours on a Colab L4 instead of over 6; and about 24,000 labelled reviews is enough for this binary task. `reviews_clean.csv` stays complete: the chosen 12,000 are listed in `pairs.csv`, and the other 15,691 human reviews are a **reserve** test set for the false-positive rate (real players flagged as AI).
- **Split** (`scripts/build_dataset.py`, see "Final dataset" below). The Mistral pairs are split 70/15/15 into train, validation and test **by pair**, stratified by game: a human review and its AI twin always land in the same set, so the model cannot learn the pair instead of the writing style. The Qwen pairs (5,516 reviews) are only a held-out test.
- **Prompt (v2).** The model writes as the player ("You have played X and you are writing your own user review of it on Steam... first person, not like an advertisement"). Prompt v1 gave advert-like text, see the failure journal. One prompt per review, containing only the game name, the recommendation, the target length and one of five styles (casual, detailed, emotional, humorous, plain), picked at random. The human review text is never sent to the model.
- **Sampling.** temperature 0.9, top_p 0.95, repetition penalty 1.05, the same for both models. Prompt, model and settings are stored with every raw output.
- **Not exactly reproducible.** A new run produces similar reviews, not the same ones: sampling is random (seed per batch), library and model versions are not pinned, and 4-bit GPU generation is not bit-for-bit deterministic. The method is reproducible; the texts are not, so all later steps use the one shared `dataset_v1.csv`.
- **Test mode.** `notebooks/02_generate_ai_reviews.ipynb` is committed with `TEST_RUN = True` (100 reviews, to measure speed). Set it to `False` for a full run.
- **Length fix.** The models ignore short targets (median AI 29 words vs. target 18 in the first Mistral run). Reviews far from their target length (more than 1.5 × target + 3 words, or fewer than target / 1.5 − 3) are regenerated with a hard limit ("at most / at least N words"), 4 candidates each, and the closest is kept (`length_fix = True`). This is a separate notebook, `notebooks/02b_fix_lengths.ipynb`, which writes a new file `ai_reviews_clean_lengthfix.csv`; the original `ai_reviews_clean.csv` from notebook 02 is kept for comparison.
- **Cleaning.** Chat wrappers are stripped and counted ("Here is a review:", "Review:", markdown, surrounding quotes, "(Word count: 25)"). Then the same rules as for the human reviews are applied, from `scripts/clean_reviews.py`.

Output on the team Drive (`TA2/data/ai/v1/`): `pairs.csv`, `raw_<generator>.jsonl`, `ai_reviews_clean.csv` (`review_id, pair_id, appid, text, voted_up, word_count, target_words, generator, prompt_style, held_out, label`), `generation_report.json`, `postprocess_examples.csv`.

Known limits: only 7B open models, which may be easier to detect than large commercial models; the detector learns "these models under our prompts", not all AI text.

### Final dataset (`data/final/dataset_v1.csv`)

One file for every later notebook, built by `scripts/build_dataset.py` (seed 42). Only complete pairs are used, so every paired split is exactly 50/50; 8 Qwen reviews that still contained Chinese characters were dropped together with their pair.

| `split` | Human | AI | Use |
| --- | --- | --- | --- |
| `train` | 6,190 | 6,190 (Mistral) | training |
| `val` | 1,326 | 1,326 (Mistral) | tuning, model choice |
| `test` | 1,327 | 1,327 (Mistral) | final comparison of models |
| `heldout_qwen` | 2,758 | 2,758 (Qwen) | test on an LLM never seen in training |
| `reserve_human` | 16,090 | 0 | false-positive rate on real players never seen |
| **Total** | **27,691** | **11,601** | **39,292 rows** |

The Mistral pairs are split 70/15/15 **by pair** and stratified by game: a human review and its AI twin are always in the same split. Every later notebook starts from this one file:

```python
df = pd.read_csv("data/final/dataset_v1.csv")
train, val, test = (df[df.split == s] for s in ["train", "val", "test"])
X_train, y_train = train.text, train.label        # 0 = human, 1 = AI
```

A human review and its AI twin share the same `pair_id`. Columns: `review_id, pair_id, split, label (0 human / 1 AI), generator (human / mistral / qwen), appid, game, voted_up, text, word_count, target_words, prompt_style, length_fix, year` (`year` only for human reviews).

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
# notebooks/02_generate_ai_reviews.ipynb and 02b_fix_lengths.ipynb in Colab -> data/ai/v1/
python scripts/build_dataset.py              # writes data/final/dataset_v1.csv
# notebooks 03 (CPU), 04 and 05 (GPU) in Colab -> results/03_baselines/, results/04_models/
python scripts/error_analysis.py             # CPU, about a minute -> results/06_error_analysis/
python scripts/make_ai_sample.py             # -> data/sample/ai_reviews_sample.csv
```

Then run `notebooks/01_explore_human_reviews.ipynb`. The cleaning step writes `reviews_clean.csv`, `cleaning_report.json` (counts per rule, overall and per game) and `dropped_examples.csv` (25 randomly picked removed reviews per rule) into `data/clean/v3/`.

Steam changes over time (reviews get deleted or edited), so a new run will not return exactly the same reviews. The team works on one shared copy of the data from 17 November 2026.
