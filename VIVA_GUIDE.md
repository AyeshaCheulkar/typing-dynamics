# Viva Guide — Where Is Everything? (Typing Dynamics Project)

**One-line project:** A web platform records *how* people type (speed, pauses, deletions, revisions) while they write, collects their own 1–5 rating of **self-perceived writing effort**, and tests with machine learning whether typing behaviour can estimate that rating. A separate prototype then turns the trained model into an explainable report for a writer.

---

## 0. QUICK LOOKUP — "Ma'am asks: where is ...?"

| Ma'am asks | Answer (file) |
|---|---|
| Where is **keystroke logging**? | `static/logger.js` (browser, records every keydown/keyup + time + caret). Prototype version: `prototype_platform/static/capture.js` |
| Where are keystrokes **received/saved** on the server? | `app.py` → `save_session()` (`POST /api/session`) → `db.py` → `insert_session()` |
| Where is the **database**? | Schema/code: `db.py`. File: `data.db` (Stage 1). Prototype: `prototype_platform/db.py` → `prototype.db` |
| Where is **feature extraction**? | `features.py` → `extract_features()` (writes `features.csv`) |
| Where is the **ML model training**? | `train_model.py` (final model → `effort_model.pkl`); evaluation in `model.py`, `analysis_primary.py` |
| Where is **Random Forest / Linear Regression**? | `analysis_primary.py` → `model_factories()`; fitted in `train_model.py` → `train()` |
| Where is **SHAP explainability**? | `explain.py` → `explain_session()` and `global_summary()` (figure: `shap_summary.png`) |
| Where is the **prediction for a new session**? | `prototype_platform/predict.py` → `estimate_and_explain()` |
| Where is the **report** the writer sees? | `prototype_platform/app.py` → `report()` + `templates/report.html` |
| Where is the **admin / researcher dashboard**? | Stage 1: `app.py` `/admin` + `templates/admin.html` + `static/admin.js`. Prototype: `prototype_platform/app.py` `/admin/*` routes |
| Where are **recommendations** generated? | `prototype_platform/recommendations.py` → `recommend()` |
| Where is **cross-validation (LOPO)**? | `analysis_primary.py` → `oof_lopo()`; `model.py` → `lopo_scores()` |
| Where are **statistics / confidence intervals**? | `analysis_primary.py` → `bootstrap_corr()`, `metric_ci()`, `permutation_r2()`, `paired_vs_baseline()` |
| Where is the **external dataset** work? | `external_data.py` (convert), `external_experiment.py` (emotion experiment) |
| Where is **data-quality filtering**? | `app.py` → `assess_quality()` (content flags) and `features.py` → `behavioural_valid` (≥40 keystrokes, <30% unidentified keys) |
| Where is **deployment**? | `pythonanywhere_wsgi.py` (Stage 1), `prototype_wsgi.py` (prototype), `DEPLOY.md` |
| Where is the **admin password / security**? | `app.py` → `require_admin()` (HTTP Basic Auth, password from env var `ADMIN_PASSWORD`) |

---

## 1. Research app vs Prototype — and why two?

| | **Stage 1: Research / data-collection app** | **Prototype platform** |
|---|---|---|
| Folder | project root (`app.py`, `db.py`, `templates/`, `static/`) | `prototype_platform/` |
| Purpose | **Collect clean research data**: keystrokes + the participant's effort rating | **Demonstrate the finished product**: take a new writing session, predict + explain + give feedback |
| Who uses it | Study participants (the people whose data trains the model) | Demo users / evaluators / researcher |
| Output | Raw data (`data.db` → CSVs) | A report page: self-rated effort, **Experimental Model Estimate**, mean-baseline reference, SHAP bars, behaviour profile, suggestions |
| Uses the ML model? | **No.** It only records data. | **Yes.** Loads `effort_model.pkl` (never retrains) |
| Database | `data.db` (`sessions`, `keystrokes`) | `prototype.db` (`pt_sessions`, `pt_keystrokes`) |
| Port | Hosted at `AyeshaCheulkar.pythonanywhere.com` | Separate (local 5001 / own WSGI) |

