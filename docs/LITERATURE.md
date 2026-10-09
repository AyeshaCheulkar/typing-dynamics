# Literature basis and validation of the behaviour formulas

Scope: which typing features the literature links to emotion, stress, cognitive load and
attention, how each is defined, and whether it holds up on our external data (EmoSurv).
Regenerate the numbers with `python prototype_platform/validate_literature_formulas.py`.

## 1. Sources and verification status

"Verified" = bibliographic record and abstract checked against OpenAlex / Europe PMC (DOI
resolved). "Partly" = record confirmed but full text not read; claims come from the abstract
or a search summary. "Not verified" = cited from memory — confirm before submission.

| Source | What it gives us | Status |
|---|---|---|
| Epp, Lippold & Mandryk (2011), CHI, doi:10.1145/1978942.1979046 | Rhythm of typing on a standard keyboard, with self-reported emotion, classified 15 emotional states. 2-level classifiers for confidence, hesitance, nervousness, relaxation, sadness, tiredness reached 77–88%; anger and excitement 84%. Field study, free text, small sample. | Verified (abstract) |
| Zulueta et al. (2018), JMIR 20(7):e241, doi:10.2196/jmir.9775 | Mobile keystroke metadata vs clinician mood ratings (bipolar disorder, 8 weeks, within-person). Feature definitions: **average interkey delay** (mean seconds between keystrokes), **backspace ratio** (backspaces / total keypresses), **autocorrect rate**, session length, circadian similarity, accelerometer. Mixed models: HDRS R²c = .63; YMRS R² = .34. | Verified (abstract + variable table) |
| Vizer, Zhou & Sears (2009), IJHCS 67(10):870–886, doi:10.1016/j.ijhcs.2009.07.005 | Cognitive and physical stress vs neutral from keystroke + linguistic features of free text; 24 participants, 42 parameters, 75% (cognitive) and 62.5% (physical) per search summary. | Partly (record verified; numbers from a search summary) |
| Conijn, Roeser & van Zaanen (2019), Reading & Writing, doi:10.1007/s11145-019-09953-8 | Which keystroke features respond to task cognitive demand: the **average of all inter-keystroke intervals was stable across tasks**; time between words and (sub)sentences differed only between copy and academic tasks. | Verified (abstract) |
| Tian, Kim & Crossley (2023/24), J. Writing Research, doi:10.17239/jowr-2024.15.03.01 | Defines **P-bursts** as production delimited by pauses longer than 2 s; used as a fluency/cognitive-load indicator. | Verified (abstract) |
| Leijten & Van Waes (2013), Written Communication 30(3):358–392 (Inputlog) | Standard writing-process measures (pauses, bursts, revisions). | Partly (cited in a verified paper; not opened) |
| Chenoweth & Hayes (2001), Written Communication 18(1) | Origin of burst/fluency measures. | Not verified |
| Kuvar et al. (2022), User Modeling and User-Adapted Interaction, doi:10.1007/s11257-022-09340-z | Task-unrelated thought (mind wandering) predicted from keystrokes, modest agreement (thesis version reports kappa ≈ 0.34; a snippet said 0.363). | Partly (title/DOI verified; abstract and window length not read) |
| Lau (2018), CMU dissertation, doi:10.1184/r1/6723227.v3 | Stress via keystroke dynamics, 116 subjects; looks for per-person and universal markers. | Partly (abstract only) |
| Maalej & Kallel (2020), Intelligent Environments + EmoSurv, IEEE DataPort | Our external emotion dataset: 124 participants, neutral then induced anger/happiness/calm/sadness, fixed and free text. | Partly (search summaries; dataset used directly) |
| Khare (2026), TypeState, Zenodo | Single-author pilot; says stress may reduce typing-rhythm variance. Data inspected: 35 usable sessions from about 8 devices, Android, copy-typing, no participant IDs. **Not usable for validation**; cited only as a hint. | Verified (record + data inspected) |
| Hutto & Gilbert (2014), VADER; Rude, Gortner & Pennebaker (2004), first-person pronouns | Text side of the report. | Not verified |
| Books | None verified yet. Candidate: Lindgren & Sullivan, *Observing Writing* (Brill, 2019). | Not verified |

## 2. Formulas, as the literature defines them, and what held up on EmoSurv

Test: each feature, same checks, Holm correction across 12 features. Within-person =
emotional block minus the same person's neutral block (Wilcoxon). EmoSurv's neutral block is
about 1.8x longer than the emotional blocks, so the length-matched and per-person rows are the
trustworthy ones for length-dependent features.

| Feature (source) | Per person (n=67), Holm p | Length-matched (n=38), Holm p | Happy vs sad, Holm p | Verdict |
|---|---|---|---|---|
| Rhythm variability, CV = std/mean of inter-key interval (Epp 2011; Khare hint) | **0.023** (steadier, 69% of people) | 0.27 (same direction, 68%) | 0.07 (effect 0.41) | **Supported within person** |
| Mean inter-key delay (Zulueta 2018) | 1.0 | 1.0 | 1.0 | Not supported (matches Conijn 2019: stable) |
| Median inter-key delay (Epp 2011) | 1.0 | 1.0 | 0.25 | Not supported |
| Backspace/delete ratio (Zulueta 2018; Vizer 2009) | 1.0 | 1.0 | 1.0 | Not supported |
| Cognitive pauses per 100 keys, gap ≥ 2 s (P-burst boundary) | 0.43 | 1.0 | 0.88 | Not supported once length is controlled |
| Time in pauses, gap ≥ 0.5 s | 0.43 | 1.0 | 1.0 | Not supported once length is controlled |
| Revision bursts per 100 keys (Conijn 2019) | 1.0 | 1.0 | 1.0 | Not supported |
| Typing speed (Epp 2011; Lau 2018) | 0.43 | 1.0 | 1.0 | Not supported once length is controlled |
| Our composites: focus, hesitation, mind-space load | 0.023, 0.015, 0.009 | 1.0 | 0.45, 0.96, 0.40 | Differ emotional vs neutral per person; no happy/sad separation |

What this does and does not show:
- The one robust, literature-consistent signal is **rhythm variability**: people type with a
  steadier rhythm when writing under an induced emotion than in their own neutral block.
- **Nothing separates happy from sad** on this dataset after correction (n = 32 vs 29).
- Mean/median key delay, backspace use and revisions do not move across these conditions, which
  agrees with Conijn et al. (mean interval is a stable trait of the typist, not of the task).
- Our composite indices differ between neutral and emotional writing per person, but they are
  built partly from variability and pauses, so they add no information beyond those features.
- None of this is validation against **focus** or **stress** labels. EmoSurv has emotion labels
  only. That validation needs our research-mode self-ratings.

## 3. What the report may claim now

- Supported: the **typing-rhythm steadiness** reading, within a person, against a baseline.
- Descriptive only: speed, pauses, corrections, text tone.
- Unvalidated proxies (label as such): focus index, mind-space load.
- Not supported: separating happy from sad by typing alone; the exploratory happy-like/sad-like
  model; the effort estimate.

## 4. Next validation steps

1. Collect research-mode sessions (target 30 or more) with mood, focus, mind-wandering, tension
   ratings and the interruption flag; test every formula against those labels with the same
   Holm-corrected protocol.
2. Add word-boundary pause features (Conijn 2019) to the feature extractor and test them.
3. Decide how the within-person baseline is obtained now that the warm-up passage is removed.
4. Open and verify the sources marked "Partly" or "Not verified".
