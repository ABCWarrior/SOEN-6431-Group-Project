#!/usr/bin/env bash
# SOEN 6431 - Case Study 2 - Track A (traditional static analysis) for HTTPie.
# Re-runs every tool and regenerates raw/, figures/ and debt_summary_table.md.
# Usage (from repo root):   bash track_a_analysis/run_track_a.sh
# With SonarQube:           SONAR_TOKEN=<token> bash track_a_analysis/run_track_a.sh
# Tool console output goes to track_a_analysis/raw/logs/; this script prints one status block per section.
set -uo pipefail
cd "$(dirname "$0")/.."
OUT=track_a_analysis/raw
FIG=track_a_analysis/figures
LOG=$OUT/logs
mkdir -p "$OUT" "$FIG" "$LOG"
VENV=${VENV:-venv}   # same venv the Makefile uses (git-ignored)

# ---------------------------------------------------------------- output helpers
if [ -t 1 ]; then G=$'\e[32m'; R=$'\e[31m'; Y=$'\e[33m'; B=$'\e[1m'; N=$'\e[0m'; else G= R= Y= B= N=; fi
RESULTS=()          # one line per section for the final recap
SEC_FAIL=0          # failures inside the current section
TOTAL_FAIL=0
RUN_T0=$(date +%s)

section() {  # section "<number>" "<title>"
  SEC_NUM=$1; SEC_TITLE=$2; SEC_FAIL=0; SEC_T0=$(date +%s)
  echo
  echo "${B}[$SEC_NUM] $SEC_TITLE${N}"
}
mtime() { python -c 'import os,sys; print(int(os.path.getmtime(sys.argv[1])))' "$1"; }
check() {  # check <file> "<label>"  -> file must exist, be non-empty and be written during this section
  if [ -s "$1" ] && [ "$(mtime "$1")" -ge "$SEC_T0" ]; then
    printf "    ${G}✔${N} %-30s %s\n" "$2" "$1"
  elif [ -s "$1" ]; then
    printf "    ${R}✘${N} %-30s %s ${R}(old file, not regenerated)${N}\n" "$2" "$1"; SEC_FAIL=$((SEC_FAIL + 1))
  else
    printf "    ${R}✘${N} %-30s %s ${R}(missing or empty)${N}\n" "$2" "$1"; SEC_FAIL=$((SEC_FAIL + 1))
  fi
}
info() { echo "    → $*"; }
fail() { echo "    ${R}✘ $*${N}"; SEC_FAIL=$((SEC_FAIL + 1)); }
done_section() {  # done_section ["skipped reason"]
  local secs=$(( $(date +%s) - SEC_T0 ))
  if [ -n "${1:-}" ]; then
    echo "  ${Y}⚠ SKIPPED${N} - $1"
    RESULTS+=("${Y}⚠ SKIPPED${N}  [$SEC_NUM] $SEC_TITLE")
  elif [ $SEC_FAIL -eq 0 ]; then
    echo "  ${G}✔ SUCCESS${N} - $SEC_TITLE (${secs}s)"
    RESULTS+=("${G}✔ OK     ${N}  [$SEC_NUM] $SEC_TITLE")
  else
    echo "  ${R}✘ FAILED${N} - $SEC_FAIL problem(s) in $SEC_TITLE, see $LOG/"
    RESULTS+=("${R}✘ FAILED ${N}  [$SEC_NUM] $SEC_TITLE")
    TOTAL_FAIL=$((TOTAL_FAIL + 1))
  fi
}
pyget() { python -c "import json,sys; d=json.load(open(sys.argv[1])); print($2)" "$1" 2>/dev/null || echo "?"; }

echo "${B}=== SOEN 6431 Track A - static analysis of HTTPie ===${N}"
echo "Tool logs: $LOG/"

# ---------------------------------------------------------------- 0. environment
section 0 "Python environment"
if [ ! -x "$VENV/bin/lizard" ]; then
  info "installing tools into $VENV (first run only)..."
  [ -x "$VENV/bin/python" ] || python3.11 -m venv "$VENV"
  "$VENV/bin/pip" install -q -e '.[dev]' \
     lizard==1.25.0 radon==6.0.1 flake8==7.5.0 flake8-bugbear flake8-cognitive-complexity \
     pylint==4.1.3 vulture==2.16 pydeps==3.0.9 grimp import-linter matplotlib numpy pandas rich \
     > $LOG/pip_install.txt 2>&1
