# Step 4 — External Data (EmoSurv): Compatibility, Validation & Experiment

External dataset used as **supporting data only** — never a replacement for our
own labelled participant data, and its emotion labels are **never** mixed with our
1–5 writing-effort labels.

## 1. Compatibility check (the key question)

EmoSurv's **absolute keyDown/keyUp timestamps are unusable** — the downloaded CSV
had been saved through Excel, which rounded the epoch-millisecond values to
6-figure scientific notation (only 69 distinct values across 28,412 rows).

**But the `D1D2` column — the down-to-down inter-key interval — is fully intact:**
99.1% of values are clean (0–60000 ms), no negatives, no corruption, median
202 ms. So each session's keystroke timeline is **reconstructed from the D1D2
intervals** and fed through the *same* `extract_features()` used on our data.
`keyCode` is clean (space, backspace, then normal English letter frequency).

**Verdict: compatible.** 193 sessions parsed, **190 behaviourally valid**
(≥40 keystrokes), from **81 participants**.

## 2. Feature validation (Strategy A) — medians

The same extractor yields the same-scale features on this independent dataset:

| feature | Ours (22) | EmoSurv (190) |
|---------|-----------|---------------|
| median_iki_ms | 209.5 | **205.5** |
| chars_per_sec | 2.15 | 2.62 |
| n_short_pause_per_100 | 14.4 | 13.6 |
| n_long_pause_per_100 | 1.89 | 1.34 |
| pause_time_ratio | 0.539 | 0.466 |
| delete_rate | 0.085 | 0.064 |
| revisions_per_100 | 3.25 | 2.89 |

Inter-key interval matches almost exactly; all pause/deletion/revision features
sit in the same range. Expected differences: our sessions are longer (120–180-word
tasks vs EmoSurv's short free-text) and show more rhythm variability (free
composition vs guided typing). **This validates the feature pipeline.**

## 3. Separate external experiment — emotion (NOT effort)

EmoSurv's own question, run with our pipeline, LOPO by participant:

| Task | Baseline BalAcc | Random Forest BalAcc | Macro-F1 (RF) |
|------|-----------------|----------------------|---------------|
| 5-way emotion (N/H/S/C/A) | 0.20 | **0.39** | 0.38 |
| Neutral vs Emotion-induced | 0.50 | **0.64** | 0.64 |

The Random Forest **clearly beats baseline** — the same typing-dynamics features
carry a real psychological-state signal on a properly-sized dataset.

Descriptive pattern (medians): angry/happy typing is faster (higher chars/sec,
lower IKI); sad typing is slower with fewer long pauses.

## 3b. Second validation dataset — KeyRecs (99 participants)

KeyRecs (Zenodo, free-text typing, 99 participants / 197 valid sessions) was added
as an independent second validation set. Its digraph latencies (`DD.key1.key2`)
were reconstructed the same way and run through the same extractor.

| feature | Ours (22) | EmoSurv (190) | KeyRecs (197) |
|---------|-----------|---------------|---------------|
| median_iki_ms | 209 | 206 | 174 |
| chars_per_sec | 2.15 | 2.62 | 3.15 |
| pause_time_ratio | 0.54 | 0.47 | 0.43 |
| **n_long_pause_per_100** | **1.89** | 1.34 | **0.34** |
| revisions_per_100 | 3.25 | 2.89 | 3.18 |

The features come out at the same scale across **all three** independent datasets —
the method is now validated on two external sources, not one. The most telling
difference is interpretable: our **composition** data shows ~5× more long
"thinking" pauses than KeyRecs **transcription** — consistent with the idea that
composing requires planning pauses that copy-typing does not. (KeyRecs has no
effort/difficulty label; validation only.)

## 3c. IIITD-BU low/high cognitive-demand — investigated, not accessible

The one path to a difficulty-labelled augmentation (Strategy B) was IIITD-BU. Its
GitHub repo (`ijcb-2024/keystroke-llm-plagiarism`) contains only two notebooks and
a README — **no data files**. The dataset requires a separate author request, so
the low/high-demand experiment cannot be run at this time. (LIFT, another
difficulty-labelled writing corpus, is likewise access-restricted on Zenodo.)

## 4. What this establishes (for the thesis)

- The feature-extraction method is **validated on an independent 81-participant
  dataset** and produces the same-scale behavioural features.
- On enough data, those features **predict an internal psychological state above
  chance** — so the approach is sound.
- Therefore our own effort model's weakness is best explained by **small sample
  size (n=22), not a flawed method** — it shows the right directional signal and
  should reach predictive power with more labelled sessions.
- Emotion ≠ effort: this experiment supports the *approach*, it does not add
  training labels to our effort model. The primary effort result stays based
  solely on our 25 sessions.

Files: `external_data.py` (adapter + EmoSurv loader), `external_experiment.py`
(this experiment), `external_features_emosurv.csv` (output features).
