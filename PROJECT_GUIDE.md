# Project Guide — What Each File Does

A plain-language map of the Typing Dynamics project, kept **side by side** with the
code so it's easy to understand and to explain in review meetings. Updated as each
stage progresses.

**Project in one line:** a web writing platform that records *how* people type
(speed, pauses, deletions, revisions) while they write, collects their own 1–5
rating of how much *effort* the writing took, and uses machine learning to test
whether typing behaviour can estimate that effort.

---

## The pipeline at a glance

```
Participant writes  ─►  Browser records every keystroke  ─►  Server stores it
   (index.html)            (logger.js)                        (app.py + db.py -> data.db)
        │
        ▼
Researcher reviews & marks valid sessions  ─►  Download the data
   (admin.html + admin.js)                      (server_export.csv, server_keystrokes.csv)
        │
        ▼
Stage 2: turn raw keystrokes into features  ─►  Stage 3: train & compare models
   (features.py -> features.csv)                  (coming next)
```

---

## Stage 1 — The data-collection website (already built & live)

| File | What it does (plain language) |
|------|-------------------------------|
| **templates/index.html** | The page a participant sees: pick a task, read the prompt, write in the text box, rate effort 1–5, submit. |
| **static/logger.js** | The "recorder". Runs in the browser and captures **every key press/release** with its exact time, plus caret position. This is what makes typing-dynamics research possible. Also blocks pasting and mobile/IME keyboards so the data stays clean. |
| **static/style.css** | How the pages look (layout, colours, fonts). |
| **templates/admin.html** | The researcher's dashboard: a table of all sessions, summary numbers, and buttons to mark each session **included** (valid) or **excluded**. |
| **static/admin.js** | Makes the admin dashboard interactive (the include/exclude buttons, viewing a session). |
| **app.py** | The **server brain** (Flask). Serves the pages, lists the writing tasks, receives a finished session, checks it for basic quality, and saves it. Also provides the password-protected admin views and the CSV download links. |
| **db.py** | The **database helper**. Defines the two tables and the functions to save/read them. |
| **data.db** | The **database file** (SQLite). Two tables: `sessions` (one row per writing task, incl. the 1–5 effort label) and `keystrokes` (one row per key event — the raw behaviour). *Note: the live data lives in the copy on the server, not this local file.* |
| **pythonanywhere_wsgi.py** | The glue that runs `app.py` on the PythonAnywhere hosting service. Holds the admin password as an environment setting (not in the code). |
| **requirements.txt** | The list of Python libraries the project needs. |
| **DEPLOY.md / README.md** | Notes on how to deploy and run the project. |

**Where the live site is:** https://AyeshaCheulkar.pythonanywhere.com/ (writing page),
`/admin` (dashboard). Code is on GitHub.

---

## The data we pulled down from the live site

| File | What it is |
|------|-----------|
| **server_export.csv** | One row per session — the **summary + the effort label**. 32 sessions total, 25 marked valid/included. Columns: id, participant, task, difficulty, timings, word/char counts, event count, **effort_rating (1–5)**, included flag. |
| **server_keystrokes.csv** | The **raw behaviour** — one row per single key event across all sessions (~31,700 rows). Columns: session_id, participant, task, event_type (keydown/keyup), key, time-in-ms, caret position. This is the ground-truth data Stage 2 reads. |

---

## Stage 2 — Turning raw keystrokes into features (just built)

| File | What it does |
|------|-------------|
| **features.py** | The **feature extractor**. Reads the two CSVs above and computes, for each session, a set of behavioural numbers the model can learn from: typing speed, inter-key intervals, how many/how long the pauses were, deletion rate, number of revision bursts, active writing time. It also flags sessions whose keystroke recording is unusable (e.g. mobile-keyboard sessions where keys show as "Unidentified"). **Written to be reusable on external datasets too**, so later comparisons are fair. |
| **features.csv** | The **output table** — one row per session, 18 features + the effort label. This is what the machine-learning step trains on. 25 sessions, of which **22 are behaviourally valid**; 3 (sessions 8, 9, 19) are flagged `behavioural_valid=0` because they were typed on mobile/IME keyboards that didn't record real keystroke timing. |