fi
export PATH="$PWD/$VENV/bin:$PATH"
for t in python lizard radon flake8 pylint vulture pydeps npx git; do
  command -v $t >/dev/null || fail "tool not found: $t"
done
info "$(python --version), venv: $VENV"
done_section

# ---------------------------------------------------------------- 1. complexity & debt counters
section 1 "Complexity metrics (Lizard, Radon, TODO/FIXME)"
lizard httpie -x "*/tests/*" -C 10 -L 60 -a 5 --csv      > $OUT/lizard_functions.csv
lizard httpie -x "*/tests/*" -C 10 -L 60 -a 5 -w         > $OUT/lizard_warnings.txt
lizard httpie -x "*/tests/*"                              > $OUT/lizard_full.txt
lizard httpie -x "*/tests/*" -Eduplicate                  > $OUT/lizard_duplicate.txt 2>&1
radon cc  httpie -s -a -nc > $OUT/radon_cc_C_plus.txt
radon cc  httpie -j        > $OUT/radon_cc.json
radon mi  httpie -s -j     > $OUT/radon_mi.json
radon raw httpie -s -j     > $OUT/radon_raw.json
radon hal httpie -j        > $OUT/radon_hal.json
grep -rn -E "TODO|FIXME|XXX|HACK" --include='*.py' httpie > $OUT/todo_fixme.txt
check $OUT/lizard_functions.csv "Lizard per-function metrics"
check $OUT/lizard_warnings.txt  "Lizard threshold warnings"
check $OUT/radon_cc.json        "Radon cyclomatic complexity"
check $OUT/radon_mi.json        "Radon maintainability index"
check $OUT/todo_fixme.txt       "TODO/FIXME markers"
info "$(($(wc -l < $OUT/lizard_functions.csv))) functions analysed, $(grep -c 'warning' $OUT/lizard_warnings.txt) over thresholds, $(wc -l < $OUT/todo_fixme.txt | tr -d ' ') TODO/FIXME markers"
done_section

# ---------------------------------------------------------------- 2. static linters & smells
section 2 "Linters & code smells (Flake8, Pylint, Vulture)"
flake8 httpie --max-complexity=10 --max-cognitive-complexity=15 \
       --select=C90,CCR,B,E,W,F --ignore=E501,W503 --statistics --count > $OUT/flake8_complexity.txt 2>&1
flake8 httpie --max-complexity=10 --select=C90 > $OUT/flake8_mccabe_only.txt
pylint httpie --output-format=json2 > $OUT/pylint_full.json 2>$LOG/pylint_full_stderr.txt
pylint httpie --disable=all --enable=design,similarities,cyclic-import,too-many-lines,too-many-nested-blocks,too-many-return-statements,too-many-branches,too-many-statements,too-many-arguments,too-many-locals,too-many-instance-attributes,too-many-public-methods,too-few-public-methods,too-many-boolean-expressions,fixme,unused-import,unused-variable,unused-argument,broad-exception-caught,protected-access \
       --min-similarity-lines=6 --reports=n > $OUT/pylint_design.txt 2>&1
pylint httpie --disable=all --enable=duplicate-code --min-similarity-lines=4 \
       --ignore-imports=y --ignore-docstrings=y > $OUT/pylint_duplicate_code.txt 2>&1
vulture httpie --min-confidence 60 > $OUT/vulture_dead_code.txt
check $OUT/flake8_complexity.txt "Flake8 complexity + smells"
check $OUT/pylint_full.json      "Pylint full report"
check $OUT/pylint_design.txt     "Pylint design checks"
check $OUT/vulture_dead_code.txt "Vulture dead code"
info "Flake8: $(tail -1 $OUT/flake8_complexity.txt) violations, Pylint: $(pyget $OUT/pylint_full.json 'len(d["messages"])') messages, Vulture: $(wc -l < $OUT/vulture_dead_code.txt | tr -d ' ') dead-code hits"
done_section

# ---------------------------------------------------------------- 3. duplication
section 3 "Code duplication (jscpd)"
npx -y jscpd@4.0.5 httpie --format python --min-tokens 50 --reporters console,json --output $OUT/jscpd_50 \
  --silent > $LOG/jscpd_50.txt 2>&1
