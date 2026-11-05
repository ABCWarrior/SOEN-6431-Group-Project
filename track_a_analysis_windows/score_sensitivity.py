"""Check how much the Track A hotspot ranking depends on the chosen weights.

The Track A report uses WEIGHTS = 0.30/0.20/0.15/0.15/0.10/0.10 (scripts/hotspots.py)
for six signals. This script holds the six signals fixed and only changes the weights,
then asks whether the top of the ranking moves. Standard library only; it reads
track_a_analysis/raw/debt_summary_by_file.csv, so no tools need to be re-run.

Usage (from the repository root):
    python track_a_analysis_windows/score_sensitivity.py
"""
import csv
import random
from pathlib import Path

KEYS = ["complexity_debt", "churn_commits", "missed_stmts", "violations", "dup_lines", "coupling"]
BASE = {
    "complexity_debt": .30,
    "churn_commits": .20,
    "missed_stmts": .15,
    "violations": .15,
    "dup_lines": .10,
    "coupling": .10,
}

# This file lives in <repo>/track_a_analysis_windows/, the CSV in <repo>/track_a_analysis/raw/
CSV = Path(__file__).resolve().parents[1] / "track_a_analysis" / "raw" / "debt_summary_by_file.csv"
rows = list(csv.DictReader(CSV.open(encoding="utf-8")))

# min-max normalise each signal, as hotspots.py does
lo = {k: min(float(r[k]) for r in rows) for k in KEYS}
hi = {k: max(float(r[k]) for r in rows) for k in KEYS}
norm = {
    k: {
        r["file"]: (float(r[k]) - lo[k]) / (hi[k] - lo[k]) if hi[k] > lo[k] else 0.0
        for r in rows
    }
    for k in KEYS
}


def ranking(weights):
    scored = [
        (sum(w * norm[k][r["file"]] for k, w in weights.items()) * 100, r["file"])
        for r in rows
    ]
    return [f for _, f in sorted(scored, reverse=True)]


def short(files):
    return [f.replace("httpie/", "") for f in files]


# ---- 1. a few named weightings ----------------------------------------------------
SCHEMES = {
    "reported 30/20/15/15/10/10": BASE,
    "complexity down, churn up": {**BASE, "complexity_debt": .15, "churn_commits": .35},
    "churn down, complexity up": {**BASE, "complexity_debt": .40, "churn_commits": .10},
    "equal weights (1/6 each)": {k: 1 / 6 for k in KEYS},
    "spec's four signals only": {k: .25 for k in ("complexity_debt", "churn_commits", "missed_stmts", "dup_lines")},
    "complexity only": {**{k: 0.0 for k in KEYS}, "complexity_debt": 1.0},
    "churn only": {**{k: 0.0 for k in KEYS}, "churn_commits": 1.0},
}
top = {name: ranking(w)[:3] for name, w in SCHEMES.items()}
for name in SCHEMES:
    print(f"{name:28s} top3 = {short(top[name])}")
same = sum(1 for t in top.values() if t == top["reported 30/20/15/15/10/10"])
print(f"\nSame top 3 as reported: {same} of {len(SCHEMES)} weightings")

# ---- 2. random weightings ---------------------------------------------------------
# The share of random weightings that put core.py first depends on how the random
# weights are drawn, so two ways are shown (5,000 draws each, fixed seed).
N = 5000
FIRST = "httpie/core.py"


def share_first(draw, seed=0):
    random.seed(seed)
    hits = 0
    for _ in range(N):
        w = draw()
        scores = {r["file"]: sum(w[k] * norm[k][r["file"]] for k in KEYS) for r in rows}
        hits += max(scores, key=scores.get) == FIRST
    return hits / N


def each_uniform():
    x = {k: random.random() for k in KEYS}
    s = sum(x.values())
    return {k: v / s for k, v in x.items()}


def simplex_uniform():
    x = {k: random.expovariate(1) for k in KEYS}
    s = sum(x.values())
    return {k: v / s for k, v in x.items()}


print(f"\n{FIRST} ranked first in {N} random weightings:")
print(f"  each weight uniform(0,1), then normalised : {share_first(each_uniform):.1%}")
print(f"  uniform over all possible weight sets      : {share_first(simplex_uniform):.1%}")
