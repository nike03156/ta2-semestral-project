# Detecting AI-Generated Reviews: project handoff

**Status as of Saturday 14 November 2026, 20:15.** Written for teammates and for any LLM assistant they work with. It is self-contained: read it top to bottom and you know the rules, what exists, and what is left.

**Team:** Vojtěch Hrdina, Eliška Nikolova, Šimon Bartek, Anna Šnevajsová, Kryštof Žák
**Course:** Text Analytics 2 (semestral project)
**Theme (fixed):** Detecting AI-generated reviews. Can a classifier tell from the text alone whether a short review was written by a person or by an LLM?

---

## 1. Summary

- The public GitHub repository exists with a README, a failure journal, a collection script and a cleaning script.
- Human reviews are collected from Steam (game reviews written before ChatGPT): 36,000 collected from 12 games, **24,296 kept** after cleaning.
- Next step is generating the AI reviews. It is blocked on one thing: someone has to check API access (section 7).
- Nothing has been trained yet. The prefinal package is due **Thursday 26 November 2026, 23:59**.

---

## 2. Rules from the teacher (cannot be changed)

Source: "Project types and criteria" and "Prefinal project submission task".

**Ground rules**

- A ready-made clean dataset must not be the only source. We must do our own collection and our own cleaning.
- AI tools are allowed for coding and drafting, but every team member must be able to explain and defend everything submitted. Code or text nobody can explain is scored as if it did not exist.
- Keep a trace of the process (git history, notes, commit messages).
- Consultations are mandatory in every phase.
- Raw scraped data must not be published. The repository holds the collection script, the schema and a small anonymised sample.

**Grading: four pillars, 25% each**

1. Data and methodology: suitable, justified data; noise, duplicates and edge cases handled; method choice explained.
2. Comparison of approaches and error analysis: at least two approaches; where and why the model fails on concrete examples, not only an aggregate metric.
3. Process reflection and failure journal: what did not work, what we changed our mind about and why.
4. Critical thinking and defense: limits, risks and biases of our own solution; defending decisions under questioning.

For a **Model** project (the type that fits us; confirm it with the teacher), the criteria specifically ask for: justified representation, architecture and hyperparameters; baseline vs stronger models; confusion matrix and concrete misclassified examples; ideally ablations; failed training runs in the journal; limits of generalization, bias in training data, robustness to distribution shift.

**At the Final Defense** the teacher may ask anyone about any part of the project, not only its author.

**Deadlines**

| What | When |
| --- | --- |
| Prefinal package (report, failure journal, contributions, repository with tag) | Thu 26 Nov 2026, 23:59 |
| Individual feedback on three other teams | Mon 7 Dec 2026 |
| Slides | Tue 8 Dec 2026 |
| Day 3 presentation (6 min talk + 7 min discussion) | Thu 10 Dec 2026 |