npx -y jscpd@4.0.5 httpie --format python --min-tokens 30 --min-lines 4 --reporters console,json \
  --output $OUT/jscpd_30 > $LOG/jscpd_30.txt 2>&1
check $OUT/jscpd_50/jscpd-report.json "jscpd report (50 tokens)"
check $OUT/jscpd_30/jscpd-report.json "jscpd report (30 tokens)"
info "50 tokens: $(pyget $OUT/jscpd_50/jscpd-report.json 'len(d["duplicates"])') clones | 30 tokens: $(pyget $OUT/jscpd_30/jscpd-report.json 'str(len(d["duplicates"]))+" clones, "+str(d["statistics"]["total"]["duplicatedLines"])+" duplicated lines ("+str(round(d["statistics"]["total"]["percentage"],2))+" %)"')"
done_section

# ---------------------------------------------------------------- 4. churn & coverage
section 4 "Git churn & test coverage (pytest-cov)"
git log --since=2019-01-01 --no-merges --numstat --format="--%h" -- httpie \
  | awk '/^--/{next} NF==3{f=$3; ch[f]+=$1+$2; c[f]++} END{for(f in c) print c[f]","ch[f]","f}' \
  | sort -t, -k1 -nr > $OUT/git_churn_since2019.csv
info "running the test suite (takes about a minute)..."
python -m pytest tests -q -p no:cacheprovider --override-ini=addopts= --cov=httpie \
  --cov-report=xml:$OUT/coverage.xml --cov-report=json:$OUT/coverage.json --cov-report=term \
  2>&1 | tail -80 > $OUT/pytest_coverage.txt
check $OUT/git_churn_since2019.csv "Git churn per file"
check $OUT/coverage.json           "Coverage (JSON)"
check $OUT/coverage.xml            "Coverage (XML, for Sonar)"
info "$(wc -l < $OUT/git_churn_since2019.csv | tr -d ' ') files with churn since 2019, line coverage $(pyget $OUT/coverage.json 'round(d["totals"]["percent_covered"],1)') %, tests: $(grep -E 'passed|failed' $OUT/pytest_coverage.txt | tail -1 | tr -d '=' | sed 's/^ *//')"
done_section

# ---------------------------------------------------------------- 5. dependency structure / coupling
section 5 "Dependencies, coupling & DSM heatmaps (pydeps, grimp)"
pydeps httpie --noshow --max-bacon=2 --cluster --rankdir LR -T svg -o $FIG/pydeps_graph.svg > $LOG/pydeps.txt 2>&1
pydeps httpie --noshow --show-cycles -T svg -o $FIG/pydeps_cycles.svg >> $LOG/pydeps.txt 2>&1
python track_a_analysis/scripts/dsm.py > $LOG/dsm.txt 2>&1
check $FIG/pydeps_graph.svg          "Dependency graph"
check $FIG/pydeps_cycles.svg         "Import cycles graph"
check $FIG/dsm_heatmap.png           "DSM heatmap (components)"
check $FIG/dsm_modules_heatmap.png   "DSM heatmap (modules)"
check $OUT/coupling_modules.csv      "Coupling (Ca/Ce) per module"
check $OUT/import_cycles.txt         "Import cycles list"
info "$(tail -1 $LOG/dsm.txt)"
done_section

