"""
behaviour.py — transparent behavioural indices computed from the keystroke
features (Option 1 of the emotion-writing extension).

Every index is an EQUAL-WEIGHT mean of percentile ranks against a reference
distribution (no fitted weights, nothing hidden), so each one can be written as a
one-line formula in the report:

  hesitation   = mean( pct(long_pauses/100), pct(max_pause), pct(pause_time_ratio) )
  correction   = mean( pct(delete_rate), pct(revisions/100) )
  irregularity = pct( CV of inter-key interval = std_iki / mean_iki )
  focus        = 100 - mean( pct(pause_time_ratio), pct(CV), pct(long_pauses/100) )
  mind_space   = mean( hesitation, correction, irregularity )   (stress proxy)

Feature choice follows the keystroke-emotion / stress literature (Epp et al. 2011;
Vizer et al. 2009): pause frequency and length, key latency / rhythm variability,
and backspace/delete use are the signals most often tied to affective state.

These are RELATIVE, research-grade proxies — not a clinical measure.
"""

import bisect
import json
import os

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
REFERENCE_PATH = os.path.join(_HERE, "reference_stats.json")

# raw feature -> (reference column, transform)
COMPONENTS = ["pause_time_ratio", "rhythm_cv", "n_long_pause_per_100",
              "max_pause_ms", "delete_rate", "revisions_per_100"]

INDEX_META = {
    "focus": {
        "label": "Focus index", "higher": "steadier, more continuous writing",
        "formula": "100 − mean(pct(time paused), pct(rhythm CV), pct(long pauses))"},
    "hesitation": {
        "label": "Hesitation / load", "higher": "more and longer thinking pauses",
        "formula": "mean(pct(long pauses), pct(longest pause), pct(time paused))"},
    "correction": {
        "label": "Self-correction", "higher": "more deleting and revising",
        "formula": "mean(pct(delete rate), pct(revision bursts))"},
    "irregularity": {
        "label": "Rhythm irregularity", "higher": "less even key-to-key timing",
        "formula": "pct(std ÷ mean of inter-key interval)"},
    "mind_space": {
        "label": "Mind-space load (stress proxy)", "higher": "more strain-like typing",
        "formula": "mean(hesitation, self-correction, rhythm irregularity)"},
}
INDEX_ORDER = ["focus", "hesitation", "correction", "irregularity", "mind_space"]


def rhythm_cv(feats):
    """Coefficient of variation of the inter-key interval (std / mean)."""
    mean = float(feats.get("mean_iki_ms") or 0)
    return float(feats.get("std_iki_ms") or 0) / mean if mean > 0 else 0.0


def component_values(feats):
    """The raw component values the indices are built from."""
    return {
        "pause_time_ratio": float(feats.get("pause_time_ratio") or 0),
        "rhythm_cv": rhythm_cv(feats),
        "n_long_pause_per_100": float(feats.get("n_long_pause_per_100") or 0),
        "max_pause_ms": float(feats.get("max_pause_ms") or 0),
        "delete_rate": float(feats.get("delete_rate") or 0),
        "revisions_per_100": float(feats.get("revisions_per_100") or 0),
    }


def make_reference(rows):
    """Build a reference (101-point quantile table per component) from an iterable
    of feature dicts. Stores aggregates only — no participant-level data."""
    cols = {c: [] for c in COMPONENTS}
    for f in rows:
        for c, v in component_values(f).items():
            cols[c].append(v)
    return {c: [float(x) for x in np.percentile(v, np.linspace(0, 100, 101))]
            for c, v in cols.items() if v}


def load_reference(name="study"):
    try:
        with open(REFERENCE_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh).get(name)
    except (OSError, ValueError):
        return None


def _pct(ref, comp, value):
    """Percentile rank (0-100) of `value` within the reference distribution
    (mid-rank for ties)."""
    q = ref[comp]
    mid = (bisect.bisect_left(q, value) + bisect.bisect_right(q, value)) / 2.0
    return max(0.0, min(100.0, 100.0 * mid / len(q)))


def band(score):
    """Plain-language band for a 0-100 percentile-style score."""
    if score < 34:
        return "Low"
    if score > 66:
        return "High"
    return "Moderate"


def compute_indices(feats, ref=None):
    """Return {index: 0-100 score} for one session, or None when the typing
    capture is invalid / no reference is available."""
    ref = ref or load_reference("study")
    if not ref or not feats.get("behavioural_valid", 1):
        return None
    v = component_values(feats)
    p = {c: _pct(ref, c, v[c]) for c in COMPONENTS}
    hesitation = np.mean([p["n_long_pause_per_100"], p["max_pause_ms"],
                          p["pause_time_ratio"]])
    correction = np.mean([p["delete_rate"], p["revisions_per_100"]])
    irregularity = p["rhythm_cv"]
    focus = 100 - np.mean([p["pause_time_ratio"], p["rhythm_cv"],
                           p["n_long_pause_per_100"]])
    mind = np.mean([hesitation, correction, irregularity])
    return {"focus": round(float(focus), 1),
            "hesitation": round(float(hesitation), 1),
            "correction": round(float(correction), 1),
            "irregularity": round(float(irregularity), 1),
            "mind_space": round(float(mind), 1)}
