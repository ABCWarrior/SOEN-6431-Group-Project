"""Track A - combine every static-analysis report into a per-file debt table + visuals.

Inputs  (track_a_analysis/raw/, produced by run_track_a.sh):
  lizard_functions.csv, radon_mi.json, flake8_complexity.txt, pylint_full.json,
  jscpd_30/jscpd-report.json, git_churn_since2019.csv, coverage.json,
  coupling_modules.csv, import_cycles.txt, [sonar_files.json - optional]

Outputs:
  raw/debt_summary_by_file.csv          full table, all modules
  debt_summary_table.md                 top-15 hotspot table (Markdown)
  figures/debt_heatmap.png              top-20 files x metrics, normalised colour + raw values
  figures/ccn_histogram.png             distribution of function CCN
  figures/top_functions_ccn.png         15 most complex functions vs thresholds
  figures/churn_vs_complexity.png       hotspot quadrant (Tornhill style)

Debt score (0-100) = weighted sum of min-max normalised signals:
  30% complexity debt  (sum over functions of max(0, CCN-10))
  20% change churn     (commits touching the file since 2019-01-01)
  15% coverage gap     (missed statements, pytest-cov)
  15% rule violations  (flake8 + pylint, docstring conventions excluded)
  10% duplication      (jscpd duplicated lines, min 30 tokens)
  10% coupling         (efferent + afferent module dependencies, grimp)
"""
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW, FIG = ROOT / "raw", ROOT / "figures"

# ------------------------------------------------------------------ lizard
funcs = pd.read_csv(RAW / "lizard_functions.csv", header=None,
                    names=["nloc", "ccn", "tokens", "params", "length", "location", "file",
                           "function", "long_name", "start", "end"])
funcs = funcs[~funcs.file.str.contains("/tests/")]
per = funcs.groupby("file").agg(nloc=("nloc", "sum"), functions=("ccn", "size"),
                                avg_ccn=("ccn", "mean"), max_ccn=("ccn", "max"))
per["ccn_gt10"] = funcs[funcs.ccn > 10].groupby("file").size()
per["complexity_debt"] = funcs.assign(ex=(funcs.ccn - 10).clip(lower=0)).groupby("file").ex.sum()

# module files that have no functions (constants etc.) still matter
cov = json.load(open(RAW / "coverage.json"))["files"]
all_files = sorted(set(per.index) | {f for f in cov if f.startswith("httpie/")})
df = pd.DataFrame(index=all_files).join(per)

# ------------------------------------------------------------------ radon MI
mi = json.load(open(RAW / "radon_mi.json"))
df["mi"] = pd.Series({k: v["mi"] for k, v in mi.items()})

# ------------------------------------------------------------------ flake8
f8 = Counter()
for line in open(RAW / "flake8_complexity.txt"):
    m = re.match(r"^(httpie/[^:]+):\d+:\d+: ", line)
    if m:
        f8[m.group(1)] += 1
df["flake8"] = pd.Series(f8)

# ------------------------------------------------------------------ pylint
pl = json.load(open(RAW / "pylint_full.json"))["messages"]
DOCSTRING = {"C0114", "C0115", "C0116"}
plc = Counter(m["path"] for m in pl if m["messageId"] not in DOCSTRING)
df["pylint"] = pd.Series(plc)
df["violations"] = df[["flake8", "pylint"]].fillna(0).sum(axis=1)

# ------------------------------------------------------------------ jscpd duplication
dup = defaultdict(int)
for d in json.load(open(RAW / "jscpd_30" / "jscpd-report.json"))["duplicates"]:
    for side in ("firstFile", "secondFile"):
        f = d[side]
        dup[f["name"]] += f["end"] - f["start"] + 1
df["dup_lines"] = pd.Series(dup)

# ------------------------------------------------------------------ churn
churn = {}
for row in csv.reader(open(RAW / "git_churn_since2019.csv")):
    churn[row[2]] = int(row[0])
df["churn_commits"] = pd.Series(churn)

# ------------------------------------------------------------------ coverage
df["coverage_pct"] = pd.Series({k: v["summary"]["percent_covered"] for k, v in cov.items()})
df["missed_stmts"] = pd.Series({k: v["summary"]["missing_lines"] for k, v in cov.items()})

# ------------------------------------------------------------------ coupling
coup = pd.read_csv(RAW / "coupling_modules.csv")


def mod2file(m):
    p = m.replace(".", "/")
    return p + ".py" if (ROOT.parent / (p + ".py")).exists() else p + "/__init__.py"


coup["file"] = coup.module.map(mod2file)
coup = coup.set_index("file")
df["ca"] = coup.afferent_Ca
df["ce"] = coup.efferent_Ce
df["coupling"] = df.ca.fillna(0) + df.ce.fillna(0)
cyc_text = (RAW / "import_cycles.txt").read_text()
in_cycle = {mod2file(m.strip()) for m in re.findall(r"^\s+(httpie\.[\w.]+)$", cyc_text, re.M)}
df["in_cycle"] = df.index.isin(in_cycle)

