# Research plan: what we analyse, which papers support it, what gap we fill, what we build

Living document. The **Build log** (section 10) is updated whenever something is built or decided.
Last updated: 2026-10-19.

Source-checking key: **[V]** = page or abstract opened and checked; **[S]** = record confirmed only in
search results (full text not read); **[M]** = from memory, must be checked before submission.
Longer notes on each source: `LITERATURE.md`. Formulas: `FORMULAS.md`.

---

## 1. One-paragraph summary (what to say if asked)

We built a writing platform that records keystroke timing while a person writes about a happy or a sad
moment, then asks ten short questions from published instruments (SAM, NASA-TLX, Flow Short Scale).
Our question is **whether typing behaviour reflects how a person felt and how hard they worked while
writing, measured against validated self-report rather than a single made-up effort rating**. We use
transparent, literature-based typing measures (not a black-box model), test them against the
questionnaire scores with participant-aware statistics, and use public datasets only to check that our
typing measures behave as published work says they should. Claims stay at the level of "typing
patterns associated with self-reported state". We do not diagnose anything.

## 2. What we already have and what it can and cannot do

| Data | Size | Has | Cannot do |
|---|---|---|---|
| Pilot study (`data/study/`), frozen | 32 sessions, 25 included, 22 valid keystroke streams, 17 people | Keystrokes + one self-rated writing effort (1-5), two task difficulties | Cannot be changed or extended. Too small for a model: no model beat a predict-the-mean baseline (RF MAE 0.94-1.10 vs 0.90-0.94). 0 of 9 correlations significant (need \|r\| >= 0.42). |
| EmoSurv (public) | 190 usable free-text sessions, 81 people | Keystroke intervals + induced emotion (neutral, anger, happy, calm, sad) | No effort, load or flow labels. Absolute timestamps corrupted, so we rebuild the timeline from the down-to-down interval column. |
| KeyRecs (public) | 197 free-text sessions, 99 people | Keystroke digraph timings, demographics | No state labels at all. Used only to confirm our features have realistic values. |
| New prototype data (`data/databases/prototype.db`) | 5 sessions so far | Keystrokes + happy/sad + SAM + NASA-TLX + Flow answers | Needs at least 30 sessions to say anything (section 6). |

Consequence: **the pilot result stays in the thesis as an honest negative/pilot finding. The new
contribution comes from the new data plus the external checks.**

## 3. Papers we rely on

### 3.1 Typing and emotion
| Paper | What it found | Why we need it | Status |
|---|---|---|---|
| Epp, Lippold & Mandryk (2011), CHI, doi:10.1145/1978942.1979046 | Typing rhythm on an ordinary keyboard, with self-reported emotion; several two-class emotion models reached 77-88% | Origin of rhythm-based emotion sensing; supports using rhythm variability | [V] abstract |
| Lee, Tsui & Hsiao (2015), PLoS ONE 10(6):e0129056 | 52 students, emotion induced by sounds; **arousal** affected key duration and latency, valence did not; effects small relative to individual differences; authors suggest personalised models | Tells us to expect small effects, to report arousal separately from valence, and to use within-person comparison | [V] page opened |
| Kołakowska & Landowska (2021), Sensors 21(17):5963 | 49 students wrote opinions on their most positive and most negative learning experiences; typing speed differed between the two (paired p = 0.0068); backspace and delete did not; only spacebar frequency survived multiple-test correction; positive-vs-negative classification F1 about 0.63, described as "not impressive" | Closest design to ours (recall a positive or negative experience and write). Their weak result is the realistic benchmark | [V] page opened |
| Maalej & Kallel (2020), EmoSurv, IEEE DataPort, doi:10.21227/eae6-pk42 | Public typing data with induced emotions, 124 people, fixed and free text | Our external emotion dataset | [S] dataset used directly |
| Vizer, Zhou & Sears (2009), IJHCS 67(10):870-886 | Cognitive and physical stress vs neutral from keystroke and language features | Stress and load measured from free text | [S] |
| Bixler & D'Mello (2013), IUI, doi:10.1145/2449396.2449426 | 44 people wrote essays; boredom vs engagement detected from keystrokes, task appraisals and stable traits, 11-38% above chance, generalised to new people | Precedent for **engagement/flow from keystrokes during writing** | [S] |

