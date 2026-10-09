# Formulas and calculations

Everything the prototype calculates, how, and where it appears. Participants never see the
formulas; they see the results in plain words (`prototype_platform/core/plain_report.py`,
`templates/participant/report.html`). Section 5 maps **every item in the participant report** to its
calculation. Provenance is marked: **[lit]** the definition comes from published work,
**[ours]** our own choice (unvalidated), **[data]** chosen or tested on our data.

Code: `research/features.py` (shared measurements), `prototype_platform/core/behaviour.py` (indices),
`core/questionnaire.py` (questionnaire scores), `core/affect.py` (text tone), `core/recommendations.py`
(comparisons and suggestions), `core/predict.py` (timeline, effort estimate), `research/explain.py` (explanation).

---

## 1. Keystroke capture and validity
- Each keydown/keyup is logged with a millisecond timestamp, the key, and the caret position.
  Paste is blocked and logged.
- A session is **behaviourally valid** if it has at least **40 key presses** and at most
  **30%** "Unidentified" keys (mobile/IME keyboards). If invalid, the indices and the effort
  estimate are suppressed. [ours; protects data quality]

## 2. Base measurements (from `research/features.py`)
Let the key-down times be t₁ … tₙ (ms) and the gaps IKIᵢ = tᵢ − tᵢ₋₁.

| Measure | Calculation | Basis |
|---|---|---|
| Active time | tₙ − t₁ | [ours] |
| Typing speed | characters in final text ÷ active seconds | [lit] Epp 2011, Vizer 2009 |
| Mean / median / SD of IKI | mean, median, population SD of the gaps | [lit] Epp 2011; Zulueta 2018 (average interkey delay) |
| Pause | IKI ≥ 500 ms | [ours] Stage-1 setting |
| Long ("thinking") pause | IKI ≥ 2000 ms | [lit] P-burst boundary, Leijten & Van Waes; Tian et al. |
| Long pauses per 100 keys | 100 × (number of IKI ≥ 2 s) ÷ n | derived |
| Short pauses per 100 keys | 100 × (number of IKI ≥ 0.5 s) ÷ n | derived |
| Time paused (ratio) | sum of all IKI ≥ 0.5 s ÷ active time | derived [lit-style] |
| Longest pause | max IKI | derived |
| Correction rate | (Backspace + Delete key presses) ÷ n | [lit] Zulueta 2018 backspace ratio |
| Revision bursts | number of runs of consecutive Backspace/Delete | [lit] R-bursts, Conijn 2019 |
| Revisions per 100 keys | 100 × revision bursts ÷ n | derived |
| Rhythm variability (CV) | SD of IKI ÷ mean of IKI | [data] supported on EmoSurv; motivated by Epp 2011 |
| Word count | text split on whitespace | — |

## 3. Reference samples and percentiles
Two reference sets are used, both our 22 valid pilot sessions:
1. **Study quartiles** (`features.csv` via `recommendations.py`): a value is "lower than most"
   below Q25, "higher than most" above Q75, otherwise "within the typical range". Its
   percentile = the share of pilot sessions with a value ≤ yours. Used by the "How you wrote"
   grid, the radar, "Session at a glance", the suggestions, and the plain-language cards.
2. **Quantile table** (`reference_stats.json` via `behaviour.py`): 101 quantiles per measure.
   pct(x) = 100 × (mid-rank of x in the table) ÷ 101, with ties given the mid-rank. Used by the
   indices in section 4.

## 4. The five indices (`behaviour.py`) [ours]
Equal weights, no fitted parameters. pct(·) as in section 3.2.

| Index | Formula |
|---|---|
| Hesitation | mean( pct(long pauses/100), pct(longest pause), pct(time paused) ) |
| Self-correction | mean( pct(correction rate), pct(revisions/100) ) |
| Irregularity | pct(CV) |
| **Focus** | 100 − mean( pct(time paused), pct(CV), pct(long pauses/100) ) |
| **Mind-space load** | mean( Hesitation, Self-correction, Irregularity ) |

