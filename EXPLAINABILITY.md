# Stage B — Explainability (SHAP)

**What this is.** SHAP assigns each typing behaviour a signed contribution to a
single session's predicted effort, so we can say *why* the model produced a given
estimate. Contributions add up from the model's baseline (mean effort ≈ 2.68) to
the final prediction.

**Honest framing (important).** The effort model does **not** beat a mean baseline
on this 22-session pilot (see `ANALYSIS_PRIMARY.md`). Therefore SHAP here explains
**what the model does**, not a validated causal driver of self-perceived effort.
Any predicted-effort number is **experimental** and must be shown as such.

## Global importance — which behaviours the model leans on

SHAP mean |impact| on predicted effort (Random Forest, all 22 sessions):

| Rank | Behaviour | Mean \|SHAP\| |
|------|-----------|--------------|
| 1 | Writing time | 0.196 |
| 2 | Share of time paused | 0.167 |
| 3 | Longest pause | 0.082 |
| 4 | Typing-rhythm variability | 0.073 |
| 5 | Average keystroke gap | 0.072 |
| 6 | Backspace/delete activity | 0.053 |
| 7 | Revision activity | 0.045 |
| 8 | Typing speed | 0.029 |
| 9 | Long-pause frequency | 0.021 |

**Reading it:** the model relies most on **writing time and pausing behaviour**,
then rhythm — the same pause/time signals that led the correlation analysis. This
is internally consistent and theory-aligned (harder writing → more pausing / more
time), even though the effect is too weak at n=22 to predict reliably. Figure:
`shap_summary.png`.

## Linear Regression cross-check (with a caveat)

Standardised LR coefficients rank differently (rhythm variability +3.35, longest
pause −2.55, …) and take large, sign-flipping values. This is the expected
**instability of a linear model on 22 correlated features** — it overfits. The
SHAP-on-Random-Forest picture is the more trustworthy explanation; the LR
coefficients are reported only as a cross-check and should not be over-read.

## Example per-session explanation

Participant M01, self-rated effort **5**, model predicted **3.9** (from baseline
2.68). Top drivers that pushed the estimate **up**:
- Share of time paused (+0.46)
- Longest pause (+0.21)
- Typing-rhythm variability (+0.20)
- Writing time (+0.15)

All four point the theory-consistent way: this writer paused more, paused longer,
typed less evenly and took longer — and the model read that as higher effort.

## How the prototype platform will use this

`explain.py` exposes `explain_session(artifact, features)` returning the predicted
effort, ranked contributions, and plain-language sentences. The future
`prototype_platform/` will call this to generate each writer's explainable report —
**foregrounding the measured behaviour and recommendations**, and labelling the
predicted-effort estimate as experimental. It loads the shared `effort_model.pkl`
and `features.py`; it does not touch the Stage-1 data-collection app or database.

Files: `train_model.py` (fits + saves `effort_model.pkl`), `explain.py`
(SHAP global + per-session), `shap_summary.png`.