**Why two separate apps?**
1. **Protect the research data.** The study dataset (22 valid sessions) is the scientific ground truth. Demo/test sessions typed into a prototype must never pollute it. Separate DB files guarantee this.
2. **The model must be trained on data collected *before* it is used.** Collection (Stage 1) comes first; the prototype exists only after training. You can't mix a live predictor into the collection tool without biasing the labels (participants would see the prediction before rating themselves).
3. **Different goals, different UI.** Collection = minimal, neutral editor. Prototype = reports, charts, dashboards.
4. **Reuse without copying.** The prototype imports `features.py`, `explain.py` and loads `effort_model.pkl` read-only, so the science has a single source of truth. (Rule recorded in `PLATFORM_DESIGN.md`.)

---

## 2. The pipeline end to end

```
STAGE 1  Participant writes  ->  logger.js records keys  ->  app.py/db.py save  ->  data.db
              |
              v  (researcher marks valid sessions in /admin, downloads CSVs)
STAGE 2  server_export.csv + server_keystrokes.csv  --features.py-->  features.csv (9 features + label)
              |
              v
STAGE 3  model.py / analysis_primary.py  (evaluate LinReg vs RF vs mean baseline, LOPO CV)
         train_model.py  ->  effort_model.pkl
              |
              v
STAGE 4  explain.py  (SHAP)  ->  shap_summary.png
              |
              v
PROTOTYPE  new session -> predict.compute_features -> RF prediction -> SHAP -> report.html
```

---

## 3. Every file explained

### 3.1 Stage 1 — data-collection app (root)

| File | What it contains | Key functions | Problem it solves |
|---|---|---|---|
| `app.py` | Flask backend (439 lines) | `index()` serve editor; `save_session()` receive+store; `assess_quality()` flag gibberish/short/copied text; `normalize_pid()` canonical participant IDs; `require_admin()` password gate; `admin()`, `export_csv()`, `export_keystrokes_csv()`, `set_included()`, `session_detail()` | Receive & store sessions safely; give researcher a way to review/export |
| `db.py` | SQLite layer | `init_db()`, `insert_session()`, `list_sessions()`, `list_all_keystrokes()`, `get_session_detail()`, `set_included()` | Persist the two layers: `sessions` (label) and `keystrokes` (raw behaviour) |
| `data.db` | The SQLite database file | tables `sessions`, `keystrokes` | Local copy of collected data (live data is on PythonAnywhere) |
| `templates/index.html` | Participant page | task choice, editor, effort-rating screen | The UI participants use |
| `templates/admin.html` | Researcher table | session list, include/exclude | Review & mark valid sessions |
| `static/logger.js` | **The keystroke recorder** | `record()` capture keydown/keyup with timestamp+caret; `blockDevice()/isPhone()` block phones; `flagBlockedPaste()` stop pasting; `checkIme()` detect IME keyboards; `pickVariation()`, `selectLevel()` task setup | Core of typing-dynamics research; keeps data clean |
| `static/admin.js` | Admin interactivity | `loadKeystrokes()`, `stat()`, `esc()` | Make dashboard work |
| `static/style.css` | Styling | — | Look and feel |
| `static/templates/` | Untracked duplicate copies of the two HTML templates | — | Not needed; ignore |
| `pythonanywhere_wsgi.py` | Template WSGI file | imports Flask `app` | Lets PythonAnywhere serve Stage 1 |
| `requirements.txt` | Python dependencies | — | Reproducible install |

### 3.2 Stage 2 — feature extraction

| File | What it does | Key functions |
|---|---|---|
| `features.py` | Raw keystrokes → one row of behaviour features per session (`features.csv`). Thresholds: short pause 500 ms, long pause 2000 ms. Validity rule: ≥40 keydowns and <30% unidentified keys. | `extract_features()`, `load_events_by_session()`, `build()` |
| `extra_features.py` | Extra theory-based features (initial planning pause, within-word pauses…) from existing keystrokes → `extra_features.csv`. Used in extended analysis only, **not** the 9 model features | `session_extra()`, `build()` |
| `external_data.py` | Reshapes external keystroke datasets (EmoSurv, KeyRecs) into the same event format and runs the **same** extractor | `build_emosurv_features()`, `build_keyrecs_features()`, `keycode_to_key()` |

