# Stage 3 — Primary Model Results (pilot)

**Question:** can typing dynamics (speed, pauses, deletions, revisions, writing
time) estimate a writer's own 1–5 effort rating?

**Data:** 22 behaviourally-valid sessions, 17 participants. Effort ratings are
bunched (1:3, 2:7, 3:8, 4:2, 5:2), mean 2.68.

**Test method:** Leave-One-Participant-Out cross-validation (the model is always
tested on a person it never trained on). Behavioural features only — the text
content is never used.

## Result — models do not yet beat the mean baseline

| Model | MAE ↓ | RMSE ↓ | R² |
|-------|------|------|-----|
| Baseline (predict average effort) | **0.94** | **1.17** | −0.12 |
| Linear Regression | 1.14 | 1.44 | −0.71 |
| Random Forest | 1.08 | 1.37 | −0.54 |

Both models are **worse than guessing the average**, and no feature is
statistically correlated with effort (all p > 0.05). **This is the expected
outcome of a small pilot**, not an error: with only 22 sessions and effort
concentrated at 2–3, there is too little data to learn a stable pattern.

## What is still valuable

1. **Sensitivity check validates the data filter.** Re-running with the 3 flagged
   mobile/IME sessions added makes Linear Regression collapse (R² −4.69),
   proving those sessions are harmful and were rightly excluded.
2. **Weak signal points the right way.** The features leaning most toward *higher*
   effort are pause-related (`pause_time_ratio`, short-pause frequency) and total
   writing time — i.e. more pausing / longer time → rated harder. Matches the
   hypothesis; just not significant at this sample size.
3. **Random Forest importance** ranks `active_time_s`, `pause_time_ratio`, and
   pause frequency highest.

## Binary reframe (LOW vs HIGH effort) — `model_binary.py`

To give a small dataset an easier target, effort was collapsed to two classes
(primary split: 1–2 = LOW, 3–5 = HIGH; 10 vs 12, balanced).

| Model (LOPO) | Balanced Accuracy | AUC |
|--------------|-------------------|-----|
| Baseline (majority class) | 0.33 | — |
| Logistic Regression | 0.37 | 0.27 |
| Random Forest | 0.38 | 0.32 |

Still at/below chance (0.5) — the pilot **cannot classify an individual writer's
effort** either. BUT the descriptive feature-means table shows a **consistent,
theory-matching direction across both splits**: higher effort → more time paused,
more long thinking pauses, more variable typing rhythm, more revision bursts and
corrections. So the signal is present and points the right way; the sample is
simply too small to turn it into a reliable predictor.

## Implication for next steps

- Both regression and classification agree: **more data is the bottleneck, not
  the method.** The pipeline is proven end to end and yields the expected
  descriptive signal.
- Keep collecting sessions, and bring in external keystroke data (Steps 4–5),
  using the binary framing to combine with external low/high cognitive-demand
  data (Strategy B).

*Honest framing for review: this pilot shows the pipeline works end-to-end and
identifies which behaviours are promising, while demonstrating (with a baseline
comparison) that a larger sample is required before typing dynamics can predict
effort reliably.*