# ------------------------------------------------------------------ optional SonarQube
sonar_path = RAW / "sonar_files.json"
if sonar_path.exists():
    s = json.load(open(sonar_path))
    df["sonar_debt_min"] = pd.Series({k: v.get("sqale_index", 0) for k, v in s.items()})
    df["sonar_smells"] = pd.Series({k: v.get("code_smells", 0) for k, v in s.items()})
    df["sonar_cognitive"] = pd.Series({k: v.get("cognitive_complexity", 0) for k, v in s.items()})

df = df.fillna({c: 0 for c in df.columns if c not in ("mi", "coverage_pct", "avg_ccn")})

# ------------------------------------------------------------------ debt score
WEIGHTS = {"complexity_debt": .30, "churn_commits": .20, "missed_stmts": .15,
           "violations": .15, "dup_lines": .10, "coupling": .10}


def norm(s):
    s = s.astype(float)
    return (s - s.min()) / (s.max() - s.min()) if s.max() > s.min() else s * 0


df["debt_score"] = sum(norm(df[k]) * w for k, w in WEIGHTS.items()) * 100
df = df.sort_values("debt_score", ascending=False)
df.index.name = "file"
df.round(2).to_csv(RAW / "debt_summary_by_file.csv")

# ------------------------------------------------------------------ markdown table
top = df.head(15)
cols = ["nloc", "functions", "avg_ccn", "max_ccn", "ccn_gt10", "mi", "violations", "dup_lines",
        "churn_commits", "coverage_pct", "ce", "ca", "debt_score"]
hdr = ["File", "NLOC (in funcs)", "Funcs", "Avg CCN", "Max CCN", "Funcs CCN>10", "MI (radon)",
       "Rule violations", "Dup lines", "Churn (commits)", "Coverage %", "Ce", "Ca", "Debt score"]
if "sonar_debt_min" in df:
    cols.insert(-1, "sonar_debt_min")
    hdr.insert(-1, "Sonar debt (min)")
lines = ["| Rank | " + " | ".join(hdr) + " |", "|" + "---|" * (len(hdr) + 1)]
for r, (f, row) in enumerate(top.iterrows(), 1):
    vals = []
    for c in cols:
        v = row[c]
        vals.append("–" if pd.isna(v) else f"{v:.1f}" if c in ("avg_ccn", "mi", "coverage_pct", "debt_score") else f"{int(v)}")
    cyc = " ⟳" if row.in_cycle else ""
    lines.append(f"| {r} | `{f}`{cyc} | " + " | ".join(vals) + " |")
tot = df
lines += ["", f"**Codebase totals (httpie/ package, {len(df)} modules):** "
          f"function NLOC {int(tot.nloc.sum())} (Lizard total NLOC 6988), functions {int(tot.functions.sum())}, "
          f"avg CCN {funcs.ccn.mean():.2f}, functions with CCN>10: {int((funcs.ccn > 10).sum())}, "
          f"CCN>15: {int((funcs.ccn > 15).sum())}, rule violations {int(tot.violations.sum())}, "
          f"duplicated lines {int(tot.dup_lines.sum())}, modules in import cycles {int(tot.in_cycle.sum())}.",
          "", "⟳ = module participates in an import cycle (grimp SCC / pylint R0401)."]
(ROOT / "debt_summary_table.md").write_text("\n".join(lines) + "\n")

# ------------------------------------------------------------------ heatmap
H = df.head(20)
hm_cols = [("max_ccn", "Max CCN"), ("avg_ccn", "Avg CCN"), ("complexity_debt", "CCN excess\n(>10)"),
           ("violations", "Rule\nviolations"), ("dup_lines", "Dup\nlines"),
           ("churn_commits", "Churn\n(commits)"), ("missed_stmts", "Missed\nstmts"),
           ("coupling", "Coupling\nCa+Ce"), ("mi", "MI\n(low=bad)"), ("debt_score", "DEBT\nSCORE")]
if "sonar_debt_min" in df:
    hm_cols.insert(-1, ("sonar_debt_min", "Sonar\ndebt min"))
vals = np.array([[H[c].iloc[i] for c, _ in hm_cols] for i in range(len(H))], dtype=float)
normed = np.zeros_like(vals)
for j, (c, _) in enumerate(hm_cols):
    col = df[c].astype(float).fillna(df[c].mean())
    lo, hi = col.min(), col.max()
    x = (vals[:, j] - lo) / (hi - lo) if hi > lo else 0
    normed[:, j] = 1 - x if c == "mi" else x