### 3.3 Stage 3 — modelling & analysis

| File | What it does | Key functions |
|---|---|---|
| `model.py` | First comparison: mean baseline vs Linear Regression vs Random Forest, Leave-One-Participant-Out CV | `lopo_scores()`, `evaluate()`, `correlations()` |
| `model_binary.py` | Reframes target as LOW vs HIGH effort (easier with small data) | `make_binary()`, `lopo_classify()` |
| `analysis_primary.py` | **Final rigorous analysis**: Spearman correlations + bootstrap CIs, LOPO predictions, paired Wilcoxon vs baseline, permutation test. Also defines the 9 `MODEL_FEATURES` and `HYPOTHESES` | `bootstrap_corr()`, `oof_lopo()`, `metric_ci()`, `paired_vs_baseline()`, `permutation_r2()` |
| `analysis_plots.py` | Draws `analysis_primary.png` | — |
| `mixed_effects.py` | Mixed-effects model (random intercept per participant) because some people did multiple sessions | `run()` |
| `difficulty_analysis.py` | Do Easy vs Moderate tasks differ in effort/behaviour? (Mann-Whitney U) | `run()` |
| `external_experiment.py` | Separate **emotion** classification on EmoSurv to prove the features carry signal at scale (never mixed with effort labels) | `lopo()`, `run_task()` |
| `train_model.py` | Fits final RF + Linear Regression on all 22 valid sessions, saves `effort_model.pkl` (includes features list, training data, baseline mean 2.68) | `train()` |
| `explain.py` | SHAP: global importance + per-session explanation; falls back to linear coefficients if `shap` isn't installed | `explain_session()`, `global_summary()`, `linear_coefficients()` |

### 3.4 Prototype platform (`prototype_platform/`)

| File | What it does |
|---|---|
| `app.py` | Flask app. Writer: `/` landing, `/test` write, `/api/submit` (extract→predict→save), `/report/<id>`. Admin: login, overview, participants, per-session report, live view, methodology, model card, research, CSV export |
| `predict.py` | **The end-to-end bridge**: `compute_features()` → `estimate_and_explain()` (RF prediction + SHAP + baseline + band) → `timeline_from_events()` (typing/pause/revision timeline) |
| `recommendations.py` | Suggestions tied to **observed behaviour** (never to the score), thresholds = quartiles of the study sample → `recommend()`, `context_labels()` |
| `research_data.py` | Read-only access to study CSVs for the researcher dashboard (KPIs, distributions, participant profiles) |
| `db.py` | Own database `prototype.db` (`pt_sessions`, `pt_keystrokes`) |
| `tasks.py` | Writing prompts (2 difficulty levels × several variations) copied so the prototype never imports Stage 1 |
| `static/capture.js` | Keystroke capture on the prototype writing page |
| `static/dashboard.js` | Dashboard animations/charts |
| `static/style.css`, `premium.css`, `report.css` | Styling |
| `static/vendor/chart.min.js` | Chart.js library (charts) |
| `static/*.png` | Copies of the analysis/SHAP figures for the Research & Model-Card pages |
| `templates/` (15 files) | `base`/`admin_base` layouts; `landing`, `write`, `report` (writer); `login`, `overview`, `participants`, `participant_profile`, `session_report`, `live`, `live_profile`, `methodology`, `model_card`, `research` (admin) |
| `README.md`, `requirements.txt`, `.gitignore` | Docs/deps |

### 3.5 Deployment & utilities

| File | Purpose |
|---|---|
| `prototype_wsgi.py` | WSGI config to host the prototype on PythonAnywhere |
| `run_prototype_online.bat` | Starts the prototype locally and opens a Cloudflare public tunnel |
| `build_blackbook.py` | Generates the project report (Word) with python-docx |
| `render_blackbook_pdf.py` | Converts that report to PDF with ReportLab |
| `deploy.zip`, `prototype_files.zip` | Packaged uploads for hosting |

