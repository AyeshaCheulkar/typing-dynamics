"""
build_emotion_validation.py — one-off build step for the emotion-writing extension.

Reads (READ-ONLY, from the repo root):
  ../external_features_emosurv.csv   EmoSurv sessions already run through the SAME
                                     features.py extractor (emotion = induced label)
  ../features.csv                    our own pilot-study sessions

Writes (inside prototype_platform/):
  reference_stats.json       quantile tables used to turn features into 0-100 indices
                             ("study" = our pilot data, "emosurv" = EmoSurv)
  emotion_validation.json    aggregate validation numbers shown on the admin page
  emotion_model.pkl          Random Forest: happy-like vs sad-like typing (EmoSurv)

Nothing here modifies the Stage-1 app, the effort model or any source data.
Run:  python prototype_platform/build_emotion_validation.py
"""

import json
import os
import sys

import joblib
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import LeaveOneGroupOut

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import behaviour as bh                       # noqa: E402
from model import FEATURES                   # noqa: E402  (shared feature list)

EMO_NAMES = {"H": "Happy", "S": "Sad", "N": "Neutral", "A": "Angry", "C": "Calm"}
SEED = 7


def load_emosurv():
    df = pd.read_csv(os.path.join(ROOT, "external_features_emosurv.csv"))
    df = df[df["behavioural_valid"] == 1].copy()
    df["participant"] = df["external_session"].astype(str).str.split("|").str[0]
    return df.reset_index(drop=True)


def load_study():
    df = pd.read_csv(os.path.join(ROOT, "features.csv"))
    return df[df["behavioural_valid"] == 1].copy().reset_index(drop=True)


def add_indices(df, ref):
    rows = [bh.compute_indices(r.to_dict(), ref) for _, r in df.iterrows()]
    for k in bh.INDEX_ORDER:
        df[k] = [r[k] for r in rows]
    return df


def rank_biserial(a, b):
    """Effect size for Mann-Whitney U (positive = a tends to be higher)."""
    u = stats.mannwhitneyu(a, b, alternative="two-sided").statistic
    return 2 * u / (len(a) * len(b)) - 1


def index_by_emotion(df):
    out = {}
    for k in bh.INDEX_ORDER:
        med = {EMO_NAMES[e]: round(float(df.loc[df.emotion == e, k].median()), 1)
               for e in "HSNAC" if (df.emotion == e).any()}
        groups = [df.loc[df.emotion == e, k].values for e in "HSNAC"
                  if (df.emotion == e).sum() > 2]
        kw = stats.kruskal(*groups)
        # paired happy vs sad within participant
        wide = df[df.emotion.isin(["H", "S"])].pivot_table(
            index="participant", columns="emotion", values=k, aggfunc="mean").dropna()
        if len(wide) >= 6:
            w = stats.wilcoxon(wide["H"], wide["S"])
            paired = {"n": int(len(wide)), "p": round(float(w.pvalue), 4),
                      "median_diff_H_minus_S": round(float((wide["H"] - wide["S"]).median()), 1)}
        else:
            paired = None
        out[k] = {"medians": med, "kruskal_p": round(float(kw.pvalue), 4),
                  "happy_vs_sad": paired}
    return out


