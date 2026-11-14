# Failure journal

Running list, newest entry at the bottom. Add an entry the same day something fails or a decision changes.
Pattern: **We tried X because Y, but it failed because Z, so we switched to W.**

| Date | What we tried and why | How it failed / why we dropped it | What we did instead |
| --- | --- | --- | --- |
| 2026-11-14 | Proposal plan: take the human reviews from existing public review datasets, because they are free and large. | Not allowed as the only source: the course rules require our own collection and cleaning, not a ready-made clean dataset. | We collect the human reviews ourselves with our own script and do our own cleaning. |
| 2026-11-14 | Plan to copy Kryštof's SST-2 notebook as closely as possible, because the four architectures already work there. | That project reports test accuracy only. This course also grades error analysis on concrete examples, a failure journal and limits, which the notebook does not have. | We reuse only its modelling skeleton (MLP, CNN, BiLSTM, DistilBERT, baseline vs tuned) and add our own evaluation and error analysis. |
| 2026-11-14 | Considered Google Maps reviews as the human source, because the proposal names Google Maps and e-shops as where fake reviews appear. | The official Places API returns at most 5 reviews per place and forbids storing them; scraping the website is against Google's terms; review dates are shown only as "3 years ago", so the pre-ChatGPT cutoff cannot be checked exactly. | Steam reviews: a documented public endpoint with exact timestamps and a date filter. Cost: game domain only, thumbs up/down instead of stars. |
| 2026-11-14 | Planned to call Steam's `store.steampowered.com/appreviews` address, because most scraping tutorials use it. | Valve's documentation marks it as deprecated, with no shutdown date, so the script could stop working before the final defense. | The collection script uses the replacement, `IUserReviewsService/GetAppReviews`, which also has a date-range filter. |
| 2026-11-14 | First version of the cleaning script checked language and length before the symbol rules. | On a 10-review test file the removals were labelled wrongly: an ASCII-art review was counted as "non-English" and the repeated-character rule never fired, so the per-rule counts would have been misleading in the report. | Reordered the rules (repeated characters and symbols first, then language, then length, then duplicates) and re-tested before running on real data. |
| 2026-11-14 | Planned to keep reviews of any length, because the proposal focuses on short reviews. | After cleaning the first collection, 3,335 of 12,000 reviews (28%) had under 3 words, e.g. "good game": too little text for any classifier to use. The extended collection confirmed it: 9,360 of 36,000 (26%). | Minimum of 3 words; we report this as a limit of the detector. |
| 2026-11-14 | First collection: 8 well-reviewed games × 1,500 reviews (12,000), chosen for genre variety. | Only 7,940 reviews were left after cleaning, and all eight games are highly rated, so we expected too few negative reviews (we did not measure the share before deciding). | Extended to 12 games × 3,000 reviews (36,000 collected, 24,296 kept), adding Cyberpunk 2077, Battlefield 2042, Fallout 76 and PUBG as games with many negative reviews. |
| 2026-11-14 | Planned to generate the AI reviews with the team's Claude Max and Google AI Pro (student) subscriptions. | Both cover the chat apps only. Calling the models from a script needs API access, which is separate: Claude API through the Claude Console, Gemini API through a Google AI Studio key. | Open: checking the Gemini API free tier and Claude Console credit before writing the generation script. |
|  |  |  |  |

## Entry checklist

- Date it on the day it happened, and say who ran it.
- Give the number or example that showed the failure (accuracy, a misclassified review, an error message).
- Link the commit or notebook cell if there is one.