### 3.6 Documentation (.md)

`README.md` overview · `PROJECT_GUIDE.md` file map · `PLATFORM_DESIGN.md` prototype design & rules · `DEPLOY.md` hosting steps · `PROJECT_DEPLOYMENT_REPORT.md` formal deployment report · `ANALYSIS_PRIMARY.md` final stats results · `ANALYSIS_EXTENDED.md` extended analysis · `STAGE3_RESULTS.md` model results · `EXTERNAL_RESULTS.md` external-data results · `FINAL_COMPARISON.md` three-result summary · `EXPLAINABILITY.md` SHAP notes · `AGENTS.md` repo guidelines.

### 3.7 Data & generated files

| File | What it is |
|---|---|
| `server_export.csv` | One row per session (metadata + effort label); 32 sessions, 25 included originally |
| `server_keystrokes.csv` | ~31,700 raw keystroke events — ground truth for Stage 2 |
| `features.csv` | Per-session features + label (input to models) |
| `extra_features.csv` | Extra features (extended analysis) |
| `Free Text Typing Dataset.csv` | **EmoSurv** raw external dataset (emotion-labelled typing) |
| `keyrecs_freetext.csv`, `keyrecs_demographics.csv` | **KeyRecs** raw external dataset |
| `external_features_*.csv` | External datasets after our feature extractor |
| `effort_model.pkl` | Trained model artifact (RF + LR + training data + baseline) |
| `analysis_primary.png`, `difficulty_analysis.png`, `shap_summary.png` | Result figures |
| `server.log`, `server_run.log` | Logs |
| `venv/`, `__pycache__/`, `tmp/` | Environment/cache/scratch — not project code |

### 3.8 The "agent" and graphify files

| File | What it is |
|---|---|
| `.agents/rules/graphify.md` | An **instruction file for AI coding assistants** (always-on): "before answering code questions, query the graphify knowledge graph first." Not part of the project's logic |
| `.agents/workflows/graphify.md` | Defines a `graphify` workflow command for the assistant to build the graph |
| `graphify-out/graph.json` | Machine-readable **knowledge graph** of the whole project (1080 nodes, 2701 edges: files, functions, relations) |
| `graphify-out/graph.html` | Interactive visual of that graph (open in browser) |
| `graphify-out/GRAPH_REPORT.md` | Human summary: communities (e.g. "Primary Statistical Analysis", "Prototype Dashboard & Reporting"), key nodes |
| `graphify-out/manifest.json`, `cost.json`, `cache/` | Bookkeeping: which files were scanned, token cost, cache |

These are **developer tooling** to help navigate the code; they are not part of the research system. If asked: "graphify is a tool I used to map the codebase; it plays no role in the ML or the platform."

---

## 4. Technologies — what, why, how

| Technology | Why chosen | How used here |
|---|---|---|
| **Python** | Standard for data science/ML | All backend, analysis, models |
| **Flask** | Small, simple web framework; ideal for a research app | `app.py` routes (both apps) |
| **SQLite** | Zero-setup file database, enough for ~tens of participants | `data.db`, `prototype.db` via `db.py` |
| **HTML/CSS/JavaScript** | Keystroke timing can only be captured in the browser | `logger.js`/`capture.js` listen to `keydown`/`keyup`, store `performance`/`Date` time, caret position |
| **Jinja2 templates** | Server-side HTML rendering (comes with Flask) | `templates/*.html` |
| **Chart.js** | Lightweight charts in the browser | Dashboard & report visuals |
| **pandas / NumPy** | Tabular data & numerics | Feature tables, analysis |
| **scikit-learn** | Reliable ML library | `RandomForestRegressor`, `LinearRegression`, `LeaveOneGroupOut`, scaling |
| **SciPy / statsmodels** | Statistics | Spearman, Wilcoxon, Mann-Whitney, mixed-effects |
| **SHAP** | Standard explainability for tree models | `TreeExplainer` in `explain.py` |
| **matplotlib** | Static figures | `*.png` result charts |
| **joblib** | Save/load model | `effort_model.pkl` |
| **python-docx / ReportLab** | Generate Word/PDF report | `build_blackbook.py`, `render_blackbook_pdf.py` |
| **PythonAnywhere** | Free permanent HTTPS hosting for remote participants | Stage 1 live site; WSGI files |
| **Git / GitHub** | Version control + easy deploy via `git pull` | `AyeshaCheulkar/typing-dynamics` |
| **Cloudflare tunnel** | Temporary public URL for local demo | `run_prototype_online.bat` |

