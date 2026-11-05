"""Export SonarQube measures/issues for project httpie-cli into track_a_analysis/raw/.

Usage: SONAR_TOKEN=<user token> python track_a_analysis/scripts/sonar_export.py
"""
import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "raw"
HOST = os.environ.get("SONAR_HOST", "http://localhost:9000")
AUTH = base64.b64encode((os.environ["SONAR_TOKEN"] + ":").encode()).decode()


def get(path):
    req = urllib.request.Request(HOST + path, headers={"Authorization": "Basic " + AUTH})
    return json.load(urllib.request.urlopen(req))


M = ("ncloc,sqale_index,sqale_debt_ratio,sqale_rating,code_smells,bugs,vulnerabilities,security_hotspots,"
     "complexity,cognitive_complexity,duplicated_lines_density,duplicated_blocks,coverage,reliability_rating,"
     "security_rating")
json.dump(get(f"/api/measures/component?component=httpie-cli&metricKeys={M}"),
          open(RAW / "sonar_project_measures.json", "w"), indent=1)
FM = "sqale_index,code_smells,cognitive_complexity,complexity,duplicated_lines,coverage,ncloc"
try:
    comps = get(f"/api/measures/component_tree?component=httpie-cli&qualifiers=FIL&ps=500&metricKeys={FM}")[
        "components"]
except urllib.error.HTTPError as e:
    if e.code != 403:
        raise
    # project analysis tokens (sqp_...) may not browse the component tree -> query each file directly
    print("component_tree refused (403) - querying files one by one")
    comps = []
    for p in sorted(RAW.parents[1].glob("httpie/**/*.py")):
        rel = p.relative_to(RAW.parents[1]).as_posix()
        try:
            comps.append(get(f"/api/measures/component?component=httpie-cli:{rel}&metricKeys={FM}")["component"])
        except urllib.error.HTTPError:
            pass  # file not indexed by Sonar (e.g. empty __init__.py)
files = {c["path"]: {m["metric"]: float(m.get("value", 0)) for m in c["measures"]}
         for c in comps if c["path"].startswith("httpie/")}
json.dump(files, open(RAW / "sonar_files.json", "w"), indent=1)
issues = get("/api/issues/search?componentKeys=httpie-cli&ps=500&issueStatuses=OPEN,CONFIRMED")["issues"]
json.dump(issues, open(RAW / "sonar_issues.json", "w"), indent=1)
print(f"exported {len(files)} files, {len(issues)} issues")
