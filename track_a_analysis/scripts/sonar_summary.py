"""Print the SonarQube technical-debt summary saved by run_track_a.sh (raw/sonar_*.json)."""
import json
from collections import Counter
from pathlib import Path

from rich.console import Console
from rich.table import Table

RAW = Path(__file__).resolve().parents[1] / "raw"
m = {x["metric"]: x.get("value") for x in
     json.load(open(RAW / "sonar_project_measures.json"))["component"]["measures"]}
files = json.load(open(RAW / "sonar_files.json"))
issues = json.load(open(RAW / "sonar_issues.json"))
c = Console(width=128)
RATING = {"1.0": "A", "2.0": "B", "3.0": "C", "4.0": "D", "5.0": "E"}

t = Table(title="SonarQube 25.10 Community — project httpie-cli (Python 3.11 profile 'Sonar way')")
t.add_column("Metric")
t.add_column("Value", justify="right")
debt = int(m["sqale_index"])
for label, val in [
    ("Lines of code (ncloc)", m["ncloc"]),
    ("Technical debt (SQALE index)", f"{debt} min  (~{debt / 60:.1f} h, {debt / 480:.1f} dev-days)"),
    ("Technical debt ratio", f"{m['sqale_debt_ratio']} %"),
    ("Maintainability rating", RATING[m["sqale_rating"]]),
    ("Code smells / Bugs / Vulnerabilities", f"{m['code_smells']} / {m['bugs']} / {m['vulnerabilities']}"),
    ("Reliability / Security rating", f"{RATING[m['reliability_rating']]} / {RATING[m['security_rating']]}"),
    ("Security hotspots", m["security_hotspots"]),
    ("Cyclomatic / Cognitive complexity (sum)", f"{m['complexity']} / {m['cognitive_complexity']}"),
    ("Duplicated lines density", f"{m['duplicated_lines_density']} %"),
    ("Line coverage (pytest-cov import)", f"{m['coverage']} %"),
]:
    t.add_row(label, str(val))
c.print(t)

t2 = Table(title="Top files by remediation effort (sqale_index)")
for col in ("File", "Debt (min)", "Smells", "Cognitive", "Cyclomatic", "Coverage %"):
    t2.add_column(col, justify="left" if col == "File" else "right")
for f, v in sorted(files.items(), key=lambda kv: -kv[1].get("sqale_index", 0))[:7]:
    t2.add_row(f, *(f"{v.get(k, 0):.0f}" for k in ("sqale_index", "code_smells", "cognitive_complexity",
                                                    "complexity")), f"{v.get('coverage', 0):.1f}")
c.print(t2)

t3 = Table(title="Top rules violated")
t3.add_column("#", justify="right")
t3.add_column("Rule")
t3.add_column("Example message")
for r, n in Counter(i["rule"] for i in issues).most_common(6):
    t3.add_row(str(n), r, next(i["message"] for i in issues if i["rule"] == r)[:70])
c.print(t3)