def happy_sad_model(df):
    hs = df[df.emotion.isin(["H", "S"])].copy()
    X = hs[FEATURES].to_numpy()
    y = (hs.emotion == "S").astype(int).to_numpy()      # 1 = sad-like
    groups = hs["participant"].to_numpy()
    preds, base_preds, truth = [], [], []
    for tr, te in LeaveOneGroupOut().split(X, y, groups):
        rf = RandomForestClassifier(n_estimators=300, min_samples_leaf=3,
                                    class_weight="balanced", random_state=SEED)
        rf.fit(X[tr], y[tr])
        preds.extend(rf.predict(X[te]))
        d = DummyClassifier(strategy="most_frequent").fit(X[tr], y[tr])
        base_preds.extend(d.predict(X[te]))
        truth.extend(y[te])
    bal = balanced_accuracy_score(truth, preds)
    base = balanced_accuracy_score(truth, base_preds)
    # permutation test on the LOPO balanced accuracy (labels shuffled within person)
    rng = np.random.default_rng(SEED)
    null = []
    for _ in range(60):
        yp = y.copy()
        for g in np.unique(groups):
            idx = np.where(groups == g)[0]
            yp[idx] = rng.permutation(yp[idx])
        pp = []
        tt = []
        for tr, te in LeaveOneGroupOut().split(X, yp, groups):
            rf = RandomForestClassifier(n_estimators=60, min_samples_leaf=3,
                                        class_weight="balanced", random_state=SEED)
            rf.fit(X[tr], yp[tr])
            pp.extend(rf.predict(X[te])); tt.extend(yp[te])
        null.append(balanced_accuracy_score(tt, pp))
    p_perm = (1 + sum(n >= bal for n in null)) / (1 + len(null))
    final = RandomForestClassifier(n_estimators=400, min_samples_leaf=3,
                                   class_weight="balanced", random_state=SEED)
    final.fit(X, y)
    joblib.dump({"model": final, "features": FEATURES,
                 "classes": {0: "happy-like", 1: "sad-like"}},
                os.path.join(HERE, "emotion_model.pkl"))
    return {"n_sessions": int(len(hs)), "n_participants": int(hs.participant.nunique()),
            "lopo_balanced_accuracy": round(float(bal), 3),
            "baseline_balanced_accuracy": round(float(base), 3),
            "permutation_p": round(float(p_perm), 3)}


def engagement_shift(df):
    """Within-person test: is rhythm variability (CV of the inter-key interval) lower
    when writing under an induced emotion than in the SAME person's neutral block?
    Reported on all pairs, length-matched pairs (the neutral block is ~2x longer, which
    inflates pause effects) and one averaged pair per participant."""
    df = df.copy()
    df["cv"] = df["std_iki_ms"] / df["mean_iki_ms"]
    neu = df[df.emotion == "N"].groupby("participant").mean(numeric_only=True)
    emo = df[df.emotion.isin(list("HSAC")) & df.participant.isin(neu.index)].copy()
    emo["base_cv"] = neu.loc[emo.participant, "cv"].values
    emo["len_ratio"] = emo["n_keydown"].values / neu.loc[emo.participant, "n_keydown"].values
    emo["d"] = emo["cv"] - emo["base_cv"]

    def summ(sub, per_person=False):
        if per_person:
            d = sub.groupby("participant")["d"].mean()
        else:
            d = sub["d"]
        d = d.to_numpy()
        return {"n": int(len(d)), "median_delta_cv": round(float(np.median(d)), 3),
                "share_lower": round(float(np.mean(d < 0)), 2),
                "p": round(float(stats.wilcoxon(d).pvalue), 4)}
    matched = emo[(emo.len_ratio > 0.6) & (emo.len_ratio < 1.67)]
    return {"hypothesis": "Rhythm variability (CV) is lower in emotional writing than in the same person's neutral baseline.",
            "all_pairs": summ(emo), "length_matched": summ(matched),
            "per_participant": summ(emo, True),
            "median_length_ratio": round(float(emo.len_ratio.median()), 2),
            "note": "Pause-count and pause-time effects vanish after length matching; only rhythm variability survives."}


