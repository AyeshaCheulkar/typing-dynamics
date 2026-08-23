# Writing Analytics Platform — Prototype Design (Stage C)

**Status:** DESIGN ONLY. No platform code is written yet. Nothing here modifies the
Stage-1 data-collection system. Build begins only after this document is approved.

---

## 0. Guiding principles (non-negotiable)

1. **Three distinct concepts, never conflated** (see §12):
   - **Measured behaviour** — objective facts computed from keystrokes (reliable).
   - **Self-rated writing effort** — the participant's own 1–5 rating (the label).
   - **Experimental estimated writing effort** — the model's output (**unreliable at
     the current sample size**; always labelled *experimental*).
2. **No overclaiming.** The platform never states or implies it measures mental
   effort, cognitive load, stress, intelligence, emotion, or any psychological or
   medical state. Approved wording: *"self-rated writing effort"*,
   *"experimental estimated writing effort"*, *"writing-process behaviour"*.
3. **Complete separation from Stage 1.** The existing `app.py`, `db.py`, `data.db`,
   `templates/`, `static/` are the live research data-collection system and are
   **read-only** for this project — the prototype never imports, writes, or alters
   them. It has its own app, its own database file, and its own front-end.
4. **Reuse, don't duplicate, the science.** Feature extraction (`features.py`) and
   the trained model (`effort_model.pkl`) are the single source of truth and are
   imported/loaded read-only.
5. **Recommendations are tied to observed behaviour, never to the effort score**
   (see §6). No generic advice (e.g. "read books") ever appears.

---

## 1. Participant writing flow

```
 Consent + code        Writing task            Self-rating           Result
 ┌───────────┐   →    ┌─────────────┐    →   ┌────────────┐   →   ┌──────────────┐
 │ enter a   │        │ prompt +    │        │ 1–5 "how   │       │ explainable  │
 │ participant│       │ editor;     │        │ much effort│       │ report page  │
 │ code;     │        │ capture.js  │        │ did this   │       │ (/report/ID) │
 │ pick task │        │ logs keys   │        │ take you?" │       │              │
 └───────────┘        └─────────────┘        └────────────┘       └──────────────┘
```

Steps:
1. **Landing / consent.** Short consent + purpose statement (research prototype;
   no diagnosis). Participant enters a **participant code** (same normalisation
   rule as Stage 1: strip spaces, upper-case) and picks a writing task (Easy /
   Moderate, reusing the Stage-1 prompt pools by value — copied into the prototype,
   not imported from the running app).
2. **Writing page.** A plain textarea editor. `capture.js` (the prototype's own
   logger) records every `keydown`/`keyup`, paste attempts, timestamps (ms since
   start), and caret position — the same event shape `features.py` expects.
3. **Self-rating.** On finishing, the participant answers the 1–5 self-rated
   writing-effort question. This is stored as their own label and is **kept
   visually and semantically separate** from any model output.
4. **Submit → process → report.** The server stores the session, computes
   behavioural features, produces the experimental estimate + SHAP explanation +
   behaviour-tied recommendations, and redirects to the report.

The prototype's writing flow mirrors Stage 1 functionally but runs on its **own**
front-end and backend so the research collection app is untouched.

---

## 2. Behavioural features calculated

Computed by the shared **`features.py` `extract_features()`** — identical to the
research analysis, so the numbers a participant sees are the same ones the study
used. Grouped for the report:

| Group | Features (from `features.py`) |
|-------|-------------------------------|
| Typing speed | `chars_per_sec`, `keys_per_sec`, `median_iki_ms`, `mean_iki_ms` |
| Pauses | `n_short_pause_per_100`, `n_long_pause_per_100`, `pause_time_ratio`, `max_pause_ms` |
| Deletions | `n_delete`, `delete_rate` |
| Revisions | `n_revision_bursts`, `revisions_per_100` |
| Writing time | `active_time_s` |
| Rhythm | `std_iki_ms` |
| Volume | `char_count`, `word_count` |
| Data quality | `unid_rate`, `behavioural_valid` |

