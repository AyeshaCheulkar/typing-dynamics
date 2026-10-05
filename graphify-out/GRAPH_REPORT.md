# Graph Report - final research project  (2026-09-20)

## Corpus Check
- 67 files · ~53,867 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: .css 4, (none) 2, .bat 1)

## Summary
- 1080 nodes · 2701 edges · 64 communities (47 shown, 17 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 113 edges (avg confidence: 0.85)
- Token cost: 12,500 input · 3,200 output

## Community Hubs (Navigation)
- Chart.js Color Utilities
- Chart.js Color Utilities
- Chart.js Color Utilities
- Chart.js Layout and Scales
- External Datasets & Adapters
- Data Collection Admin Dashboard
- Prototype Dashboard & Reporting
- Primary Statistical Analysis
- Chart.js Color Utilities
- Chart.js Animation Engine
- Data Collection Database Layer
- Prototype Dashboard & Reporting
- Chart.js Layout and Scales
- Prototype Dashboard & Reporting
- Chart.js Event Handling
- Chart.js Rendering Pipeline
- Chart.js Rendering Pipeline
- Chart.js Event Handling
- Chart.js Rendering Pipeline
- Prototype Dashboard & Reporting
- Chart.js Visualization Core 20
- Chart.js Visualization Core 21
- Effort Prediction & Recommendations
- Chart.js Visualization Core 23
- Task Difficulty Analytics
- Effort Regression Models
- Chart.js Visualization Core 26
- Chart.js Rendering Pipeline
- Effort Prediction & Recommendations
- Chart.js Visualization Core 29
- Chart.js Animation Engine
- Chart.js Rendering Pipeline
- Chart.js Rendering Pipeline
- Chart.js Visualization Core 33
- Chart.js Layout and Scales
- Chart.js Rendering Pipeline
- Binary Classification Pipeline
- Chart.js Visualization Core 37
- Chart.js Visualization Core 38
- Chart.js Visualization Core 39
- Chart.js Event Handling
- Chart.js Rendering Pipeline
- Chart.js Rendering Pipeline
- Chart.js Event Handling
- Browser Keystroke Logger
- external_experiment.py
- Chart.js Visualization Core 46
- Chart.js Visualization Core 47
- Chart.js Visualization Core 48
- Chart.js Rendering Pipeline
- Chart.js Visualization Core 50
- tasks.py
- Chart.js Visualization Core 53
- Chart.js Visualization Core 54
- admin.js
- Repository Guidelines & Rules
- Primary Statistical Analysis
- Repository Guidelines & Rules
- Repository Guidelines & Rules
- Deployment & Guides
- Deployment & Guides
- Extended Analysis (no new data

## God Nodes (most connected - your core abstractions)
1. `an()` - 61 edges
2. `ns()` - 55 edges
3. `s()` - 42 edges
4. `o()` - 40 edges
5. `a()` - 38 edges
6. `n()` - 37 edges
7. `no` - 35 edges
8. `l()` - 32 edges
9. `d()` - 31 edges
10. `va` - 30 edges

## Surprising Connections (you probably didn't know these)
- `train()` --calls--> `load()`  [EXTRACTED]
  train_model.py → analysis_primary.py
- `save_session()` --calls--> `insert_session()`  [EXTRACTED]
  app.py → db.py
- `set_included()` --calls--> `set_included()`  [EXTRACTED]
  app.py → db.py
- `admin()` --calls--> `list_sessions()`  [EXTRACTED]
  app.py → db.py
- `export_csv()` --calls--> `list_sessions()`  [EXTRACTED]
  app.py → db.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Effort Prediction ML Pipeline** — features, model, analysis_primary, explain [INFERRED 0.95]
- **Interactive Prototype Platform Flow** — prototype_platform_app, prototype_platform_predict, prototype_platform_recommendations, prototype_platform_db [INFERRED 0.95]
- **Cross-Dataset Feature Validation Group** — features, external_data, external_experiment [INFERRED 0.85]

## Communities (64 total, 17 thin omitted)

### Community 0 - "Chart.js Color Utilities"
Cohesion: 0.06
Nodes (25): afterDraw(), afterEvent(), afterUpdate(), Bi(), Ci(), configure(), Ee(), Fi() (+17 more)

### Community 1 - "Chart.js Color Utilities"
Cohesion: 0.05
Nodes (11): As(), beforeUpdate(), bn, dn(), initialize(), labelColor(), labelPointStyle(), ns() (+3 more)

### Community 2 - "Chart.js Color Utilities"
Cohesion: 0.05
Nodes (13): be(), cn(), destroy(), fe(), Gt(), hn(), Jo(), jt() (+5 more)

### Community 3 - "Chart.js Layout and Scales"
Cohesion: 0.07
Nodes (13): beforeLayout(), buildLookupTable(), En, Fo(), _generate(), getDecimalForValue(), _getTimestampsForTable(), init() (+5 more)

### Community 4 - "External Datasets & Adapters"
Cohesion: 0.07
Nodes (37): csv, build_emosurv_features(), build_external_features(), build_keyrecs_features(), _decode_keycode(), _emo_num(), keycode_to_key(), _keyrecs_key() (+29 more)

### Community 5 - "Data Collection Admin Dashboard"
Cohesion: 0.07
Nodes (36): admin(), assess_quality(), export_csv(), export_keystrokes_csv(), index(), normalize_pid(), _per_participant(), route (+28 more)

### Community 6 - "Prototype Dashboard & Reporting"
Cohesion: 0.10
Nodes (31): admin_login(), _avg(), export_csv(), home(), live_clear(), live_page(), _live_participants(), _live_profile() (+23 more)

### Community 7 - "Primary Statistical Analysis"
Cohesion: 0.12
Nodes (28): analysis_plots.py — one figure summarising the PRIMARY effort analysis, now…, _boot_rows(), bootstrap_corr(), limitations(), load(), main(), metric_ci(), model_factories() (+20 more)

### Community 8 - "Chart.js Color Utilities"
Cohesion: 0.11
Nodes (11): color(), Ft(), It(), kt(), mt(), qt(), _t(), te() (+3 more)

### Community 9 - "Chart.js Animation Engine"
Cohesion: 0.13
Nodes (3): bt, Cs, os()

### Community 10 - "Data Collection Database Layer"
Cohesion: 0.10
Nodes (24): get_connection(), get_session_detail(), init_db(), insert_session(), list_all_keystrokes(), list_sessions(), _migrate(), db.py — SQLite schema and helper functions for the Typing Dynamics platform.… (+16 more)

### Community 11 - "Prototype Dashboard & Reporting"
Cohesion: 0.17
Nodes (22): admin(), session_report(), effort_distribution(), feature_vs_effort(), _fmt_date(), _keys_by_session(), participant_profile(), participants() (+14 more)

### Community 13 - "Prototype Dashboard & Reporting"
Cohesion: 0.11
Nodes (18): explain_session(), Explain ONE session. `feats` = dict feature->value. Returns a dict the platform…, os, Writing Analytics Platform — Prototype Design (Stage C), Prototype Platform System Architecture, Platform UI & UX Specifications, submit(), _band() (+10 more)

### Community 14 - "Chart.js Event Handling"
Cohesion: 0.16
Nodes (11): ct(), fs(), ge(), gs(), ms(), ps(), i(), vs() (+3 more)

### Community 15 - "Chart.js Rendering Pipeline"
Cohesion: 0.16
Nodes (4): ca(), Do(), eo(), Oe()

### Community 16 - "Chart.js Rendering Pipeline"
Cohesion: 0.12
Nodes (19): ai(), ao(), at(), draw(), getMaxOverflow(), getRange(), hi(), kn() (+11 more)

### Community 19 - "Prototype Dashboard & Reporting"
Cohesion: 0.16
Nodes (17): _fmt_time(), _hjoin(), _profile_interpretation(), Plain-language summary of the radar (percentiles vs the study sample)., report(), clear_all(), get_connection(), get_keystrokes() (+9 more)

### Community 20 - "Chart.js Visualization Core 20"
Cohesion: 0.20
Nodes (14): average(), dataset(), getCenterPoint(), Hs, _i(), index(), inRange(), ji() (+6 more)

### Community 21 - "Chart.js Visualization Core 21"
Cohesion: 0.15
Nodes (11): buildTicks(), Fn(), go(), ii(), parse(), parseArrayData(), parseObjectData(), parsePrimitiveData() (+3 more)

### Community 22 - "Effort Prediction & Recommendations"
Cohesion: 0.13
Nodes (16): _explainer(), global_summary(), linear_coefficients(), load_artifact(), explain.py — Stage B: SHAP explainability for the effort model. Produces: - a…, Standardised LR coefficients — a simple linear cross-check on SHAP., SHAP global importance (bar of mean|impact|) + return values for the doc., Stage B — Explainability (SHAP) (+8 more)

### Community 23 - "Chart.js Visualization Core 23"
Cohesion: 0.18
Nodes (6): b(), ce(), de, dt(), he(), ia()

### Community 24 - "Task Difficulty Analytics"
Cohesion: 0.14
Nodes (12): Task Difficulty Analysis Plot (difficulty_analysis), difficulty_analysis.py — does task difficulty (Easy vs Moderate) relate to…, matplotlib, matplotlib_pyplot, mixed_effects.py — participant-aware relationship modelling on the EXISTING 22…, run(), _z(), numpy (+4 more)

### Community 25 - "Effort Regression Models"
Cohesion: 0.19
Nodes (14): correlations(), describe(), evaluate(), load(), lopo_scores(), main(), model.py — Stage 3 (primary model): can typing dynamics estimate writing…, Pearson & Spearman correlation of each feature with the effort rating. (+6 more)

### Community 26 - "Chart.js Visualization Core 26"
Cohesion: 0.19
Nodes (6): a(), determineDataLimits(), Di(), is(), pt(), xo

### Community 28 - "Effort Prediction & Recommendations"
Cohesion: 0.24
Nodes (14): context_labels(), _display(), _dist(), _percentile_of(), _q(), recommendations.py — writing-process suggestions that are TIED TO OBSERVED…, Behaviour-tied suggestions (never triggered by the effort score). Each item…, Load the training distribution (valid sessions) once; column -> sorted array. (+6 more)

### Community 29 - "Chart.js Visualization Core 29"
Cohesion: 0.19
Nodes (13): _calculateBarIndexPixels(), _getRuler(), _getStackCount(), _getStackIndex(), _getStacks(), Gn(), In(), s() (+5 more)

### Community 31 - "Chart.js Rendering Pipeline"
Cohesion: 0.19
Nodes (3): n(), ne(), numeric()

### Community 32 - "Chart.js Rendering Pipeline"
Cohesion: 0.21
Nodes (4): _calculateBarValuePixels(), getBasePixel(), getPixelForValue(), updateElements()

### Community 33 - "Chart.js Visualization Core 33"
Cohesion: 0.16
Nodes (10): ea(), fa(), ga(), ha, la(), pa(), ra(), sa() (+2 more)

### Community 34 - "Chart.js Layout and Scales"
Cohesion: 0.24
Nodes (5): addBox(), reset(), start(), u(), vn()

### Community 35 - "Chart.js Rendering Pipeline"
Cohesion: 0.21
Nodes (7): beforeDatasetDraw(), beforeDatasetsDraw(), beforeDraw(), da(), Ie(), na(), ze()

### Community 36 - "Binary Classification Pipeline"
Cohesion: 0.23
Nodes (11): class_means(), evaluate(), lopo_classify(), main(), make_binary(), model_binary.py — Stage 3 (binary reframe): predict LOW vs HIGH writing effort.…, Return (df, y) with effort collapsed to LOW(0)/HIGH(1)., Leave-One-Participant-Out CV; pool out-of-fold labels + probabilities. (+3 more)

### Community 37 - "Chart.js Visualization Core 37"
Cohesion: 0.27
Nodes (9): e(), gi(), mi(), o(), on(), un(), vi(), xn() (+1 more)

### Community 38 - "Chart.js Visualization Core 38"
Cohesion: 0.18
Nodes (4): bo, et(), H(), mo()

### Community 41 - "Chart.js Rendering Pipeline"
Cohesion: 0.24
Nodes (3): aa(), afterDatasetsUpdate(), generateLabels()

### Community 42 - "Chart.js Rendering Pipeline"
Cohesion: 0.22
Nodes (3): Mn(), removeBox(), stop()

### Community 43 - "Chart.js Event Handling"
Cohesion: 0.20
Nodes (8): ho(), inXRange(), inYRange(), K(), li(), oo(), tt(), Y()

### Community 44 - "Browser Keystroke Logger"
Cohesion: 0.24
Nodes (5): flagBlockedPaste(), pickVariation(), record(), renderPreview(), selectLevel()

### Community 45 - "external_experiment.py"
Cohesion: 0.29
Nodes (9): feature_means_by_emotion(), load(), lopo(), main(), external_experiment.py — Step 4/5: a SEPARATE experiment on the external…, run_task(), sklearn_dummy, sklearn_metrics (+1 more)

### Community 46 - "Chart.js Visualization Core 46"
Cohesion: 0.20
Nodes (3): getValueForPixel(), j(), ko

### Community 47 - "Chart.js Visualization Core 47"
Cohesion: 0.25
Nodes (5): pi(), r(), vo(), wo(), zi()

### Community 50 - "Chart.js Visualization Core 50"
Cohesion: 0.40
Nodes (4): ei(), je(), qe(), ti()

### Community 51 - "tasks.py"
Cohesion: 0.33
Nodes (5): first_variation(), tasks.py — writing-task prompts for the PROTOTYPE, copied here so the prototype…, Return the first variation id for a level (simple, deterministic pick)., UI View: Live, UI View: Write

### Community 53 - "Chart.js Visualization Core 53"
Cohesion: 0.40
Nodes (3): es(), Qi(), ts()

### Community 55 - "admin.js"
Cohesion: 0.83
Nodes (3): esc(), loadKeystrokes(), stat()

### Community 56 - "Repository Guidelines & Rules"
Cohesion: 0.67
Nodes (3): Repository Guidelines, Repository Guidelines & Standards, Testing and PR Guidelines

### Community 57 - "Primary Statistical Analysis"
Cohesion: 0.67
Nodes (3): Final Analysis — Primary Data (Self-Perceived Writing Effort), Effort-Typing Hypotheses Evaluation, Linear Regression vs Random Forest Evaluation

## Knowledge Gaps
- **39 isolated node(s):** `Document: graphify.md`, `Graphify Rules & Workflow Instructions`, `Workflow: graphify`, `Graphify Rules & Workflow Instructions`, `Repository Guidelines & Standards` (+34 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 233 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ns()` connect `Chart.js Color Utilities` to `Chart.js Rendering Pipeline`, `Chart.js Color Utilities`, `Chart.js Color Utilities`, `Chart.js Animation Engine`, `Chart.js Rendering Pipeline`, `Chart.js Layout and Scales`, `Chart.js Visualization Core 21`, `Chart.js Visualization Core 54`, `Chart.js Visualization Core 29`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Why does `an()` connect `Chart.js Event Handling` to `Chart.js Color Utilities`, `Chart.js Color Utilities`, `Chart.js Layout and Scales`, `Chart.js Rendering Pipeline`, `Chart.js Rendering Pipeline`, `Chart.js Rendering Pipeline`, `Chart.js Event Handling`, `Chart.js Visualization Core 50`, `Chart.js Visualization Core 20`, `Chart.js Visualization Core 53`, `Chart.js Visualization Core 29`, `Chart.js Animation Engine`, `Chart.js Rendering Pipeline`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Why does `zt()` connect `Chart.js Color Utilities` to `Chart.js Animation Engine`, `Chart.js Color Utilities`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `s()` (e.g. with `beforeUpdate()` and `da()`) actually correct?**
  _`s()` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `o()` (e.g. with `ai()` and `da()`) actually correct?**
  _`o()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `a()` (e.g. with `ai()` and `cn()`) actually correct?**
  _`a()` has 15 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Document: graphify.md`, `Graphify Rules & Workflow Instructions`, `Workflow: graphify` to the rest of the system?**
  _39 weakly-connected nodes found - possible documentation gaps or missing edges._