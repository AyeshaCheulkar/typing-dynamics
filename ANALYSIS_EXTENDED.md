# Extended Analysis (no new data — existing 22 sessions)

Three additions that deepen the study using only the data already collected. Target
throughout = **self-perceived writing effort (1–5)**; no claim about mental effort,
cognitive load, stress, or any psychological state. Exploratory at n=22.

## 1. Richer keystroke features (`extra_features.py` → `extra_features.csv`)

Re-processing the captured keystrokes yields writing-process constructs beyond the
core features:

| Feature | Median (valid) | ρ with effort | p |
|---------|----------------|---------------|---|
| Initial planning pause (s) | 3.0 | −0.02 | .94 |
| Within-word pauses (%) | 12.0 | +0.12 | .59 |
| Between-word pauses (%) | 57.2 | +0.01 | .96 |
| Between-sentence pauses (%) | 1.1 | −0.19 | .40 |
| Production bursts (count) | 3 | +0.10 | .67 |
| Revision bursts (count) | 6 | −0.15 | .51 |
| Mean production-burst length (chars) | 19.1 | −0.18 | .41 |
| Mean revision distance (chars) | 1.9 | −0.15 | .51 |

**Descriptive insight (even where not predictive):** most long pauses fall
**between words** (57%), few within words (12%) or between sentences (1%); edits sit
**~2 characters from the writing frontier** (people fix recent typos rather than
revise far back). None correlate significantly with effort at n=22.

## 2. Task difficulty: Easy vs Moderate (`difficulty_analysis.py`)

The sessions are already labelled Easy (n=15) / Moderate (n=7). Mann-Whitney U:

| Measure | Easy | Moderate | p |
|---------|------|----------|---|
| **Self-rated effort** | **2.40** | **3.29** | .151 |
| Writing time (s) | 234 | 303 | .210 |
| Share of time paused | 0.56 | 0.54 | .73 |
| Long pauses /100 | 2.17 | 1.65 | .40 |
| Revisions /100 | 3.65 | 3.31 | 1.0 |
| Typing speed | 2.13 | 2.15 | .89 |

**Moderate tasks are rated ~0.9 points higher in effort and take longer to write** —
the expected direction (a face-validity check that the effort rating behaves
sensibly). Figure: `difficulty_analysis.png`.

## 3. Participant-aware modelling (`mixed_effects.py`)

Because several participants did more than one session, a **participant-clustered
regression** (and a random-intercept mixed model) is more appropriate than pooled
correlations.

**M1 — effort ~ difficulty (+ participant):**
- Moderate vs Easy: **coef = +0.89, p = 0.063** (participant-clustered); random-
  intercept variance 0.52. → Perceived difficulty is the **strongest, nearly-
  significant** predictor of self-rated effort in the study.

**M2 — effort ~ pausing + speed + revisions (standardised, + participant):**
- Pausing **+0.93 (p=0.16)**, Speed +0.75 (p=0.29), Revisions +0.07 (p=0.44). →
  Pausing is the strongest behavioural predictor, consistent with the correlation
  analysis, but not significant at n=22.

## What this adds to the dissertation

- **A near-significant result** (task difficulty → self-rated effort, p=0.063) that
  validates the effort measure and gives the study a positive, defensible finding.
- **A more rigorous method** (clustered / mixed-effects) that correctly handles
  repeated sessions.
- **Deeper, theory-grounded features** and descriptive insights about *where* pauses
  and edits occur — richer explanation without any new data.
- All consistent with the headline: promising, directionally-sensible signal that is
  sample-size limited, not method-limited.
