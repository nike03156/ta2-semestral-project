# Failure journal

Running list, newest entry at the bottom. Add an entry the same day something fails or a decision changes.
Pattern: **We tried X because Y, but it failed because Z, so we switched to W.**

| Date | What we tried and why | How it failed / why we dropped it | What we did instead |
| --- | --- | --- | --- |
| 2026-11-14 | Proposal plan: take the human reviews from existing public review datasets, because they are free and large. | Not allowed as the only source: the course rules require our own collection and cleaning, not a ready-made clean dataset. | We collect the human reviews ourselves with our own script and do our own cleaning. |
| 2026-11-14 | Plan to copy Kryštof's SST-2 notebook as closely as possible, because the four architectures already work there. | That project reports test accuracy only. This course also grades error analysis on concrete examples, a failure journal and limits, which the notebook does not have. | We reuse only its modelling skeleton (MLP, CNN, BiLSTM, DistilBERT, baseline vs tuned) and add our own evaluation and error analysis. |
| 2026-11-14 | Considered Google Maps reviews as the human source, because the proposal names Google Maps and e-shops as where fake reviews appear. | The official Places API returns at most 5 reviews per place and forbids storing them; scraping the website is against Google's terms; review dates are shown only as "3 years ago", so the pre-ChatGPT cutoff cannot be checked exactly. | Steam reviews: a documented public endpoint with exact timestamps and a date filter. Cost: game domain only, thumbs up/down instead of stars. |
|  |  |  |  |

## Entry checklist

- Date it on the day it happened, and say who ran it.
- Give the number or example that showed the failure (accuracy, a misclassified review, an error message).
- Link the commit or notebook cell if there is one.