The **9 model features** (order fixed by `effort_model.pkl`): `chars_per_sec`,
`mean_iki_ms`, `max_pause_ms`, `n_long_pause_per_100`, `pause_time_ratio`,
`delete_rate`, `revisions_per_100`, `active_time_s`, `std_iki_ms`.

If `behavioural_valid == 0` (too few keystrokes, or high `unid_rate` from a
mobile/IME keyboard), the report shows the measured behaviour it can, and
**suppresses the experimental estimate** with a note that the keystroke capture was
insufficient — rather than showing a misleading number.

---

## 3. How the experimental effort estimate is generated

1. On startup, the prototype loads **`effort_model.pkl`** once (the Random Forest,
   the feature list, the training data for context, and the baseline mean effort).
2. For a submitted session: build the 9-feature vector (in the artifact's feature
   order) from `extract_features()`.
3. `rf.predict(x)` → clip to the valid 1–5 range → **experimental estimated writing
   effort**.
4. It is always presented:
   - **labelled "experimental"**, with a one-line caveat that on the current pilot
     the model does not outperform a simple average and the number is indicative
     only;
   - **next to, never replacing,** the participant's own self-rating;
   - optionally as a coarse band (Lower / Around average / Higher) in addition to
     the number, because a band is more honest about the model's precision.
5. The training baseline (mean self-rated effort ≈ 2.68) is shown as the reference
   the estimate is measured against.

No attempt is made at runtime to "improve" the estimate (no retraining, no tuning).

---

## 4. How the SHAP explanation is presented

Uses the shared `explain.py` `explain_session()` (SHAP `TreeExplainer` over the
loaded RF):
- A compact **horizontal contribution chart**: the top behaviours that pushed this
  session's estimate **up** (one colour) or **down** (another), from the model
  baseline to the estimate.
- **Plain-language sentences**, e.g. *"Share of time paused raised the experimental
  estimate (+0.46)."*
- A caption stating this explains **what the model did**, not a proven cause of
  effort.

The explainer is built once at startup and cached; per-session SHAP on 9 features
is instant.

---

## 5. The participant report (`/report/<id>`)

Layout, top to bottom:

- **A. Session summary** — task, word count, active writing time.
- **B. How you wrote (measured behaviour)** — speed, pauses (count / longest / %
  time paused), deletions & revisions, writing time, rhythm. Each shown with a
  neutral descriptive comparison to the **typical range** (percentiles from the
  training distribution stored in the artifact), e.g. "within the typical range" /
  "higher than most sessions". **Facts, no judgement.**
- **C. Your self-rated writing effort** — the 1–5 the participant gave, clearly
  framed as *"what you told us."*
- **D. Experimental estimated writing effort** — the model output, clearly labelled
  *experimental*, with the uncertainty caveat and the SHAP "why" (§4).
- **E. Writing-process suggestions** — behaviour-tied only (§6); shown only if a
  behaviour trigger fires.
- **F. Disclaimer footer** — research prototype; does not measure mental effort,
  stress, intelligence, or any psychological state.

Colour/visual language keeps B (facts), C (self-report), and D (experimental)
visually distinct so they are never read as the same thing.

---

## 6. Writing-process recommendations (behaviour-tied)

**Hard rules:**
- A recommendation is triggered **only** by an observed behaviour crossing a
  threshold **relative to the training distribution** (percentiles from the
  artifact's `X_train`). It is **never** triggered by the effort score (self-rated
  or predicted).
- **No generic advice** ("read more", "read books", "study harder") — every
  suggestion names the specific behaviour it responds to.
- At most 2–3 suggestions; if nothing triggers, a single neutral message.

**Rule table (initial):**

| Observed behaviour (vs training distribution) | Suggestion (behaviour-specific) |
|-----------------------------------------------|---------------------------------|
| `revisions_per_100` **or** `delete_rate` in top quartile | "You revised a lot while writing. Jotting your main points before drafting can reduce how much you rewrite." |
| `n_long_pause_per_100` **or** `pause_time_ratio` in top quartile | "You paused often for long stretches. A brief outline before you start can move some of that planning up front." |
| `chars_per_sec` in bottom quartile (slow) | "Your typing pace was on the slower side. Short typing-fluency practice can help you get ideas down faster." *(framed as fluency, never ability/intelligence)* |
| `active_time_s` in top quartile **and** low `word_count` | "This session took a while for the amount written. Timeboxing a first draft, then editing, can help." |
| No trigger fires | "Your writing-process measures are within the typical range — nothing stands out to change." |

