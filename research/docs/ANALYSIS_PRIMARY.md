# Final Analysis — Primary Data (Self-Perceived Writing Effort)

**Target:** the participant's own 1–5 rating of *self-perceived writing effort*.
No claim is made about mental effort, cognitive load, stress, or any psychological
or medical state.

**Dataset:** 22 behaviourally-valid sessions, 17 participants. Effort ratings
{1:3, 2:7, 3:8, 4:2, 5:2}, mean 2.68. No new sessions were available, so the
sample could not be grown.

**Rigour:** everything is participant-aware — cross-validation leaves out whole
participants, and every 95% confidence interval is bootstrapped by resampling
*participants* (2000 resamples), so repeated sessions from one person don't fake
precision. Nothing was tuned to look better.

## Part A — Relationship of effort to typing behaviour (Spearman ρ, 95% CI)

At n=22 a correlation needs **|ρ| ≥ 0.42** to reach p<0.05.

| Behaviour | Hypothesis | ρ | 95% CI | Direction ok? | Significant? |
|-----------|-----------|----|--------|---------------|--------------|
| Share of time paused | more | +0.23 | [−0.30, 0.68] | ✅ | no |
| Typing-rhythm variability | more | +0.16 | [−0.41, 0.63] | ✅ | no |
| Average keystroke gap | longer | +0.15 | [−0.37, 0.61] | ✅ | no |
| Long-pause frequency | more | +0.10 | [−0.40, 0.53] | ✅ | no |
| Longest pause | longer | +0.08 | [−0.46, 0.55] | ✅ | no |
| Revision activity | more | +0.03 | [−0.39, 0.44] | ✅ | no |
| Writing time | longer | −0.02 | [−0.46, 0.47] | ✖ (≈0) | no |
| Backspace/delete activity | more | −0.03 | [−0.44, 0.40] | ✖ (≈0) | no |
| Typing speed | slower | −0.07 | [−0.54, 0.43] | ✅ | no |

- **7 of 9 behaviours point the hypothesised way**; the two that don't have ρ≈0
  (noise, not real reversals).
- **0 of 9 are significant, and every 95% CI includes zero** — no relationship is
  statistically resolved at this sample size (and 9 tests add multiple-comparison
  risk).

## Part B — Predicting the 1–5 rating (Leave-One-Participant-Out, 95% CI)

| Model | MAE [95% CI] | RMSE [95% CI] | R² |
|-------|--------------|----------------|-----|
| **Baseline (predict mean)** | **0.94 [0.65, 1.24]** | 1.17 [0.79, 1.45] | −0.12 |
| Linear Regression | 1.99 [1.42, 2.63] | 2.49 [1.73, 3.09] | −4.08 |
| Random Forest | 1.10 [0.72, 1.50] | 1.44 [0.96, 1.82] | −0.70 |

**Does either model beat the baseline?** (paired per-participant MAE, Wilcoxon)
- Linear Regression: median difference **+0.90 worse**, p = 0.000 → significantly worse.
- Random Forest: median difference **+0.14 worse**, p = 0.045 → significantly worse.

**Is R² better than shuffled-label chance?** (permutation test)
- Linear Regression: observed R² = −4.08, **p = 0.850**.
- Random Forest: observed R² = −0.70, **p = 0.990**.

Robustness (GroupKFold, 5 folds) gives the same ordering; RF ≈ baseline, LR worse.

## Hypothesis verdict

**Directionally supported, statistically unconfirmed.** The behaviours line up with
the hypothesis in direction (7/9), and the model's most-used features are the
pause/rhythm ones — but with 22 sessions:
- every correlation CI spans zero,
- neither model beats "just predict the average" (both are significantly *worse*),
- and both R² values are indistinguishable from chance.

**This is a limitation of sample size, not a refutation of the method** — the same
feature pipeline carries a measurable signal on the larger external datasets
(`EXTERNAL_RESULTS.md`). More labelled participant sessions are the prerequisite
before the effort predictor can be reliable.

Figure: `analysis_primary.png` (correlations with CIs; model error with CIs).
