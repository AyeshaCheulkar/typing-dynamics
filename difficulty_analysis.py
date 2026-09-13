"""
difficulty_analysis.py — does task difficulty (Easy vs Moderate) relate to
self-rated writing effort and typing behaviour? Uses the EXISTING labelled
sessions (features.csv); no new data.

Easy vs Moderate compared with Mann-Whitney U (small, non-normal samples).
Writes difficulty_analysis.png. Target = self-perceived writing effort.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

BLUE, AMBER, INK, GREY = "#2563eb", "#d97706", "#0f1b33", "#c7d2ec"

MEASURES = [
    ("effort_rating", "Self-rated effort"),
    ("pause_time_ratio", "Share of time paused"),
    ("n_long_pause_per_100", "Long pauses /100"),
    ("revisions_per_100", "Revisions /100"),
    ("active_time_s", "Writing time (s)"),
    ("chars_per_sec", "Typing speed"),
]


def run():
    df = pd.read_csv("features.csv")
    v = df[df["behavioural_valid"] == 1]
    easy = v[v["difficulty"] == "Easy"]
    mod = v[v["difficulty"] == "Moderate"]

    print(f"Easy n={len(easy)} | Moderate n={len(mod)}\n")
    print(f"{'measure':>22} {'Easy':>8} {'Moderate':>9} {'U-test p':>9}")
    rows = []
    for col, name in MEASURES:
        e, m = easy[col], mod[col]
        try:
            _, p = stats.mannwhitneyu(e, m, alternative="two-sided")
        except ValueError:
            p = float("nan")
        rows.append((name, e.mean(), m.mean(), p))
        print(f"{name:>22} {e.mean():>8.2f} {m.mean():>9.2f} {p:>9.3f}")

    # figure: (A) effort by difficulty with points, (B) z-scored behaviour profile
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.6))
    fig.suptitle("Task difficulty: Easy vs Moderate  (valid sessions)",
                 fontsize=13, fontweight="bold")

    # A: self-rated effort
    for i, (g, c) in enumerate([(easy, BLUE), (mod, AMBER)]):
        ax1.bar(i, g["effort_rating"].mean(), 0.55, color=c, zorder=2)
        ax1.scatter(np.random.default_rng(1).normal(i, 0.05, len(g)),
                    g["effort_rating"], color=INK, alpha=.5, s=22, zorder=3)
    ax1.set_xticks([0, 1]); ax1.set_xticklabels(["Easy", "Moderate"])
    ax1.set_ylabel("Self-rated effort (1-5)"); ax1.set_ylim(0, 5.4)
    ax1.set_title("Self-rated effort by difficulty", fontsize=10.5)
    ax1.text(0, easy["effort_rating"].mean() + .15, f"{easy['effort_rating'].mean():.2f}", ha="center")
    ax1.text(1, mod["effort_rating"].mean() + .15, f"{mod['effort_rating'].mean():.2f}", ha="center")
    for s in ("top", "right"): ax1.spines[s].set_visible(False)

    # B: z-scored behaviour means by difficulty
    beh = [("pause_time_ratio", "Time paused"), ("n_long_pause_per_100", "Long pauses"),
           ("revisions_per_100", "Revisions"), ("active_time_s", "Writing time"),
           ("chars_per_sec", "Speed")]
    labels = [b[1] for b in beh]
    ez, mz = [], []
    for col, _ in beh:
        mu, sd = v[col].mean(), v[col].std() or 1
        ez.append((easy[col].mean() - mu) / sd)
        mz.append((mod[col].mean() - mu) / sd)
    x = np.arange(len(labels)); w = 0.38
    ax2.bar(x - w/2, ez, w, label="Easy", color=BLUE, zorder=2)
    ax2.bar(x + w/2, mz, w, label="Moderate", color=AMBER, zorder=2)
    ax2.axhline(0, color=INK, lw=1)
    ax2.set_xticks(x); ax2.set_xticklabels(labels, rotation=20, ha="right", fontsize=8.5)
    ax2.set_ylabel("Mean (standardised)")
    ax2.set_title("Behaviour profile by difficulty (z-scored)", fontsize=10.5)
    ax2.legend(frameon=False)
    for s in ("top", "right"): ax2.spines[s].set_visible(False)

    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig("difficulty_analysis.png", dpi=150, bbox_inches="tight")
    print("\nsaved difficulty_analysis.png")
    return rows


if __name__ == "__main__":
    run()