fig, ax = plt.subplots(figsize=(13, 9.5))
im = ax.imshow(normed, cmap="RdYlGn_r", aspect="auto", vmin=0, vmax=1)
ax.set_xticks(range(len(hm_cols)))
ax.set_xticklabels([l for _, l in hm_cols], fontsize=9)
ax.xaxis.tick_top()
ax.set_yticks(range(len(H)))
ax.set_yticklabels([f + ("  ⟳" if c else "") for f, c in zip(H.index, H.in_cycle)], fontsize=9)
for i in range(len(H)):
    for j, (c, _) in enumerate(hm_cols):
        v = vals[i, j]
        txt = "–" if np.isnan(v) else f"{v:.1f}" if c in ("avg_ccn", "mi", "debt_score") else f"{int(v)}"
        ax.text(j, i, txt, ha="center", va="center", fontsize=8,
                color="white" if normed[i, j] > .75 else "black",
                fontweight="bold" if c == "debt_score" else None)
ax.axvline(len(hm_cols) - 1.5, color="black", lw=1.5)
ax.set_title("HTTPie Technical-Debt Heatmap — top 20 files by composite debt score\n"
             "(Lizard · Radon · Flake8 · Pylint · jscpd · git churn · pytest-cov · grimp)   ⟳ = in import cycle",
             fontsize=11, pad=50)
cb = fig.colorbar(im, ax=ax, fraction=0.025)
cb.set_label("normalised across all 78 modules (red = worse)")
fig.tight_layout()
fig.savefig(FIG / "debt_heatmap.png", dpi=160)
plt.close(fig)

# ------------------------------------------------------------------ CCN histogram
fig, ax = plt.subplots(figsize=(9, 4.8))
bins = list(range(1, 29))
ax.hist(funcs.ccn, bins=bins, color="#4c72b0", edgecolor="white", align="left")
for t, lab, col in [(10, "flake8 --max-complexity=10", "#dd8452"), (15, "Lizard default warning (15)", "#c44e52")]:
    ax.axvline(t - .5, color=col, ls="--", lw=1.5, label=lab)
ax.set_yscale("log")
ax.set_xlabel("Cyclomatic complexity (Lizard CCN) per function")
ax.set_ylabel("# functions (log scale)")
ax.set_title(f"CCN distribution — {len(funcs)} functions, mean {funcs.ccn.mean():.2f}, "
             f"{(funcs.ccn > 10).sum()} above 10, {(funcs.ccn > 15).sum()} above 15")
ax.legend()
fig.tight_layout()
fig.savefig(FIG / "ccn_histogram.png", dpi=160)
plt.close(fig)

# ------------------------------------------------------------------ top functions
tf = funcs.sort_values("ccn", ascending=False).head(15).iloc[::-1]
fig, ax = plt.subplots(figsize=(10, 6))
colors = ["#c44e52" if c > 20 else "#dd8452" if c > 10 else "#4c72b0" for c in tf.ccn]
ax.barh([f"{f}()  {p}:{s}" for f, p, s in zip(tf.function, tf.file, tf.start)], tf.ccn, color=colors)
for y, (c, n) in enumerate(zip(tf.ccn, tf.nloc)):
    ax.text(c + .3, y, f"CCN {c} · {n} NLOC", va="center", fontsize=8)
ax.axvline(10, color="#dd8452", ls="--", lw=1)
ax.axvline(20, color="#c44e52", ls="--", lw=1)
ax.set_xlabel("Lizard cyclomatic complexity (CCN)")
ax.set_title("15 most complex functions (orange > 10 moderate risk, red > 20 high risk)")
ax.tick_params(axis="y", labelsize=8)
ax.set_xlim(0, tf.ccn.max() + 8)
fig.tight_layout()
fig.savefig(FIG / "top_functions_ccn.png", dpi=160)
plt.close(fig)

# ------------------------------------------------------------------ churn vs complexity
fig, ax = plt.subplots(figsize=(9, 6.5))
d = df[df.nloc > 0]
sc = ax.scatter(d.churn_commits, d.complexity_debt + d.avg_ccn, s=d.nloc / 2 + 10,
                c=d.debt_score, cmap="RdYlGn_r", alpha=.8, edgecolor="k", lw=.4)
for f, row in d.head(10).iterrows():
    ax.annotate(f.replace("httpie/", ""), (row.churn_commits, row.complexity_debt + row.avg_ccn),
                fontsize=8, xytext=(4, 4), textcoords="offset points")
ax.axvline(d.churn_commits.median(), color="grey", ls=":", lw=1)
ax.axhline((d.complexity_debt + d.avg_ccn).median(), color="grey", ls=":", lw=1)
ax.set_xlabel("Change churn: commits touching file since 2019-01-01")
ax.set_ylabel("Complexity debt: Σ max(0, CCN−10) + avg CCN")
ax.set_title("Hotspot quadrant — high churn × high complexity (top-right) = priority debt\n"
             "bubble size = NLOC, colour = composite debt score")
fig.colorbar(sc, ax=ax, label="debt score")
fig.tight_layout()
fig.savefig(FIG / "churn_vs_complexity.png", dpi=160)
plt.close(fig)

print(df.head(10)[["nloc", "max_ccn", "complexity_debt", "violations", "dup_lines", "churn_commits",
                   "coverage_pct", "coupling", "debt_score"]].round(1).to_string())