### 3.2 Typing and cognitive load / writing process
| Paper | What it found | Why we need it | Status |
|---|---|---|---|
| Conijn, Roeser & van Zaanen (2019), Reading & Writing, doi:10.1007/s11145-019-09953-8 | Mean inter-key interval was stable across tasks of different cognitive demand; between-word and between-sentence timing varied | Warns that mean speed is mostly a trait of the typist. Motivates word-boundary pause features | [V] abstract |
| Conijn, Dux Speltz & Chukharev-Hudilainen (2021), Reading & Writing | Automatic detection of revision events from keystroke logs (7,120 annotated revisions, 65 students) | Basis for a better revision measure than counting backspaces | [S] |
| Tian, Kim & Crossley (2024), J. Writing Research, doi:10.17239/jowr-2024.15.03.01 | P-bursts (production between pauses over 2 s) as a fluency / load indicator | Justifies our 2-second thinking-pause threshold | [V] abstract |
| Leijten & Van Waes (2013), Written Communication 30(3):358-392 | Standard writing-process measures (Inputlog) | Standard reference for pauses, bursts, revisions | [S] |
| Schütz, Cherif, Sayffaerth, Weber & Chiossi (2026), arXiv:2606.28090 (preprint, not peer reviewed) | 36 people prompting an LLM; harder tasks gave more keystrokes, slower typing, more pauses and higher NASA-TLX | Recent evidence that keystroke measures track NASA-TLX workload | [V] abstract page |
| Kuvar et al. (2022), UMUAI, doi:10.1007/s11257-022-09340-z | Mind wandering predicted from keystrokes, modest agreement | Shows modest accuracy is the norm for state detection | [S] |
| Lau (2018), CMU dissertation | Stress via keystroke dynamics, per-person and universal markers | Per-person effects dominate | [S] |
| Zulueta et al. (2018), JMIR 20(7):e241 | Inter-key delay and backspace ratio vs clinician mood ratings, within person | Feature definitions | [V] |

### 3.3 Questionnaires (ground-truth labels)
| Instrument | Use | Status |
|---|---|---|
| Self-Assessment Manikin, Bradley & Lang (1994) | Valence and arousal | [M] |
| Raw NASA-TLX, Hart & Staveland (1988); Hart (2006) | Cognitive load (mental demand, effort, frustration) | [M] |
| Flow Short Scale, Rheinberg, Vollmeyer & Engeser (2003) | Flow | [M] |

Items are shortened to a 5-point scale. This is stated wherever scores appear and listed as a limitation.

### 3.4 Text side
Hutto & Gilbert (2014) VADER [M]; Rude, Gortner & Pennebaker (2004), first-person pronouns [M].

## 3.5 Secondary datasets added 2026-10-19 (downloaded to `data/external/`)

| Dataset | What it has | Use in our project | Status |
|---|---|---|---|
| Freihaut & Goritz, "Does People's Keyboard Typing Reflect their Stress Level", Zenodo 4445197 (lab study) | 53 people, each typed in a **high-stress (HS) and a low-stress (LS) condition** (within-person); keyboard features (latency mean/SD, backspaces, dwell time) plus SAM, heart rate, EDA as manipulation check | Stress check for the load and mind-space readings | [V] data read. Raw keystroke file in the repository is only an LFS pointer, so only the feature table is usable. Licence on Zenodo is listed as apgl-v3 |
| Inputlog Copy Task Corpus, Zenodo 5803401 (English subset) | 491 sessions with typing speed (cpm), computer type (laptop / desktop), keyboard layout, familiarity, per-sentence inter-key interval stats | Justifies the **typing-skill and keyboard questions** and gives skill-matched reference ranges | [V] data read; CC-BY-4.0 |
| EmoSurv, KeyRecs | already in use | emotion check and feature validity | see 3.1 |

