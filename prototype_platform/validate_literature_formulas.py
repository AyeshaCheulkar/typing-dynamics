"""
validate_literature_formulas.py — tests each literature-derived typing feature on EmoSurv.

Each feature below is defined the way the cited paper defines it (see LITERATURE.md).
Every one is run through the SAME checks, with Holm correction for the number of
features tested (so a feature is only called supported if it survives multiple testing):

  A. Within-person: emotional block vs the SAME person's neutral block
     (Wilcoxon signed-rank on the difference), on
       - all pairs, - length-matched pairs (0.6-1.67x keystrokes), - one mean per person.
     The neutral block is ~1.8x longer, so only the length-matched / per-person rows are
     trusted for features that depend on passage length.
  B. Happy vs Sad, between sessions (Mann-Whitney; effect size = rank-biserial).

Reads (read-only): ../external_features_emosurv.csv, reference_stats.json
Writes: literature_validation.json
Run:    python prototype_platform/validate_literature_formulas.py
"""

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import behaviour as bh  # noqa: E402

# feature -> (label, cited definition, source key)
FEATURES = {
    "mean_iki_s":   ("Mean inter-key delay (s)", "average time between keystrokes", "Zulueta2018"),
    "median_iki_ms": ("Median inter-key delay (ms)", "typical key-to-key latency", "Epp2011"),
    "backspace_ratio": ("Backspace/delete ratio", "backspace presses / total key presses", "Zulueta2018; Vizer2009"),
    "long_pause_100": ("Cognitive pauses per 100 keys", "gaps >= 2 s (P-burst boundary)", "Chenoweth&Hayes2001; Leijten&VanWaes2013"),
    "pause_ratio":  ("Time spent in pauses", "share of time in gaps >= 0.5 s", "Epp2011; Vizer2009"),
    "revision_100": ("Revision bursts per 100 keys", "runs of deletions (R-bursts)", "Conijn2019"),
    "rhythm_cv":    ("Rhythm variability (CV)", "std / mean of inter-key interval", "Epp2011 (variance); Khare2026 (hint)"),
    "chars_per_s":  ("Typing speed (chars/s)", "characters per active second", "Epp2011; Vizer2009; Lau2018"),
    "focus":        ("Focus index (ours)", "composite, see behaviour.py", "this project"),
    "hesitation":   ("Hesitation index (ours)", "composite, see behaviour.py", "this project"),
    "correction":   ("Self-correction index (ours)", "composite, see behaviour.py", "this project"),
    "mind_space":   ("Mind-space load (ours)", "composite, see behaviour.py", "this project"),
}


def holm(ps):
    order = np.argsort(ps)
    m = len(ps)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * ps[i])
        adj[i] = min(1.0, running)
    return adj


def load():
    df = pd.read_csv(os.path.join(ROOT, "external_features_emosurv.csv"))
    df = df[df.behavioural_valid == 1].copy()
    df["pid"] = df.external_session.astype(str).str.split("|").str[0]
    df["mean_iki_s"] = df["mean_iki_ms"] / 1000.0
    df["backspace_ratio"] = df["delete_rate"]
    df["long_pause_100"] = df["n_long_pause_per_100"]
    df["pause_ratio"] = df["pause_time_ratio"]
    df["revision_100"] = df["revisions_per_100"]
    df["rhythm_cv"] = df["std_iki_ms"] / df["mean_iki_ms"]
    df["chars_per_s"] = df["chars_per_sec"]
    with open(bh.REFERENCE_PATH, encoding="utf-8") as fh:
        ref = json.load(fh)["emosurv"]
    idx = [bh.compute_indices(r, ref) for r in df.to_dict("records")]
    for k in bh.INDEX_ORDER:
        df[k] = [i[k] for i in idx]
    return df


def main():
    df = load()
    keys = list(FEATURES)
    neu = df[df.emotion == "N"].groupby("pid")[keys + ["n_keydown"]].mean()
    emo = df[df.emotion.isin(list("HSAC")) & df.pid.isin(neu.index)].copy()
    ratio = emo["n_keydown"].values / neu.loc[emo.pid, "n_keydown"].values
    matched = (ratio > 0.6) & (ratio < 1.67)

    def paired(mask, per_person=False):
        rows = []
        for k in keys:
            d = emo[k].values - neu.loc[emo.pid, k].values
            sub_pid = emo.pid.values
            if per_person:
                s = pd.Series(d[mask], index=sub_pid[mask]).groupby(level=0).mean()
                d = s.values
            else:
                d = d[mask]
            nz = d[d != 0]
            p = float(stats.wilcoxon(d).pvalue) if len(nz) >= 6 else float("nan")
            rows.append({"feature": k, "n": int(len(d)), "median_delta": float(np.median(d)),
                         "share_lower": float(np.mean(d < 0)), "p": p})
        adj = holm(np.array([r["p"] for r in rows]))
        for r, a in zip(rows, adj):
            r["p_holm"] = float(a)
        return rows

    out = {"paired_all": paired(np.ones(len(emo), bool)),
           "paired_matched": paired(matched),
           "paired_per_person": paired(np.ones(len(emo), bool), per_person=True)}

    hs = df[df.emotion.isin(["H", "S"])]
    rows = []
    for k in keys:
        a = hs.loc[hs.emotion == "H", k].values
        b = hs.loc[hs.emotion == "S", k].values
        u = stats.mannwhitneyu(a, b, alternative="two-sided")
        rows.append({"feature": k, "n_happy": int(len(a)), "n_sad": int(len(b)),
                     "median_happy": float(np.median(a)), "median_sad": float(np.median(b)),
                     "rank_biserial": float(2 * u.statistic / (len(a) * len(b)) - 1),
                     "p": float(u.pvalue)})
    adj = holm(np.array([r["p"] for r in rows]))
    for r, a in zip(rows, adj):
        r["p_holm"] = float(a)
    out["happy_vs_sad"] = rows
    out["meta"] = {"features": {k: {"label": v[0], "definition": v[1], "source": v[2]} for k, v in FEATURES.items()},
                   "n_sessions": int(len(df)), "n_participants": int(df.pid.nunique())}
    with open(os.path.join(HERE, "literature_validation.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)

    def show(title, rows, cols):
        print("\n" + title)
        for r in rows:
            print("  %-34s" % FEATURES[r["feature"]][0] + " ".join(
                ("%s=%s" % (c, ("%.3f" % r[c]) if isinstance(r[c], float) else r[c])) for c in cols))
    show("A1 within-person, ALL pairs", out["paired_all"], ["n", "median_delta", "share_lower", "p_holm"])
    show("A2 within-person, LENGTH-MATCHED", out["paired_matched"], ["n", "median_delta", "share_lower", "p_holm"])
    show("A3 within-person, PER PERSON", out["paired_per_person"], ["n", "median_delta", "share_lower", "p_holm"])
    show("B happy vs sad", out["happy_vs_sad"], ["n_happy", "n_sad", "rank_biserial", "p_holm"])


if __name__ == "__main__":
    main()