Cut-offs used in the report (thirds of the range, not validated thresholds):
- Focus: ≤ 40 "stop-and-start", ≥ 60 "steady", otherwise "mixed".
- Mind-space: ≤ 40 "settled", ≥ 60 "strained-looking", otherwise "in between".
- Meter marker position = the index value (clamped to 3–97).
- Component lines ("What shaped this"): a percentile below 34 is "low", above 66 "high".

## 5. Every item in the participant report

| Report item | How it is calculated |
|---|---|
| **Top strip: Words** | word count |
| **Writing time** | active time, shown as m s |
| **Characters/sec** | typing speed |
| **Keystrokes** | n (key presses) |
| **Time paused** | round(100 × time-paused ratio) % |
| **"How you wrote" grid** (speed, writing time, long pauses, time paused, backspace/delete, revisions) | each value from section 2; band by Q25/Q75 of the pilot (section 3.1); bar width = percentile |
| **Headline sentence** | Focus ≥ 60 → "flowed steadily"; ≤ 40 → "stop-and-start"; else "some steady stretches and some stops" |
| **Focus meter** | Focus index (section 4); level and marker position as above |
| **Mind-space meter** | Mind-space index (section 4) |
| **"What shaped this" lines** | Focus: levels of pct(time paused), pct(CV), pct(long pauses). Mind-space: levels of the Hesitation, Self-correction and Irregularity indices |
| **Pace card** | speed; chip and bar from its pilot percentile (below 34 lower, above 66 higher) |
| **Stopping to think card** | count = round(long pauses per 100 × n ÷ 100); chip from the percentile of long pauses per 100 |
| **Steadiness card** | Irregularity < 34 "even", > 66 "uneven", otherwise typical; no bar (direction would be ambiguous) |
| **Going back card** | count = number of revision bursts; chip from the percentile of revisions per 100 |
| **Typing context line** | typing style and keyboard as answered; extra caution text if "hunt-and-peck" |
| **Tone of your words** | see section 6 |
| **"How sure are we?" box** | fixed text; no calculation |
| **Behaviour profile (radar)** | five axes = pilot percentiles of: speed, time paused, writing time, revision rate, correction rate. Sentence: an axis ≥ 66 reads "more …", ≤ 33 reads "less/little …", otherwise "closer to the study average" |
| **Writing timeline** | each gap ≥ 2000 ms is a "pause"; a gap next to a Backspace/Delete is a "revision"; all other gaps are "typing". Neighbouring spans of the same kind merge; spans under 0.4% of the session are dropped. Shows the pause count and the longest pause |
| **Self-rated effort** (research mode only) | the participant's own 1–5 answer |
| **Experimental estimate** | Random Forest (400 trees, min leaf 2, seed 42) on 9 typing features: speed, mean IKI, SD of IKI, longest pause, long pauses/100, time paused, correction rate, revisions/100, active time. Trained on the valid pilot sessions (effort 1–5). Output clipped to 1–5; band = "lower" if below the training mean − 0.5, "higher" if above + 0.5, otherwise "around average"; difference = estimate − training mean |
| **Why the model estimated this** | SHAP values (TreeExplainer) for the 9 features, top 5 by absolute size shown with sign. If SHAP is not installed: standardised linear-regression coefficient × standardised feature value |
| **Suggestions** | rule-based, from pilot quartiles, at most 5 (see below) |
| **Session at a glance** | band (Q25/Q75) for typing speed, pausing, revisions and writing time |

Suggestion rules (top quartile = ≥ Q75, bottom quartile = ≤ Q25 of the pilot):
1. revision/correction rate in the top quartile → fewer edits while drafting;
2. long pauses or time paused in the top quartile → outline first;
3. SD of IKI in the top quartile → even out the rhythm;
4. longest pause in the top quartile → placeholder and move on;
5. short pauses in the top quartile → write in fuller units;
6. speed in the bottom quartile → typing fluency;
7. active time in the top quartile with word count ≤ pilot median → timebox;
8. word count in the bottom quartile → develop points;
9. revisions and correction both in the bottom quartile → quick proofread;
10. long pauses in the bottom quartile and speed ≥ median → steady-flow note.
If none fire, one neutral "balanced process" message is shown.