**Key idea to explain in review:** the model does **not** read the text people
wrote. It only looks at the *pattern of typing* (rhythm, pauses, corrections) and
tries to predict the writer's own effort rating. That is the research question.

---

## Data strategy (own vs external data)

- **Primary dataset = our 25 valid sessions.** They are primary because they carry
  the *real* label — the participant's own 1–5 effort rating. Nothing else has this.
- **External keystroke datasets = supporting only.** Used two ways, kept separate:
  - *Strategy A:* run external raw-typing data through the **same** `features.py`
    to validate/strengthen the feature approach (no effort label needed).
  - *Strategy B:* a separate experiment merging our data (simplified to
    low/high effort) with an external dataset that has a low/high *cognitive-demand*
    label — reported as an experiment, **never** treated as the same as our effort scores.
- We always **compare** results using our data alone vs. with external data added.

---

## Stage 3 — The primary model (just built)

| File | What it does |
|------|-------------|
| **model.py** | Trains three predictors on `features.csv` — a mean baseline, Linear Regression, and Random Forest — to estimate the 1–5 effort rating from typing behaviour only (never the text). Tested with **leave-one-participant-out** cross-validation, so every score reflects how well it works on a person the model has never seen. Prints accuracy (MAE, RMSE, R²), a feature↔effort correlation table, and which behaviours matter most. Also runs a sensitivity check with the 3 flagged sessions added. |
| **model_binary.py** | The same idea but predicting just **LOW vs HIGH** effort (1–2 vs 3–5) instead of the full 1–5 scale — an easier target for a small dataset, and the bridge to external low/high cognitive-demand data. Reports balanced accuracy, F1, AUC, confusion matrix, and a readable "feature means for LOW vs HIGH" table. |
| **STAGE3_RESULTS.md** | Plain-language write-up of both the 1–5 and the LOW/HIGH results for review meetings (see summary below). |

**What the pilot showed (be honest in review):** with only 22 sessions, neither
the 1–5 regression **nor** the LOW/HIGH classifier beats a simple baseline — the
expected result of a small pilot, not an error. Valuable outcomes: (1) the
pipeline runs end to end; (2) the sensitivity check *proves* the 3 flagged
sessions are harmful and were rightly excluded; (3) a **consistent, theory-matching
descriptive signal** — higher effort goes with more pausing, more revision, and
more variable typing rhythm. The conclusion both models agree on: **more data is
the bottleneck, not the method.** Full detail in `STAGE3_RESULTS.md`.

## Step 4 — External-data adapter (just built)

| File | What it does |
|------|-------------|
| **external_data.py** | Lets an **external** keystroke dataset be run through the **same** `features.py`, so external and our own features live in one shared feature space. It converts any dataset's own column layout into our generic event stream and computes the identical features. Includes ready presets for the **EmoSurv** and **Aalto** datasets (confirm against the real file header), and a built-in plumbing self-test. |

| **external_experiment.py** | The **separate** experiment on EmoSurv's own emotion labels (never mixed with our effort labels): can the same typing features tell apart emotional states? Same leave-one-participant-out method as our own models. |
| **Free Text Typing Dataset.csv** | The downloaded EmoSurv raw data (external, supporting only). |
| **external_features_emosurv.csv** | EmoSurv run through our extractor — 190 valid sessions, 81 people, same feature columns as ours. |
| **keyrecs_freetext.csv / keyrecs_demographics.csv** | Second external dataset (KeyRecs, Zenodo) — free-text typing, 99 people. Supporting/validation only, no effort label. |
| **external_features_keyrecs.csv** | KeyRecs through our extractor — 197 valid sessions, 99 people. Confirms the features generalise across a *second* independent dataset. |
| **EXTERNAL_RESULTS.md** | Plain-language write-up of the EmoSurv compatibility, feature validation, and emotion experiment. |