Thresholds (quartiles) are computed from the training feature distribution and are
documented in code; they are **descriptive of this dataset**, not clinical cut-offs.

---

## 7. Researcher / admin dashboard (`/admin`, password-protected, separate auth)

- **Overview cards:** total sessions, participants, self-rated effort distribution,
  mean self-rated vs mean experimental estimate, count with insufficient capture.
- **Session table:** participant code, task, self-rated effort, experimental
  estimate, key behavioural features, data-quality flags. Filter/sort.
- **Analytics:** feature distributions; self-rated-effort-vs-behaviour scatter
  plots; self-rated vs experimental-estimate scatter (to show, honestly, how weakly
  they align).
- **Model results panel (static, from Stage A/B):** MAE / RMSE / R² with 95% CIs,
  the Wilcoxon and permutation outcomes, and the `shap_summary.png` global-importance
  image — so a reviewer sees the model's real (limited) performance in context.
- **Export:** the prototype's own CSV export of its sessions/features.

The dashboard reads only the **prototype's** database.

---

## 8. Session history & student-level trends

- **Per-participant view** keyed by participant code: all their sessions over time.
- **Trends across sessions:** small line charts of behavioural features (speed,
  pausing, revision, writing time) and of self-rated effort and experimental
  estimate — plotted on **separate tracks** so measured behaviour, self-report, and
  experimental estimate are never merged into one line.
- Framed descriptively ("how this writer's process varied across sessions"), with
  the same experimental caveat on the estimate track.