## 6. Tone of the words (`affect.py`)
- Needs at least 8 words. The text is split into sentences (at . ! ? or new lines).
- VADER gives each sentence a compound score from −1 to +1; **tone score = mean over sentences**.
  Positive if ≥ +0.15, negative if ≤ −0.15, otherwise mixed. [lit: Hutto & Gilbert 2014; cut-offs ours]
- **Positive/negative word share** = percentage of words whose VADER lexicon value is ≥ +1.5 / ≤ −1.5.
- Computed but not shown to participants: first-person word rate (I, me, my…) and vocabulary variety
  (unique words ÷ words).
- "This matches the happy/sad moment you chose" compares the tone with the chosen moment.

## 7. Research-only calculations (researcher pages, not the participant report)
- **Engagement-shift rule:** the emotional passage is the one with the lower CV than the person's
  baseline; a drop of at least 10% flags "engagement-like". On EmoSurv it picked the emotional
  passage in 73% of 108 pairs (95% CI 63–82%) and 68% of 38 length-matched pairs. Needs a baseline,
  so it does not run in the current participant flow. [data]
- **Literature-feature test (`validate_literature_formulas.py`):** each feature, within person
  (Wilcoxon signed-rank on emotional minus neutral), on all pairs, length-matched pairs
  (0.6–1.67× keystrokes) and one mean per person; happy vs sad by Mann–Whitney with rank-biserial
  effect size; Holm correction across the 12 features.
- **Happy-like vs sad-like model:** Random Forest on EmoSurv, leave-one-participant-out balanced
  accuracy 0.685, permutation p = 0.34 (not distinguishable from chance).
- **Live validation:** Spearman correlation between participants' answers and the indices (shown
  only from 8 sessions). The adjusted version regresses typing style and keyboard (dummy-coded) out
  of both variables, then takes Spearman on the residuals; its p-value is approximate.
- **Replication test of the shift rule:** Wilcoxon on (emotional CV − baseline CV) over
  baseline-and-emotional pairs, interrupted sessions excluded.
- **Effort model (Stage 3):** leave-one-participant-out MAE 1.10 versus 0.94 for predicting the mean;
  R² −0.70 versus −0.12. It does not beat the baseline.

## 8. What is solid, and what is not
- **From the literature (definitions):** key-to-key delay, backspace ratio, 2 s pause boundary,
  revision bursts.
- **Supported on our external data:** rhythm variability, within person (Holm p = 0.023).
- **Ours and unvalidated:** the five indices, their equal weights, all cut-offs (34/66, 40/60,
  ±0.15, ±1.5), the suggestion rules, the Q25/Q75 bands. These are why the focus and mind-space
  readings are labelled "Early evidence".
- **Reference samples are small** (22 pilot sessions), and percentile comparisons are relative to them.

---

## 6. Post-writing questionnaires (ground-truth labels) — `prototype_platform/core/questionnaire.py`
All items use a 1–5 scale (shortened from the published 7/9/21-point versions). [lit] instruments, [ours] shortening.

| State | Instrument | Score |
|---|---|---|
| Emotional intensity | Self-Assessment Manikin, Bradley & Lang 1994 | mean(felt strongly, arousal); valence kept separate |
| Cognitive load | Raw NASA-TLX, Hart 2006 (Hart & Staveland 1988) | mean(mental demand, effort, frustration) |
| Flow state | Flow Short Scale, Rheinberg, Vollmeyer & Engeser 2003 | mean(fluent, concentrate, absorbed, time distortion) |

Typing-side counterparts (`behaviour.py`): cognitive load ↔ mind-space load; flow ↔ focus index;
emotional intensity ↔ emotional-processing load = mean(hesitation, self-correction) **[ours, hypothesis]**.
The admin Behaviour page reports Spearman ρ (raw and adjusted for typing style/keyboard) for each pair; nothing is
claimed until n ≥ 8.