# ---------------------------------------------------------------- 6. SonarQube (Docker)
# start the server once with:
# docker run -d --name trackA-sonarqube -p 9000:9000 -e SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true sonarqube:25.10.0.114319-community
section 6 "SonarQube technical debt (SQALE)"
sonar_step() {
  SONAR_HOST=${SONAR_HOST:-http://localhost:9000}
  curl -sf "$SONAR_HOST/api/system/status" | grep -q '"UP"' \
    || { fail "SonarQube is not running at $SONAR_HOST (start Docker Desktop + container trackA-sonarqube)"; return; }
  info "server is UP at $SONAR_HOST"
  # coverage.py writes paths relative to the package dir -> remap <source> for the scanner container
  sed 's#<source>.*</source>#<source>/usr/src/httpie</source>#' $OUT/coverage.xml > $OUT/coverage_sonar.xml
  rm -rf .scannerwork
  info "scanning (takes about a minute)..."
  docker run --rm -e SONAR_HOST_URL=http://host.docker.internal:9000 -e SONAR_TOKEN="$SONAR_TOKEN" \
    -v "$PWD:/usr/src" sonarsource/sonar-scanner-cli:11.4 \
    -Dsonar.projectKey=httpie-cli -Dsonar.sources=httpie -Dsonar.tests=tests -Dsonar.python.version=3.11 \
    -Dsonar.python.coverage.reportPaths=$OUT/coverage_sonar.xml -Dsonar.exclusions="track_a_analysis/**" \
    > $OUT/sonar_scanner_log.txt 2>&1
  grep -q "EXECUTION SUCCESS" $OUT/sonar_scanner_log.txt \
    || { fail "sonar-scanner failed, see $OUT/sonar_scanner_log.txt"; return; }
  info "scan uploaded, waiting for the server to process it..."
  local task st
  task=$(grep ceTaskId .scannerwork/report-task.txt 2>/dev/null | cut -d= -f2)
  for _ in $(seq 1 60); do
    st=$(curl -s -u "$SONAR_TOKEN:" "$SONAR_HOST/api/ce/task?id=$task" | grep -o '"status":"[A-Z_]*"' | head -1)
    case "$st" in
      *SUCCESS*) info "server finished processing"; break;;
      *FAILED*|*CANCELED*) fail "SonarQube background task $st"; return;;
      "") info "token cannot read task status - waiting 60 s instead"; sleep 60; break;;
    esac
    sleep 5
  done
  SONAR_HOST="$SONAR_HOST" python track_a_analysis/scripts/sonar_export.py > $LOG/sonar_export.txt 2>&1 \
    || { fail "export failed, see $LOG/sonar_export.txt"; return; }
  python track_a_analysis/scripts/sonar_summary.py > $OUT/sonar_summary.txt 2>&1
  check $OUT/sonar_scanner_log.txt        "Scanner log"
  check $OUT/sonar_project_measures.json  "Project measures"
  check $OUT/sonar_files.json             "Per-file measures"
  check $OUT/sonar_issues.json            "Issues"
  check $OUT/sonar_summary.txt            "Readable summary"
  info "$(tail -1 $LOG/sonar_export.txt); $(pyget $OUT/sonar_project_measures.json \
    '"debt "+next(m["value"] for m in d["component"]["measures"] if m["metric"]=="sqale_index")+" min, debt ratio "+next(m["value"] for m in d["component"]["measures"] if m["metric"]=="sqale_debt_ratio")+" %"')"
}
if [ -n "${SONAR_TOKEN:-}" ]; then
  sonar_step
  done_section
else
  done_section "SONAR_TOKEN not set - the heatmap reuses the old raw/sonar_files.json if present"
fi

# ---------------------------------------------------------------- 7. combine -> heatmap + summary table
section 7 "Debt summary table & heatmaps (hotspots.py)"
python track_a_analysis/scripts/hotspots.py > $LOG/hotspots.txt 2>&1 || fail "hotspots.py crashed, see $LOG/hotspots.txt"
check track_a_analysis/debt_summary_table.md "Summary table (markdown)"
check $OUT/debt_summary_by_file.csv          "Summary table (CSV)"
check $FIG/debt_heatmap.png                  "Debt heatmap"
check $FIG/ccn_histogram.png                 "CCN histogram"
check $FIG/top_functions_ccn.png             "Top functions by CCN"
check $FIG/churn_vs_complexity.png           "Churn vs complexity"
if grep -q sonar_debt_min $OUT/debt_summary_by_file.csv 2>/dev/null; then
  info "heatmap includes the SonarQube debt column"
else
  info "${Y}heatmap has NO SonarQube column (no raw/sonar_files.json)${N}"
fi
done_section

# ---------------------------------------------------------------- recap
echo
echo "${B}=== Recap ($(( $(date +%s) - RUN_T0 ))s) ===${N}"
printf '  %s\n' "${RESULTS[@]}"
echo
echo "${B}--- debt_summary_table.md ---${N}"
cat track_a_analysis/debt_summary_table.md
echo
if [ $TOTAL_FAIL -eq 0 ]; then
  echo "${G}${B}✔ ALL SECTIONS COMPLETED SUCCESSFULLY${N}"
  echo "  Heatmap: $FIG/debt_heatmap.png   Table: track_a_analysis/debt_summary_table.md"
else
  echo "${R}${B}✘ $TOTAL_FAIL SECTION(S) FAILED - see the ✘ lines above and the logs in $LOG/${N}"
fi
exit $TOTAL_FAIL