def rule_evaluation(df):
    """Evaluate the transparent engagement-shift RULE: given a person's baseline and a
    second passage, 'the passage with the LOWER rhythm CV is the emotional one'.
    Two-alternative forced-choice accuracy, cluster-bootstrap CI (by participant) and a
    binomial test; also compared with a multi-feature logistic model (LOPO)."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    df = df.copy()
    df["cv"] = df["std_iki_ms"] / df["mean_iki_ms"]
    fe = ["cv", "n_long_pause_per_100", "pause_time_ratio", "chars_per_sec",
          "delete_rate", "revisions_per_100", "median_iki_ms"]
    neu = df[df.emotion == "N"].groupby("participant")[fe + ["n_keydown"]].mean()
    emo = df[df.emotion.isin(list("HSAC")) & df.participant.isin(neu.index)].copy()
    ratio_len = emo["n_keydown"].values / neu.loc[emo.participant, "n_keydown"].values
    cv_ratio = emo["cv"].values / neu.loc[emo.participant, "cv"].values
    matched = (ratio_len > 0.6) & (ratio_len < 1.67)
    d_cv = cv_ratio - 1.0
    rng = np.random.default_rng(SEED)

    def acc(mask, label):
        d = d_cv[mask]
        pids = emo.participant.to_numpy()[mask]
        groups = {p: d[pids == p] for p in np.unique(pids)}
        keys = list(groups)
        bs = []
        for _ in range(2000):
            pick = rng.choice(len(keys), len(keys))
            v = np.concatenate([groups[keys[i]] for i in pick])
            bs.append(float(np.mean(v < 0)))
        k = int((d < 0).sum())
        return {"label": label, "n": int(len(d)), "participants": int(len(keys)),
                "accuracy": round(k / len(d), 3),
                "ci95": [round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)],
                "binom_p": round(float(stats.binomtest(k, len(d), 0.5).pvalue), 4)}
    rows = [acc(np.ones(len(d_cv), bool), "All pairs"),
            acc(matched, "Length-matched pairs")]
    for e, name in (("H", "Happy"), ("S", "Sad"), ("A", "Angry"), ("C", "Calm")):
        rows.append(acc(emo.emotion.to_numpy() == e, "Only " + name))

    # multi-feature comparison on symmetrised baseline-differences
    X = np.column_stack([np.log1p(emo[f].values) - np.log1p(neu.loc[emo.participant, f].values)
                         for f in fe])
    pid = emo.participant.to_numpy()
    ok = []
    for p in np.unique(pid):
        tr = pid != p
        Xtr = np.vstack([X[tr], -X[tr]])
        ytr = np.r_[np.ones(tr.sum()), np.zeros(tr.sum())]
        sc = StandardScaler().fit(Xtr)
        m = LogisticRegression(C=0.3, max_iter=500, fit_intercept=False).fit(sc.transform(Xtr), ytr)
        ok += list(m.predict_proba(sc.transform(X[~tr]))[:, 1] > 0.5)
    thresholds = {str(int(t * 100)): round(float(np.mean(cv_ratio <= 1 - t)), 2)
                  for t in (0.10, 0.20, 0.30)}
    return {"rule": "emotional passage = the one with lower rhythm CV than the person's baseline",
            "rows": rows, "multi_feature_accuracy": round(float(np.mean(ok)), 3),
            "sensitivity_at_drop_pct": thresholds,
            "limitation": "Two-alternative test (needs the baseline and a second passage). "
                          "Specificity on a single new passage is not estimable from EmoSurv."}


def main():
    emo = load_emosurv()
    if "--only-shift" in sys.argv:
        path = os.path.join(HERE, "emotion_validation.json")
        with open(path, encoding="utf-8") as fh:
            result = json.load(fh)
        result["engagement_shift"] = engagement_shift(emo)
        result["engagement_rule"] = rule_evaluation(emo)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)
        print(json.dumps(result["engagement_rule"], indent=2))
        return
    study = load_study()

    ref_study = bh.make_reference(study.to_dict("records"))
    ref_emo = bh.make_reference(emo.to_dict("records"))
    with open(bh.REFERENCE_PATH, "w", encoding="utf-8") as fh:
        json.dump({"study": ref_study, "emosurv": ref_emo,
                   "n_study": int(len(study)), "n_emosurv": int(len(emo))}, fh)

    emo = add_indices(emo, ref_emo)
    result = {
        "dataset": "EmoSurv (external, supporting data only)",
        "n_sessions": int(len(emo)), "n_participants": int(emo.participant.nunique()),
        "emotion_counts": {EMO_NAMES[e]: int((emo.emotion == e).sum()) for e in "HSNAC"},
        "indices": index_by_emotion(emo),
        "happy_sad_model": happy_sad_model(emo),
        "engagement_shift": engagement_shift(emo),
        "engagement_rule": rule_evaluation(emo),
    }
    with open(os.path.join(HERE, "emotion_validation.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