**What Step 4 showed (strong point for review):** EmoSurv's absolute timestamps
were corrupted (saved via Excel), but its inter-key intervals were intact, so we
reconstructed the timeline and ran the **same** extractor. Result: (1) the
features come out at the **same scale as ours** (median keystroke gap 206 ms vs
our 210 ms) — the pipeline is validated on an independent 81-person dataset; and
(2) on that properly-sized data, the same features **predict a psychological state
above chance** (Random Forest beats baseline). Conclusion: our own model's
weakness is about **sample size (n=22), not method.** Detail in `EXTERNAL_RESULTS.md`.

## Step 5 — Final analysis (just done)

| File | What it does |
|------|-------------|
| **analysis_primary.py** | The final statistical + ML analysis of our own effort data: correlation of effort with each typing behaviour (+ hypothesis check), then Linear Regression & Random Forest with participant-aware CV (LOPO & GroupKFold), MAE/RMSE/R². |
| **analysis_plots.py / analysis_primary.png** | One summary figure: behaviour↔effort correlations, and model error vs baseline. |
| **ANALYSIS_PRIMARY.md** | Plain-language write-up of the final primary analysis + hypothesis verdict. |
| **FINAL_COMPARISON.md** | The concise 3-way comparison: primary effort model vs external validation vs separate EmoSurv experiment. |

**Final verdict:** hypotheses are **directionally supported but statistically
unconfirmed** at n=22 (7/9 behaviours point the right way; none significant; models
don't beat baseline). Cross-checked against the external results, the limitation is
**sample size, not method.** No new sessions were on the server, so the primary
sample could not be grown at this time.

## Stage B — Explainability (SHAP) — just done

| File | What it does |
|------|-------------|
| **train_model.py** | Fits the final Random Forest + Linear Regression on the 22 valid sessions and saves **`effort_model.pkl`** — the shared artifact the prototype platform will load (it never retrains). |
| **effort_model.pkl** | The saved models + feature list + training data for SHAP/percentile context. |
| **explain.py** | SHAP explanations: a global importance chart (`shap_summary.png`) and a reusable `explain_session()` that says, in plain words, which behaviours pushed one writer's effort estimate up/down. |
| **shap_summary.png** | SHAP global-importance figure. |
| **EXPLAINABILITY.md** | Plain-language write-up + honest caveats. |

**What SHAP showed:** the model leans most on **writing time and pausing** (then
rhythm) — consistent with the correlation analysis and the hypothesis. Framed
honestly: since the model doesn't beat baseline, SHAP explains *what the model
does*, and predicted effort is **experimental**.

## Not built yet — the final prototype platform (deliberately deferred)

Will live in a **separate `prototype_platform/` folder** — its own templates,
static files, and prediction/report logic — reusing only `effort_model.pkl` and
`features.py`. It must **not** modify the Stage-1 data-collection app (`app.py`,
`db.py`, `data.db`, `templates/`, `static/`).

| Step | Status |
|------|--------|
| **Stage C design** | ✅ Done — `PLATFORM_DESIGN.md`. |
| **Stage C build** | ✅ Done — built entirely in **`prototype_platform/`**; Stage-1 app/db untouched. Run with `python prototype_platform/app.py` (port 5001). |

## The prototype platform (`prototype_platform/` — separate from Stage 1)

A self-contained Flask app: participant writes → keystrokes captured → behaviour
features (via shared `features.py`) → **experimental** effort estimate + SHAP
explanation (via shared `explain.py`/`effort_model.pkl`) → explainable report with
behaviour-tied recommendations. Plus a researcher dashboard, per-participant
history, and a model-results panel. Reuses the shared research code **read-only**;
its own database is `prototype_platform/prototype.db` (never `data.db`).

| File | Role |
|------|------|
| `app.py` | Flask routes, own port 5001, own DB |
| `db.py` | prototype SQLite (`pt_sessions`, `pt_keystrokes`) |
| `predict.py` | features + experimental estimate + SHAP (reuses shared code) |
| `recommendations.py` | behaviour-tied suggestions (thresholds from `features.csv`) |
| `tasks.py` | writing prompts (copied, decoupled) |
| `templates/` | `write.html`, `report.html`, `dashboard.html`, `history.html` |
| `static/` | `capture.js`, `style.css`, result images |
| `README.md` | how to run |

---

*This guide is updated at the end of each stage so it always matches the code.*