Looked at and rejected: Inputlog EFL revision set (PDF reports only), audio-description scriptwriting set
(phase durations only, no keystroke timing), KEasyLogger (digraphs only, 17 people, no state labels),
Kaggle writing-process data (needs a Kaggle login), DUX (the data sits inside a 4.2 GB reproduction kit; labels not checked).

### First results from these datasets
- **Stress (Freihaut, n = 53 paired):** typing was slightly slower under high stress (median +12.9 ms between keys, Wilcoxon p = 0.017, not corrected for the other tests). Rhythm variability (CV of key latency) did not differ (p = 0.49), nor did backspaces (p = 0.81). The task was typing fixed patterns, not free writing.
- **Why we ask typing skill and keyboard (Inputlog copy task, n = 491):**
  - Slow, middle and fast typists (thirds by speed) had median key intervals of 188, 148 and 124 ms and rhythm variability of 0.59, 0.49 and 0.48.
  - Laptop users (n = 242) had shorter intervals than desktop users (n = 238): 142 vs 164 ms, p < 0.001. This is confounded with who uses which device, so it justifies **adjusting for** device, not a causal claim.
  - Faster typists have slightly steadier rhythm (Spearman rho = -0.12, p = 0.007).
  So any typing reading must be compared with people of similar speed and device, otherwise the typist is being measured, not the writing.

## 4. Research gap

From the sources above (search was limited, so this is **"we did not find"**, not "does not exist"):

1. **Most keystroke-emotion work uses a single kind of label.** Emotion classifiers (Epp, Lee,
   Kolakowska) use emotion labels only; load studies (Conijn, Schutz) use task difficulty or NASA-TLX only.
   We found no study that measures **emotional intensity, cognitive load and flow together, in the same
   free-writing session, with validated questionnaires**, and compares each with typing.
2. **Effects are small and mostly between-person.** Lee et al. and Kolakowska & Landowska both report weak
   effects against individual variability. Few studies report their negative results in full or control for
   typing skill, keyboard and passage length. We do.
3. **Weak evidence behind popular "focus" and "stress" scores.** Dashboards often show such scores without
   checking them against a validated label. We test every typing index against NASA-TLX, Flow and SAM and
   say plainly when it fails.
4. **Reproducible, open and small.** Everything is transparent equal-weight formulas, with confound
   controls and the results published even when null.

**Gap statement for the thesis:** *"Whether simple, interpretable typing measures from a single free-writing
session track validated self-reports of emotional intensity, cognitive load and flow, once typing skill,
keyboard and text length are controlled, and how far those findings agree with public keystroke data."*

## 5. Research questions and hypotheses

| ID | Question | Typing measure | Label | Expected |
|---|---|---|---|---|
| H1 | Is rhythm steadier under emotion? | Rhythm variability (CV of inter-key interval) | Condition (emotional vs neutral) | Lower CV in emotional writing. **Supported on EmoSurv** (108 pairs, p < 0.0001). Cannot be tested on our own data until a baseline passage exists (warm-up step was removed). |
| H2 | Does heavier load show in typing? | Mind-space load index; hesitation | NASA-TLX score | Positive correlation |
| H3 | Does flow show in typing? | Focus index | Flow Short Scale | Positive |
| H4 | Does emotional intensity show in typing? | Processing-load index | SAM (felt strength, arousal) | Positive |
| H5 (exploratory) | Do happy and sad moments type differently? | All measures | Task chosen | EmoSurv says no; test only as exploratory |
| H6 (replication) | Did the pilot direction (more pausing with more effort) replicate? | Share of time paused | NASA-TLX effort item | Positive, directionally |

## 6. Analysis plan (fixed before collecting more data)

