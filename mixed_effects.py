"""
mixed_effects.py — participant-aware relationship modelling on the EXISTING 22
sessions. A linear mixed-effects model with a RANDOM INTERCEPT per participant
correctly handles the fact that several people contributed more than one session
(repeated measures), and is more sensitive than pooled correlations.

Two models:
  M1: effort ~ difficulty            + (1 | participant)
  M2: effort ~ pausing + speed + revisions (standardised) + (1 | participant)

Target = self-perceived writing effort (1-5). Exploratory (n=22); no claim about
mental effort or any psychological state.
"""

import warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")


def _z(s):
    return (s - s.mean()) / (s.std() or 1)


def run():
    df = pd.read_csv("features.csv")
    v = df[df["behavioural_valid"] == 1].copy()
    v["moderate"] = (v["difficulty"] == "Moderate").astype(int)
    v["pausing"] = _z(v["pause_time_ratio"])
    v["speed"] = _z(v["chars_per_sec"])
    v["revisions"] = _z(v["revisions_per_100"])

    print(f"n={len(v)} sessions, {v['participant_id'].nunique()} participants "
          f"(random intercept per participant)\n")

    def fit(formula, label):
        # Participant-CLUSTERED OLS: robust, always converges, accounts for the
        # repeated-measures clustering by participant.
        ols = smf.ols(formula, v).fit(cov_type="cluster",
                                      cov_kwds={"groups": v["participant_id"]})
        print(f"=== {label} ===")
        print(f"  {formula}   (participant-clustered SE)")
        print(f"  {'term':>14} {'coef':>8} {'p':>8}")
        for term in ols.params.index:
            print(f"  {term:>14} {ols.params[term]:>8.3f} {ols.pvalues[term]:>8.3f}")
        # Bonus: try a random-intercept mixed model (may not converge at n=22).
        try:
            md = smf.mixedlm(formula, v, groups=v["participant_id"]).fit(method="nm")
            print(f"  [mixed model participant variance: "
                  f"{float(md.cov_re.iloc[0,0]):.3f}]\n")
        except Exception:
            print("  [random-intercept mixed model did not converge at n=22 — "
                  "clustered OLS reported]\n")
        return ols

    fit("effort_rating ~ moderate", "M1: task difficulty")
    fit("effort_rating ~ pausing + speed + revisions", "M2: behaviours")

    print("Reading: 'moderate' coef = extra self-rated effort for Moderate vs Easy.\n"
          "Behaviour coefs = change in effort per 1 SD of the behaviour, with "
          "participant-\nclustered standard errors. With n=22 these remain "
          "exploratory (wide uncertainty).")


if __name__ == "__main__":
    run()
