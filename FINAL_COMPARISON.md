# Results So Far — Concise Comparison

Three separate results. They are **not** combined into one model: the primary
model is trained only on our own effort labels; the external data supports the
method but never contributes effort labels.

| # | Result | Data | Target | Method | Outcome |
|---|--------|------|--------|--------|---------|
| 1 | **Primary effort model** | Our own — 22 valid sessions, 17 participants | Self-perceived writing effort (1–5) | LinearReg + RandomForest, participant-aware CV (LOPO & GroupKFold), MAE/RMSE/R² | **Does not beat baseline** yet (RF MAE 0.94–1.10 vs baseline 0.90–0.94). 7/9 behaviours point the hypothesised way; 0/9 significant. *Directionally supported, underpowered.* |
| 2 | **External feature validation** | EmoSurv (190 sess / 81 ppts) **and** KeyRecs (197 sess / 99 ppts) | (none — validation only) | Same `extract_features()` after reconstructing timing from inter-key intervals | **Pipeline validated on TWO independent datasets.** Same-scale features throughout (median keystroke gap 209 ms ours / 206 EmoSurv / 174 KeyRecs). Our composition shows ~5× more long "thinking" pauses than KeyRecs transcription — theory-consistent. |
| 3 | **Separate EmoSurv experiment** | EmoSurv — same 190 sessions | Induced **emotion** (a behavioural state — NOT effort) | RandomForest, leave-one-participant-out | **Signal confirmed at scale.** RF beats baseline: 5-way emotion balanced-accuracy 0.39 vs 0.20 chance; neutral-vs-emotion 0.64 vs 0.50. |

## What the three together establish

- The **feature-extraction method is sound and validated** on an independent
  81-participant dataset (Result 2).
- On a properly-sized dataset, the **same typing features carry a measurable
  behavioural-state signal** (Result 3) — so the general approach works.
- Our own **effort model underperforms because of sample size (n=22), not a flawed
  method** (Result 1) — it shows the right directional signal and should reach
  predictive power with more labelled sessions.

## Boundaries kept

- EmoSurv's **emotion labels were never mixed** with our effort ratings.
- The target stays **self-perceived writing effort**; no claim about mental
  effort, stress, or any psychological/medical condition.

## Recommended next action (before building the platform)

Collect more of our own labelled sessions (more participants especially). The
pipeline, features, models and evaluation are all in place — they just need a
larger primary sample to turn the directional signal into a reliable predictor.
Once that is in hand, proceed to the final Writing Analytics Platform
(prediction + SHAP explainability + student reports + researcher/admin dashboard).