**Inclusion:** keystroke stream valid (at least 40 key-downs, at most 30% unidentified keys); desktop keyboard only.

**Controls:** typing skill (touch / mixed / hunt-and-peck), keyboard (laptop / external), passage length
(words). Mean key speed is treated as a typist trait, not a state, following Conijn et al. (2019).

**Statistics:**
1. Spearman correlation per hypothesis pair, with a 95% bootstrap interval.
2. Partial / adjusted version controlling for skill, keyboard and length.
3. If participants have several sessions: a mixed model with a random intercept per participant (the same
   approach used on the pilot).
4. Holm correction across the hypotheses. Report effect sizes with intervals, not only p-values.
5. Everything is reported as supported, partly supported or not supported, including nulls.

**Sample size:** at 80% power and alpha 0.05, a true correlation of 0.5 needs about 29 sessions, 0.4 needs
about 47. **Target at least 30 valid sessions from at least 20 different people; the current 5 is far below.**
The admin page already refuses to show a correlation below 8 sessions.

**External checks (public data, never mixed into our labels):**
- EmoSurv: do our measures vary with induced emotion as published work says? (done: H1 holds; happy vs sad does not separate.)
- KeyRecs and the pilot: do our features have realistic values? (done: median inter-key interval 209 / 206 / 174 ms.)

## 7. Model plan: what changes

| Before | After |
|---|---|
| One target: self-rated writing effort 1-5, trained on 22 sessions, never beat the mean | **Targets are the validated scores**: cognitive load (NASA-TLX), flow, emotional intensity |
| Random Forest / Linear Regression as the headline | **Headline is the interpretable indices and their tested association with the labels.** A model is a secondary check |
| Effort estimate shown to participants (unreliable) | Shown as a range (model error about 1.1 points) next to the person's own effort answer, with SHAP drivers; stored for every session so predicted vs actual can be re-checked as data arrives |

If and when there are about 30 or more sessions: train a small, regularised model (ridge or random forest) to predict each state,
compare with a predict-the-mean baseline and with the single-index baseline, using leave-one-participant-out validation.
Report it whether or not it wins. SHAP only if a model beats the baseline. No model is trained before then, because
the pilot already showed that doing so on 22 sessions produces noise.

Planned features to add (from the literature): between-word pause time, between-sentence pause time
(Conijn 2019); P-burst length (Tian 2024); revision events instead of backspace counts (Conijn 2021).

## 8. Report design (DECIDED 2026-10-19; replaces the earlier proposal)