**Prefinal package contents** (one folder in the team's Teams folder, named as the project)

| File | Content |
| --- | --- |
| `report.pdf` | 3–5 pages, public repository link on page one. Order: goal and results; data and methodology; comparison of approaches and error analysis; limits and risks. Concise, with concrete examples everywhere, no general NLP introductions. |
| `failure-journal.pdf` | 1–2 pages, dated entries kept from the start. |
| `contributions.pdf` | Half a page: who did what, mapped to the pillars. |
| Slides | Due later (8 Dec). |

**Repository requirements:** README with overview and where to find what; a sample of data and outputs; a metrics table; one or two analysed failure cases; a git tag named `prefinal` (`git tag prefinal && git push origin prefinal`).

---

## 3. Decisions made so far, with reasons

Each of these is something any team member may have to defend.

| Decision | Reason | Cost / what to admit |
| --- | --- | --- |
| Collect the human reviews ourselves instead of using public datasets (as the proposal said). | The course forbids a ready-made clean dataset as the only source. | More work; smaller dataset. |
| Use Kryštof's SST-2 notebook only partially: keep its modelling skeleton (MLP + TF-IDF, CNN, BiLSTM, DistilBERT, baseline vs tuned), add our own evaluation. | That notebook reports test accuracy only. This course grades error analysis, a failure journal and limits. | None. |
| Source of human reviews: **Steam** (game reviews). | Valve documents a public endpoint for downloading an app's reviews; no key needed; exact timestamps and a date-range filter. | Domain is games only; rating is thumbs up/down, not stars. |
| Google Maps was considered and rejected. | The official Places API returns at most 5 reviews per place and forbids storing them; scraping the site is against Google's terms; dates are shown only as "3 years ago". | The proposal's motivation mentions Google Maps and e-shops, so the report must say the method is demonstrated on a different review domain. |
| "Human" = written **and last edited** before ChatGPT's release on 30 Nov 2022. The script's window is 1 Jan 2015 to 29 Nov 2022. | Before that date reviews cannot be LLM-written. An old review edited later could contain AI text, so it is dropped. | Human reviews are older than the AI ones; language drift over time is a possible confound. |
| Author Steam IDs are never stored. | Personal data; not needed. | None. |
| Minimum review length: 3 words. | 26% of collected reviews had fewer than 3 words ("good game"); no classifier can use that. | The detector has a length floor. This is a limit to report, and it qualifies the proposal's "short reviews" claim. |
| Games chosen from different genres. | So the model does not learn one game's vocabulary. | Still a small set of games. |

**Lessons taken from Kryštof's notebook**

- Its validation set was tiny (872) with a different class balance than the test set, which made hyperparameter tuning unreliable (tuned MLP was worse than baseline). We need a proper stratified train/validation/test split.
- Its MLP pipeline removes stopwords and punctuation. For AI detection those may be exactly the signal (function words, punctuation habits). Test with and without as an ablation.

---

## 4. Repository

Public GitHub repository created by Eliška. **Link: (Eliška to fill in.)** Teammates are being added as collaborators.

| Path | Content |
| --- | --- |
| `README.md` | Overview, status table, where to find what, data schema. Status table needs updating as work progresses. |
| `failure-journal.md` | Dated table of what we tried, how it failed, what we did instead. |
| `scripts/collect_steam_reviews.py` | Collects human reviews from Steam. |
| `scripts/clean_reviews.py` | Cleans the raw reviews and writes a report. |
| `requirements.txt` | `requests`, `pandas`. |
| `.gitignore` | Ignores `data/raw/`, models, `.env`, caches. |
| `data/sample/`, `notebooks/`, `results/` | Empty placeholders. |

**To check in the repository (not confirmed):**

- Is the latest `clean_reviews.py` pushed? The latest version also writes `data/clean/dropped_examples.csv`.
- `.gitignore` ignores only `data/raw/`. `data/clean/` also contains scraped review text and must not be committed. Add `data/clean/` to `.gitignore`.
- Does the failure journal contain all four entries listed in section 8?

### `collect_steam_reviews.py`

- Endpoint: `https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/` (Valve's documented replacement for the deprecated `store.steampowered.com/appreviews`). Parameters go in one `input_json` query parameter.
- Requests: English reviews, newest first, 100 per page, date range 1 Jan 2015 to 29 Nov 2022, 1.5 s pause between requests, waits and retries on HTTP 429.
- Checks the date window again on our side and drops reviews edited after the cutoff.
- Stops at `--max-per-app` reviews per game (default 1,500). Each run overwrites that game's file.
- Output: `data/raw/steam_<appid>.jsonl` with `review_id`, `appid`, `text`, `voted_up`, `timestamp_created`, `timestamp_updated`, `language`, `playtime_at_review_min`, `votes_up`, `received_for_free`.

```
python scripts/collect_steam_reviews.py                                  # 8 default games
python scripts/collect_steam_reviews.py --appids 620 --max-per-app 200   # small test
```

Default games: Portal 2 (620), Terraria (105600), Stardew Valley (413150), The Witcher 3 (292030), Hollow Knight (367520), Slay the Spire (646570), Civilization VI (289070), Hades (1145360).

### `clean_reviews.py`

Rules, applied in this order, each counted:

1. Empty text.
2. Same character repeated 10+ times (`aaaaaaaaaa`).
3. More than half of the visible characters are symbols (ASCII art, emoji walls).
4. Language tag is not English.
5. Fewer than 90% of letters are plain Latin letters (catches Cyrillic, Chinese etc. tagged as English).
6. Fewer than `--min-words` words (default 3).
7. Duplicate of an earlier review, ignoring case, spacing and punctuation.

Output in `data/clean/`: `reviews_clean.csv` (columns `review_id, appid, text, voted_up, word_count, playtime_at_review_min, votes_up, timestamp_created, label`; `label = 0` means human), `cleaning_report.json`, `dropped_examples.csv` (first 25 removed reviews per rule, useful as "noisy cases" in the report).

```
python scripts/clean_reviews.py
```

---

## 5. What has been done

| Step | State |
| --- | --- |
| Read the assignment, proposal and Kryštof's notebook; agreed a 10-step plan | Done |
| Repository with README, failure journal, scripts | Done |
| Collection script | Done; ran successfully on real Steam data |
| First collection: 8 games × 1,500 reviews | Done (12,000 reviews, 7,940 kept); now superseded |
| Cleaning script | Done |
| Extended collection: 12 games × 3,000 reviews | Done (36,000 reviews) |
| Cleaning of the extended collection | Done (24,296 kept) |
| Team added as collaborators | In progress |

A visual plan also exists as a Whiteboard in Eliška's Claude account: https://claude.ai/artifact/4uVDMMJrBunWXcHroX6aDd (private until she shares it).

---

## 6. Data so far

Current dataset: the extended run of 14 November 2026, 12 games × 3,000 reviews. Every game reached the 3,000 cap, so more is available if needed.

| | Count | Share of collected |
| --- | --- | --- |
| Collected | 36,000 | 100% |
| **Kept** | **24,296** | **67.5%** |
| Dropped: fewer than 3 words | 9,360 | 26.0% |
| Dropped: duplicates | 1,127 | 3.1% |
| Dropped: mostly symbols | 489 | 1.4% |
| Dropped: repeated characters | 352 | 1.0% |
| Dropped: non-English text | 228 | 0.6% |
| Dropped: empty | 148 | 0.4% |

Median length of kept reviews: 13 words.

For comparison, the first run (8 games × 1,500 = 12,000 reviews) kept 7,940 (66.2%), dropped 3,335 (27.8%) as too short, and had a median of 11 words. The proportions are similar in both runs.

### Games analysed

Reviews are collected per game by its Steam app ID (the number in `store.steampowered.com/app/<appid>/`). Each game contributed 3,000 collected reviews.

| # | Game | App ID | Genre | Kept after cleaning | Kept share |
| --- | --- | --- | --- | --- | --- |
| 1 | Portal 2 | 620 | Puzzle | 1,875 | 62.5% |
| 2 | Terraria | 105600 | Sandbox | 1,760 | 58.7% |
| 3 | Stardew Valley | 413150 | Farming sim | 1,993 | 66.4% |
| 4 | The Witcher 3: Wild Hunt | 292030 | RPG | 1,842 | 61.4% |
| 5 | Hollow Knight | 367520 | Platformer | 1,980 | 66.0% |
| 6 | Slay the Spire | 646570 | Card game | 2,114 | 70.5% |
| 7 | Civilization VI | 289070 | Strategy | 2,084 | 69.5% |
| 8 | Hades | 1145360 | Action | 2,160 | 72.0% |
| 9 | Cyberpunk 2077 | 1091500 | RPG | 2,219 | 74.0% |
| 10 | Battlefield 2042 | 1517290 | Shooter | 2,343 | 78.1% |
| 11 | Fallout 76 | 1151340 | Online RPG | 2,407 | 80.2% |
| 12 | PUBG: Battlegrounds | 578080 | Battle royale | 1,519 | 50.6% |
| | **Total** | | | **24,296** | **67.5%** |

Games 1–8 are the script's defaults: well-reviewed games from different genres. Games 9–12 were added because they are likely to have many negative reviews, which the first eight lack. All twelve IDs were checked against the Steam store pages by Eliška.

Observations to follow up:

- The kept share differs a lot by game: 50.6% for PUBG up to 80.2% for Fallout 76. The cleaning report does not break the drops down per game, so the cause is not confirmed; the likely one is that some games attract far more one- or two-word reviews. Worth one plot in the exploration step.
- The dataset is not balanced by game (1,519 to 2,407). Decide in step 4 whether to downsample to equal counts per game.

Command that produced this dataset:

```
python scripts/collect_steam_reviews.py --appids 620 105600 413150 292030 367520 646570 289070 1145360 1091500 1517290 1151340 578080 --max-per-app 3000
python scripts/clean_reviews.py
```

**Not yet checked (do this on the cleaned CSV):**

- **Date spread.** The script takes the newest reviews before the cutoff first, so the data may cluster in the last months before November 2022. Check `df.timestamp_created.agg(['min','max'])` and a histogram by month.
- **Share of positive reviews.** `df.voted_up.mean()`. If it is around 0.9, there are few negative reviews to match AI reviews against.
- **Read the dropped examples.** Open `dropped_examples.csv` and confirm each rule removes what it should, and that nothing useful is lost.

---

## 7. Open question blocking the next step: API access

Generating AI reviews from a script needs API keys. Chat subscriptions do not provide them:

- **Claude Max** does not include API access. API usage is billed separately through the Claude Console. One third-party article claims Max includes a monthly API credit; this is unconfirmed.
- **Google AI Pro (student plan)** covers the Gemini apps, not API requests. The **Gemini API has its own free tier** through a key from Google AI Studio, with no billing needed. Limits per model are shown only inside AI Studio. Free-tier requests may be used by Google to improve its products. One article says the free tier is not offered to EU users; unconfirmed.

**Two checks, about 10 minutes, for whoever has the accounts:**

1. Create a key in Google AI Studio. Note which models it offers, the daily request limit, and whether it works from Czechia.
2. Open the Claude Console and see whether there is API credit, or whether a small prepaid top-up is needed.

API keys go in a local `.env` file (already git-ignored). Never commit a key.

---

## 8. Failure journal entries so far

The journal must be honest and dated on the day things happened. Entries written so far (the fourth was proposed; check that it is in the file):

| Date | Tried, and why | How it failed | Instead |
| --- | --- | --- | --- |
| 2026-11-14 | Human reviews from existing public datasets (proposal). | Not allowed as the only source. | Own collection and cleaning. |
| 2026-11-14 | Copy Kryštof's notebook as closely as possible. | It reports accuracy only; this course also grades error analysis, journal and limits. | Reuse only the modelling skeleton. |
| 2026-11-14 | Google Maps as the human source. | API gives 5 reviews per place and forbids storing; scraping is against the terms; dates are vague. | Steam reviews. |
| 2026-11-14 | Keep reviews of any length. | 3,335 of 12,000 (28%) had under 3 words in the first run; 9,360 of 36,000 (26%) in the extended run. | Minimum of 3 words, reported as a limit. |

Add an entry every time something fails or a decision changes: failed training runs, abandoned hyperparameters, prompts that produced obviously artificial reviews, API limits hit.

---

## 9. What is left

Dates are a suggested schedule to reach the 26 November deadline.

### Step 3. Generate AI reviews (by about 19 Nov)

- One AI review per human review, matched on **game, thumbs up/down and word count**, so length and topic cannot give the class away.
- **Size decision needed.** There are 24,296 kept human reviews. Matching all of them means about 24,000 generated reviews (roughly 1,200 requests at 20 reviews each), which may exceed free-tier limits. A balanced subsample, for example 1,000 human reviews per game (12,000 human + 12,000 AI), is enough for these models and leaves the rest as a reserve.
- Use 2–3 different LLMs. Record `generator` and `prompt_style` for every review.
- **Keep one generator completely out of training** and use it as an extra test set. That measures generalization to an unseen LLM (the "distribution shift" the Model criteria ask about).
- Use several prompt styles (casual, angry, brief, detailed), otherwise the model learns one prompt's voice.
- The prompt should contain only the game name, the recommendation and a target length, **not the human review text**. That avoids sending scraped text to a third party and avoids paraphrase pairs.
- Ask for about 20 reviews per request, as JSON, to stay inside free-tier request limits.
- Strip giveaways before saving: "Here is a review:" preambles, surrounding quotation marks, markdown, numbering.
- Run the AI reviews through the same cleaning rules as the human ones, and log what gets removed.
- The script must be resumable (skip what is already generated), because rate limits will interrupt it.
- Known weakness to state in the report: the AI reviews come from our prompts, so the model detects "LLM output under our prompts", not all AI text.

### Step 4. Explore and split (19–20 Nov)

- Plots: class balance, length distribution per class, most distinctive words per class (the ratio plot from Kryštof's notebook works well here).
- Before any model, check the obvious giveaways: do the classes differ in average length, punctuation, capitalisation, typos, emoji? If a single feature such as "contains a typo" separates them, say so; it is a finding.
- Stratified train / validation / test split, with a validation set of at least a few hundred per class.
- Extra test sets: the held-out generator, and ideally a held-out game.

### Step 5. Train the models (20–23 Nov)

- Dummy classifier (majority class) as the floor.
- MLP with TF-IDF (bigrams), CNN, BiLSTM, DistilBERT, following Kryštof's notebook: baseline first, then a tuned version.
- Ablation: MLP with and without stopword and punctuation removal.
- Log every run (settings, result, date). Failed runs go into the failure journal.

### Step 6. Evaluate (23–24 Nov)

- Per-class precision, recall and F1, confusion matrices, not accuracy alone.
- False-positive rate on human reviews (a real reviewer flagged as AI is the costly error for a platform).
- Results by review length bucket, by thumbs up/down, by game, and by generator including the held-out one.

### Step 7. Error analysis (24 Nov)

- Pull concrete misclassified reviews for each model and explain why each failed.
- Look for patterns: very short reviews, humans who write formally, AI reviews prompted to be sloppy.
- Check whether the model is really detecting topic, length or formatting rather than authorship.

### Step 8. Write the package (24–26 Nov)

- `report.pdf` (3–5 pages) in the required order, with an example for every claim.
- `failure-journal.pdf` from `failure-journal.md`.
- `contributions.pdf`: each of the five mapped to a pillar, showing comparable depth.

### Step 9. Finish the repository (26 Nov)

- Update the README status table and add the repository link to the report's first page.
- Add a small anonymised sample to `data/sample/`, the metrics table and one or two analysed failure cases to `results/`.
- `git tag prefinal && git push origin prefinal`.
- Upload the package folder to the team's Teams folder before 23:59.

### Step 10. After submission

- Each member: feedback on three assigned projects by Mon 7 Dec.
- Slides by Tue 8 Dec. Prioritise: the comparison with one concrete failure example, one dead end from the journal, the limits. Keep data and output brief.
- Presentation Thu 10 Dec.

### Also to do

- **Consultation:** confirm with the teacher that Steam is an acceptable source and that "Model" is the right project type.
- **Split the work** among five people now, by pillar, and write it down for `contributions.pdf`. A possible split: data collection and cleaning; AI generation; classical models and ablation; DistilBERT and tuning; evaluation, error analysis and report assembly.

---

## 10. Limits and risks already known (material for the report's last section)

- **Domain:** game reviews only; no evidence the model works on Google Maps or e-shop reviews.
- **Time gap:** human reviews are from before November 2022, AI reviews from 2026. The model could partly learn "old vs new" language.
- **Sampling:** newest-first collection may cluster the human reviews in a short period; a handful of games.
- **Length floor:** reviews under 3 words are excluded; very short reviews are probably undetectable.
- **Generator dependence:** results hold for the LLMs and prompts we used. The held-out generator shows how far that goes.
- **Evasion:** an AI review that is lightly edited by a person, or prompted to imitate typos and slang, may pass.
- **Cost of errors:** a false positive accuses a real customer; a platform would need a human check before acting.
- **Labels:** "human" assumes nobody posted machine-generated text before November 2022 (bots and templates existed).
- **Gemini free tier:** requests may be used by Google; we send only game names and instructions, no scraped text.

---

## 11. Notes for an LLM assistant picking this up

- The theme, the teacher's rules and the deadlines in section 2 are fixed. Everything in the original proposal is a draft and may be changed if it improves the result.
- The students must be able to explain every line. Prefer simple, readable code with comments on the reasons, over clever code.
- Do not invent results. Numbers in this document come from the team's real runs on 14 November; anything after that must come from the team's own runs.
- When something fails or a decision changes, propose a failure-journal entry with the date and the concrete number or example.
- Never put raw scraped text or API keys into the repository.