---

## 5. Models — everything

**Target:** participant's own rating of *self-perceived writing effort*, 1–5. (Not mental effort, stress, or any medical/psychological state.)

**Data:** 22 behaviourally-valid sessions from 17 participants. Ratings: {1:3, 2:7, 3:8, 4:2, 5:2}, mean **2.68**.

**The 9 features** (from `features.py`, defined in `analysis_primary.py`):
1. Typing speed (chars/sec) 2. Average keystroke gap (mean IKI) 3. Longest pause 4. Long-pause frequency (per 100 keys, ≥2 s) 5. Share of time paused 6. Backspace/delete activity 7. Revision activity (editing bursts per 100) 8. Writing time 9. Typing-rhythm variability (std of IKI)

**Three predictors compared:**
- **Mean baseline** — always predicts 2.68. The benchmark any real model must beat.
- **Linear Regression** (standardised) — simple, interpretable.
- **Random Forest** (400 trees, min leaf 2) — handles non-linear patterns; this is the model used in the prototype.

**Evaluation:** Leave-One-Participant-Out CV (whole participant held out, so a person's multiple sessions never leak between train/test); 95% CIs by bootstrapping *participants*; Wilcoxon test vs baseline; permutation test for R².

**Results (be honest in viva):**
| Model | MAE | Verdict |
|---|---|---|
| Baseline (mean) | 0.94 | best |
| Random Forest | 1.10 | slightly worse (p=0.045) |
| Linear Regression | 1.99 | much worse |

7 of 9 behaviours point in the hypothesised direction but **0 of 9 are statistically significant**. Conclusion: **directionally supported but underpowered** — the limit is the sample size (n=22), not the method.

**Supporting evidence from external data:**
- *Feature validation:* same extractor on EmoSurv (190 sessions/81 people) and KeyRecs (197/99) gives same-scale features (median keystroke gap 209 ms ours / 206 / 174).
- *Emotion experiment:* on EmoSurv the RF beats chance (balanced accuracy 0.39 vs 0.20 five-way; 0.64 vs 0.50 neutral-vs-emotion). Shows typing features carry behavioural-state signal when data is large. **Emotion labels were never mixed with effort labels.**

**Why does the prototype still use the RF if it doesn't beat the baseline?** To show the complete pipeline (new session → features → model → SHAP → report) and the *intended* product. Every estimate is labelled **Experimental Model Estimate**, shown next to the mean baseline (reference only), and the report states it is not validated. With more data it should become reliable.

**SHAP:** for each session, shows how much each of the 9 behaviours pushed the estimate up or down. It explains *what the model does*, not what causes effort.

**Why a mean-baseline reference?** It shows the user how the model compares with "just guess the average" and keeps us honest that the model is not yet better.

---

## 6. Likely viva questions — short answers

- **Why keystroke dynamics?** Objective, unobtrusive behaviour; commonly used in writing-process research.
- **Why leave-one-participant-out?** Prevents leakage when one person has several sessions; mimics predicting for a new person.
- **Why didn't the model beat the baseline?** Only 22 sessions/17 people for a noisy 1–5 label; underpowered, directionally supported.
- **Why two apps?** See Section 1 — protect research data, correct order of work, different goals.
- **What's novel/useful?** A reproducible pipeline + explainable prototype, validated feature extraction on two external datasets, and honest reporting.
- **Ethical limits?** No clinical claims, participant IDs only, admin password-protected, raw data/keystrokes kept out of the public repo.
- **What next?** Collect more labelled sessions, re-train with `train_model.py`, re-evaluate before trusting estimates.
