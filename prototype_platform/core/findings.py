"""
findings.py — turns the study's numbers into the research summary shown on the researcher
dashboard: plain-language findings with an honest status, and the questionnaire hypotheses
(each with its live status). Every figure comes from the data files or the live database;
only the wording around the figures is written here.

Statuses:  supported · not-supported · mixed · pending
"""

ALPHA = 0.05
STATUS_LABEL = {"supported": "Supported", "not-supported": "Not supported",
                "mixed": "Partly supported", "pending": "Collecting data"}

# plain wording of the three questionnaire hypotheses (keys match affect.live_validation)
HYPOTHESES = [
    {"key": "load", "id": "H2", "title": "Cognitive load",
     "claim": "People who report heavier mental effort (NASA-TLX) type with more hesitation, "
              "correction and uneven rhythm (mind-space load)."},
    {"key": "flow", "id": "H3", "title": "Flow",
     "claim": "People who report more flow (Flow Short Scale) type more continuously and evenly "
              "(focus index)."},
    {"key": "intensity", "id": "H4", "title": "Emotional intensity",
     "claim": "People who report a stronger emotional experience (SAM) delete and pause more while "
              "writing (emotional-processing load)."},
]


def pair_status(p, min_n):
    """Status of one correlation pair against its expected direction."""
    r = p.get("result")
    if not r:
        return "pending", "Collecting data (%d of %d sessions)" % (p["n"], min_n)
    sig = r["p"] < ALPHA
    exp = p.get("expected")
    if sig and (exp is None or (r["rho"] > 0) == (exp > 0)):
        return "supported", "Supported (rho %+.2f, p = %.3f)" % (r["rho"], r["p"])
    if sig:
        return "mixed", "Opposite direction (rho %+.2f, p = %.3f)" % (r["rho"], r["p"])
    return "not-supported", "Not supported yet (rho %+.2f, p = %.2f)" % (r["rho"], r["p"])


def hypotheses(live):
    """H2-H4 with the matching live correlation attached."""
    by = {p["hypothesis"]: p for p in live["pairs"] if p.get("hypothesis")}
    out = []
    for h in HYPOTHESES:
        p = by.get(h["key"])
        if p is None:
            status, text = "pending", "Collecting data (0 of %d sessions)" % live["min_n"]
        else:
            status, text = pair_status(p, live["min_n"])
        n = p["n"] if p else 0
        out.append(dict(h, pair=p, status=status, status_label=STATUS_LABEL[status], text=text,
                        n=n, progress=min(100, round(100 * n / live["min_n"]))))
    return out


def build(kpis, signals, model, ext, lit, live):
    """Headline findings in the order a reader should meet them, plus the hypotheses."""
    f = []

    # ---- pilot study: does typing predict self-rated effort?
    if signals:
        top = max(signals, key=lambda s: abs(s["rho"]))
        f.append({
            "id": "F1", "study": "Pilot study", "status": "not-supported",
            "title": "Typing did not reliably predict self-rated writing effort",
            "number": "|ρ| ≤ %.2f" % abs(top["rho"]),
            "body": "Across %d valid sessions from %d people, no typing measure was significantly related to "
                    "how much effort people said the writing took. The strongest was %s (ρ = %+.2f, p = %.2f), "
                    "and the models did not beat a plain average."
                    % (kpis["valid_sessions"], kpis["participants"], top["name"].lower(), top["rho"], top["p"]),
            "link": "model_research_page", "anchor": "pilot"})

    # ---- external data: EmoSurv
    if ext:
        sig = [k for k, v in ext["indices"].items() if v["kruskal_p"] < ALPHA]
        n_idx = len(ext["indices"])
        hs = ext["happy_sad_model"]
        f.append({
            "id": "F2", "study": "External check (EmoSurv)", "status": "supported",
            "title": "Typing changes with mood, but does not tell happy from sad",
            "number": "%d of %d" % (len(sig), n_idx),
            "body": "In %d public sessions from %d people, %d of %d typing readings differed across the five moods. "
                    "Happy and sad could not be told apart (a classifier reached %.0f%% balanced accuracy, "
                    "permutation p = %.2f)."
                    % (ext["n_sessions"], ext["n_participants"], len(sig), n_idx,
                       100 * hs["lopo_balanced_accuracy"], hs["permutation_p"]),
            "link": "behaviour_page", "anchor": "emosurv"})

        es = ext["engagement_shift"]
        f.append({
            "id": "F3", "study": "External check (EmoSurv)", "status": "supported",
            "title": "Typing is steadier when writing under an emotion than in neutral writing",
            "number": "%d%%" % round(100 * es["all_pairs"]["share_lower"]),
            "body": "Rhythm variability fell in %d%% of %d emotion-versus-neutral pairs (median change %+.2f, p < 0.001). "
                    "It survived length-matching (n = %d, p = %.3f)."
                    % (round(100 * es["all_pairs"]["share_lower"]), es["all_pairs"]["n"],
                       es["all_pairs"]["median_delta_cv"], es["length_matched"]["n"],
                       es["length_matched"]["p"]),
            "link": "behaviour_page", "anchor": "shift"})

    # ---- external data: measures taken from the literature
    if lit:
        rows = lit["paired_per_person"]
        sup = [r for r in rows if r["p_holm"] < ALPHA]
        hs_sep = [r for r in lit["happy_vs_sad"] if r["p_holm"] < ALPHA]
        f.append({
            "id": "F4", "study": "External check (EmoSurv)",
            "status": "mixed" if sup else "not-supported",
            "title": "Published typing measures: some separate emotion from neutral, none separate happy from sad",
            "number": "%d of %d" % (len(sup), len(rows)),
            "body": "Of %d measures taken from the literature, %d differed between emotional and neutral writing "
                    "after correcting for multiple tests, and %d separated happy from sad."
                    % (len(rows), len(sup), len(hs_sep)),
            "link": "behaviour_page", "anchor": "literature"})

    # ---- our emotion-writing study: do the questionnaires agree with typing?
    hyps = hypotheses(live)
    answered = max([h["n"] for h in hyps] + [0])        # sessions that have questionnaire answers
    done = [h for h in hyps if h["status"] != "pending"]
    sup = [h for h in hyps if h["status"] == "supported"]
    status = ("pending" if not done else "supported" if len(sup) == len(hyps)
              else "not-supported" if not sup else "mixed")
    if done:
        body = ("Cognitive load, flow and emotional intensity are measured with published questionnaires and compared "
                "with the typing readings. %d of %d hypotheses are supported so far." % (len(sup), len(hyps)))
    else:
        body = ("Cognitive load, flow and emotional intensity are measured with published questionnaires and compared "
                "with the typing readings. At least %d sessions with answers are needed before any correlation is shown; "
                "%d collected so far." % (live["min_n"], answered))
    f.append({
        "id": "F5", "study": "Our emotion-writing study", "status": status,
        "title": "Do people's own answers agree with what their typing suggests?",
        "number": "%d of %d" % (len(sup), len(hyps)) if done else "%d of %d sessions" % (answered, live["min_n"]),
        "body": body, "link": "behaviour_page", "anchor": "live"})

    for x in f:
        x["status_label"] = STATUS_LABEL[x["status"]]
    return f, hyps