- Because participants may do repeated sessions, the view groups by participant
  (consistent with the study's participant-level analysis).

---

## 9. Database / storage architecture (prototype-only)

A **separate SQLite file `prototype_platform/prototype.db`** — never `data.db`.
Own tables (prefixed to avoid any ambiguity):

`pt_sessions`
| column | meaning |
|--------|---------|
| id | PK |
| participant_code | normalised code |
| task_id | chosen task |
| started_at / ended_at / duration_ms | timing |
| final_text | submitted text |
| char_count / word_count | volume |
| self_rated_effort | 1–5 (the participant's own label) |
| predicted_effort | experimental estimate (nullable if capture insufficient) |
| features_json | the full feature dict (for dashboard without recompute) |
| behavioural_valid | 0/1 |
| created_at | insert time |

`pt_keystrokes`
| column | meaning |
|--------|---------|
| id | PK |
| session_id | FK → pt_sessions |
| event_type | keydown / keyup / paste |
| key_value / t_ms / caret_pos / selection_end | raw event |

Self-rated and predicted effort are **separate columns**, reflecting the conceptual
separation in the schema itself.

---

## 10. Exact `prototype_platform/` folder structure

```
prototype_platform/
├── app.py                # own Flask app (own port); routes below. Imports shared
│                         #   features.py + explain.py from repo root (read-only).
├── db.py                 # own SQLite layer -> prototype.db (never data.db)
├── predict.py            # build features (via features.py) -> experimental estimate
│                         #   + SHAP explanation (via explain.py); orchestration
├── recommendations.py    # behaviour-tied rule engine (§6); thresholds from artifact
├── tasks.py              # copy of the writing-task prompts (decoupled from Stage 1)
├── prototype.db          # created at runtime (gitignored)
├── requirements.txt      # flask, scikit-learn, shap, pandas, numpy, matplotlib, joblib
├── README.md             # how to run the prototype independently
├── templates/
│   ├── write.html        # participant writing task + editor
│   ├── report.html       # explainable participant report (§5)
│   ├── dashboard.html    # researcher/admin dashboard (§7)
│   └── history.html      # participant session history / trends (§8)
└── static/
    ├── capture.js        # prototype's OWN keystroke logger (not Stage-1 logger.js)
    ├── report.js         # report charts/interactions
    ├── dashboard.js      # dashboard charts
    └── style.css         # prototype styling

Routes (app.py):
  GET  /                      landing + consent + code + task pick
  GET  /write/<task_id>       writing page
  POST /api/submit            store session+keystrokes, compute, predict, redirect
  GET  /report/<id>           participant explainable report
  GET  /admin                 dashboard (password-protected)
  GET  /admin/participant/<c> session history / trends for one participant
  GET  /admin/export.csv      prototype's own export
```

Shared, reused **read-only** (NOT copied, NOT modified), at repo root:
```
../features.py         # feature extraction (single source of truth)
../effort_model.pkl    # trained RF + LR + training context
../explain.py          # SHAP explain_session()  (imported read-only)
```

---

## 11. How reuse works without touching Stage 1

- **Import path:** `prototype_platform/app.py` adds the repo root to `sys.path` and
  does `from features import extract_features` and `from explain import
  explain_session, load_artifact`. These modules are **imported, never edited**.
- **Model artifact:** `effort_model.pkl` is loaded with `joblib.load` (read-only).
- **No shared state:** the prototype uses its own Flask instance, its own port, and
  `prototype.db`. It never imports `app.py`/`db.py` and never opens `data.db`.
- **Prompts:** writing-task text is **copied** into `tasks.py` so the prototype does
  not depend on the running Stage-1 app for content.
- **Dependencies:** the prototype ships its **own** `requirements.txt`; the Stage-1
  `requirements.txt` stays lean and unchanged (so the data-collection deploy is not
  affected by adding scikit-learn/shap).
- **Result:** deleting or stopping the prototype has zero effect on Stage-1
  collection; running the prototype cannot write to or corrupt `data.db`.

---

## 12. Clear separation of the three concepts (UI + data + wording)

| Concept | Source | Reliability | Where it appears | Wording |
|---------|--------|-------------|------------------|---------|
| **Measured behaviour** | keystrokes → `features.py` | reliable (objective) | Report §B, dashboard, trends | "your typing behaviour", "measured" |
| **Self-rated writing effort** | participant 1–5 | subjective self-report (the label) | Report §C, stored `self_rated_effort` | "self-rated writing effort", "what you told us" |
| **Experimental estimated writing effort** | model → `rf.predict` | **unreliable at n=22** | Report §D, stored `predicted_effort` | "experimental estimated writing effort" |

These are separate columns in the DB, separate sections in the report with distinct
visual styling, and separate tracks in the trend charts. The report and dashboard
**never** display the predicted value as if it were a measurement or a fact about
the person.

---

## 13. Ethics & wording guardrails (applied everywhere)

- Never: "mental effort", "cognitive load", "stress", "intelligence", "ability",
  "emotion", diagnosis, or any clinical framing.
- Always: "self-rated writing effort", "experimental estimated writing effort",
  "writing-process behaviour".
- The experimental estimate carries a visible caveat wherever it appears.
- A footer disclaimer states the tool is a research prototype that does not measure
  any psychological or medical state.

---

## 14. Deployment note

The prototype can run locally (`python prototype_platform/app.py` on its own port)
or, if desired later, as a **second, independent** PythonAnywhere web app — separate
from the Stage-1 collection app. SHAP runs at request time via the cached
`TreeExplainer` (fast on 9 features). This is out of scope until the prototype is
built and approved.

---

## 15. What is explicitly OUT of scope for the build

- No change to `app.py`, `db.py`, `data.db`, Stage-1 `templates/`, `static/`,
  `requirements.txt`.
- No retraining or tuning at runtime.
- No new claims beyond the approved wording.

---

## Approval checklist (please confirm before build)

- [ ] Folder structure & separation from Stage 1 (§10, §11)
- [ ] Report contents and the three-concept separation (§5, §12)
- [ ] Experimental-estimate framing / optional band (§3)
- [ ] Behaviour-tied recommendation rules & thresholds (§6)
- [ ] Dashboard + history/trends scope (§7, §8)
- [ ] Prototype database schema (§9)
- [ ] Wording guardrails (§13)
```
