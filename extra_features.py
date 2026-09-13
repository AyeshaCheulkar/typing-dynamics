"""
extra_features.py — richer, theory-grounded keystroke features derived from the
EXISTING captured keystrokes (server_keystrokes.csv). No new data is collected;
this only re-processes what was already logged.

New features per session (writing-process research constructs):
  initial_pause_s          — planning pause before the first keystroke
  within_word_pause_pct    — share of long pauses that fall inside a word
  between_word_pause_pct    — share that fall between words
  between_sentence_pause_pct— share that fall between sentences
  n_production_bursts      — bursts of typing with no deletions (P-bursts)
  n_revision_bursts_seg    — bursts that contain deletions (R-bursts)
  mean_prod_burst_chars    — average length of a production burst
  mean_revision_distance   — how far back (chars) edits happen from the frontier

Outputs extra_features.csv and prints Spearman correlations with self-rated effort
(valid sessions only). Target stays "self-perceived writing effort" — no claim
about mental effort or any psychological state.
"""

import csv
import statistics
import pandas as pd
from scipy import stats

PAUSE_LOC_MS = 1000      # threshold for classifying a "pause" by location
BURST_MS = 2000          # threshold that separates typing bursts
DELETE = {"Backspace", "Delete"}
SENTENCE_END = {".", "!", "?"}


def _is_letter(k):
    return isinstance(k, str) and len(k) == 1 and k.isalpha()


def _load_keys():
    by = {}
    with open("server_keystrokes.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["event_type"] != "keydown":
                continue
            by.setdefault(int(r["session_id"]), []).append(
                (int(r["t_ms"]), r["key_value"],
                 int(r["caret_pos"]) if r["caret_pos"] not in ("", None) else None))
    for sid in by:
        by[sid].sort(key=lambda x: x[0])
    return by


def session_extra(evs):
    if len(evs) < 3:
        return None
    t = [e[0] for e in evs]
    keys = [e[1] for e in evs]
    caret = [e[2] for e in evs]

    initial_pause_s = round(t[0] / 1000.0, 1)

    # pause-location classification (gaps >= PAUSE_LOC_MS)
    loc = {"within": 0, "between_word": 0, "between_sentence": 0, "other": 0}
    for i in range(1, len(t)):
        if t[i] - t[i - 1] < PAUSE_LOC_MS:
            continue
        prev, cur = keys[i - 1], keys[i]
        if prev in SENTENCE_END:
            loc["between_sentence"] += 1
        elif prev == " " or cur == " ":
            loc["between_word"] += 1
        elif _is_letter(prev) and _is_letter(cur):
            loc["within"] += 1
        else:
            loc["other"] += 1
    tot = sum(loc.values()) or 1

    # bursts (split at gaps >= BURST_MS); classify by presence of deletions
    prod_bursts, rev_bursts, prod_lens = 0, 0, []
    cur_len, cur_has_del = 0, False
    def close():
        nonlocal prod_bursts, rev_bursts, cur_len, cur_has_del
        if cur_len == 0:
            return
        if cur_has_del:
            rev_bursts += 1
        else:
            prod_bursts += 1
            prod_lens.append(cur_len)
    for i in range(len(t)):
        if i > 0 and t[i] - t[i - 1] >= BURST_MS:
            close(); cur_len, cur_has_del = 0, False
        if keys[i] in DELETE:
            cur_has_del = True
        elif len(str(keys[i])) == 1:
            cur_len += 1
    close()

    # revision distance: for each delete, how far behind the frontier caret is
    frontier, dists = 0, []
    for i in range(len(t)):
        if caret[i] is not None:
            frontier = max(frontier, caret[i])
            if keys[i] in DELETE:
                dists.append(max(0, frontier - caret[i]))

    return {
        "initial_pause_s": initial_pause_s,
        "within_word_pause_pct": round(100 * loc["within"] / tot, 1),
        "between_word_pause_pct": round(100 * loc["between_word"] / tot, 1),
        "between_sentence_pause_pct": round(100 * loc["between_sentence"] / tot, 1),
        "n_production_bursts": prod_bursts,
        "n_revision_bursts_seg": rev_bursts,
        "mean_prod_burst_chars": round(statistics.fmean(prod_lens), 1) if prod_lens else 0,
        "mean_revision_distance": round(statistics.fmean(dists), 1) if dists else 0,
    }


def build():
    keys = _load_keys()
    base = pd.read_csv("features.csv")
    rows = []
    for _, r in base.iterrows():
        ex = session_extra(keys.get(int(r["session_id"]), []))
        if ex is None:
            continue
        rows.append({"session_id": int(r["session_id"]),
                     "participant_id": r["participant_id"],
                     "difficulty": r["difficulty"],
                     "effort_rating": int(r["effort_rating"]),
                     "behavioural_valid": int(r["behavioural_valid"]), **ex})
    out = pd.DataFrame(rows)
    out.to_csv("extra_features.csv", index=False)
    return out


NEW_FEATURES = ["initial_pause_s", "within_word_pause_pct", "between_word_pause_pct",
                "between_sentence_pause_pct", "n_production_bursts",
                "n_revision_bursts_seg", "mean_prod_burst_chars",
                "mean_revision_distance"]

if __name__ == "__main__":
    df = build()
    v = df[df["behavioural_valid"] == 1]
    print(f"extra_features.csv written: {len(df)} sessions ({len(v)} valid).\n")
    print("New features - median (valid) and Spearman rho with self-rated effort:")
    print(f"{'feature':>28} {'median':>8} {'rho':>7} {'p':>7}")
    for c in NEW_FEATURES:
        rho, p = stats.spearmanr(v[c], v["effort_rating"])
        print(f"{c:>28} {v[c].median():>8.1f} {rho:>7.2f} {p:>7.3f}")
    print("\nTarget = self-perceived writing effort (1-5). Exploratory (n=22); no "
          "psychological claims.")