Participant report: plain analysis only. No formulas, no disclaimer boilerplate. (Revised 2026-10-19: the effort estimate returns as a card on the Writing tab, shown as a range with the person's own NASA-TLX effort answer beside it and a SHAP bar chart; the prediction is stored with every session.)
Wording is confident and descriptive (what the typing shows), never a claim the data cannot carry.

**Typing skill and keyboard:** shown on the report as context. Key speed is compared with typists on the same kind of
computer (laptop vs desktop/external) from the Inputlog copy-task data; skill words the comparison. The readings themselves are not rescaled
(no skill or device labels exist in the pilot or EmoSurv data to base an adjustment on).

**Tab 1: Writing**
1. Quick analysis: three plain headline sentences + metric cards (words, time, speed, pauses, additions, deletions).
2. Graphs: typing timeline; compare-with-others bars (pilot writers + public free-text sessions; key speed vs same-keyboard typists);
   pause breakdown (within word / between words / between sentences); writing over time.
3. Model analysis: driver bars (what pushed the engagement reading, plain names) + 2-3 tips tied to the top drivers and what the person did.

**Tab 2: Emotional**
1. For focus, cognitive load, emotional intensity: paired bars (typing reading vs own answer, 0-100) + one-line verdict.
2. Emotional engagement reading (resemblance to emotional vs neutral writing, %), with driver bars.
3. Text tone of their words; valence answer (SAM) against text tone; mood-passage context vs EmoSurv happy/sad.
4. Personal comparison only on the participant side. Across-participant relationships live on the researcher dashboard.

**Researcher dashboard (5 pages):** Overview | Participants (tabs: Pilot study, New sessions) | Behaviour research | Model research | Export.
Model research = one card per measure (formula, why chosen, source + verification status, test results, verdict), datasets used and rejected,
models (engagement model weights and tests), a "tested and set aside" section (pilot effort model, stress model, happy-vs-sad), and skill/keyboard handling.
Methodology, Model card and Research results pages are absorbed into it.

**Cleanup:** delete replaced code and templates; keep old database columns; keep pilot effort model files for the set-aside section;
back up prototype.db, then clear its 5 test sessions at the end (after building and testing on a copy).

## 9. What we can and cannot claim

- Can: typing rhythm steadier under induced emotion (EmoSurv, replicated over three analyses); typing measures
  show how a person wrote; our questionnaire-vs-typing results, once the sample exists, with intervals.
- Cannot: diagnose stress, anxiety, depression; tell happy from sad by typing; claim the pilot effort model works;
  claim any index measures "focus" or "stress" until it passes H2-H4.

## 10. Build log

- [x] 2026-08: Stage-1 data collection, pilot 25 sessions, analysis and effort model (negative result)
- [x] 2026-08: external validation on EmoSurv and KeyRecs
- [x] 2026-10: prototype platform, happy/sad task, indices, SAM / NASA-TLX / Flow questionnaires
- [x] 2026-10-19: repo reorganised (`data/`, `research/`, `prototype_platform/`)
- [x] 2026-10-19: this plan written, literature extended (Kolakowska 2021, Lee 2015, Schutz 2026, Bixler 2013, Conijn 2021)
- [x] 2026-10-19: secondary datasets searched and downloaded (Freihaut stress study, Inputlog copy-task corpus); first results in 3.5
- [x] 2026-10-19: `research/build_state_models.py` built engagement model (EmoSurv, held-out-participant AUC 0.60, permutation p = 0.05; rhythm variability is the main driver) and skill-matched key-speed norms (Inputlog). Tested and rejected as headline: Freihaut stress model (AUC 0.51-0.58 on 924 people) and any pilot effort model (AUC 0.13-0.32, no signal)
- [x] 2026-10-19: report design decided with user (section 8)
- [x] 2026-10-19: built per section 8: `writing_actions` (additions, deletions, pause location) in research/features.py; `core/analysis.py`; two-tab participant report; Model research page (`core/measures.py`); admin merged to 5 pages (Participants has Pilot and New-sessions tabs); dead baseline/effort code removed; tests in `prototype_platform/tests/`; test sessions backed up and cleared
- [ ] Not yet visually checked: admin pages (only the participant report was rendered and viewed)
- [ ] Add word-boundary pause and P-burst features to `research/features.py`; re-run external checks
- [ ] Collect at least 30 valid sessions from at least 20 people (landing page, login and writing flow stay unchanged)
- [ ] Run H2-H4, H6 with the section 6 protocol; add mixed model to the dashboard
- [ ] Verify every [S] and [M] source before submission
- [ ] Decide on a within-person baseline (needed to test H1 on our own data)

## 11. Questions a supervisor is likely to ask

- **Which papers did you read?** Section 3. The closest to our design is Kolakowska & Landowska (2021).
- **What is the gap?** Section 4: no study found that tests emotion, load and flow together, in free writing,
  against validated questionnaires, with controls and honest nulls.
- **Why did the effort model fail?** 22 sessions, one self-rated target, large between-person differences; Lee (2015) and
  Conijn (2019) predict exactly this. We now use validated labels and report effect sizes.
- **Why no deep learning?** Sample size. A transparent index that can be checked against a label is more defensible than a model trained on tens of sessions.
- **What if the new data also shows nothing?** It is still a result. We report it with intervals, in line with Kolakowska & Landowska's own weak findings.
