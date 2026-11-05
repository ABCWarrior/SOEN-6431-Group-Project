# Track A: Windows re-run

This folder holds an independent re-run of the Track A checks on Windows. The original run
(`../track_a_analysis/`) was done on macOS with Python 3.11.6. The purpose here is to see whether
the numbers reproduce on another platform, and to keep the raw evidence for the false-positive
audit and the weight justification.

Nothing in the repository's source code is changed. The script only reads it.

## Contents

| Path | What it is |
|---|---|
| `run_my_checks.ps1` | PowerShell script: installs Lizard, Radon, Flake8, Pylint and Vulture into one virtual environment, runs the checks, saves the logs. No Docker, npm or WSL. |
| `raw/` | Full output of every tool. Each file starts with the exact command, time, platform and commit. |
| `screenshots/` | Real terminal captures (see below). |
| `score_sensitivity.py` | Re-ranks the hotspot table under other weights (standard library only). |
| `weights_justification.md` | Why the weights are what they are, and how much the ranking depends on them. |
| `corrections.md` | Small errors found in the Track A report while checking it against the source, one line each. |

Run it from this folder:

```
powershell -ExecutionPolicy Bypass -File .\run_my_checks.ps1
python score_sensitivity.py
```

## Result: do the numbers reproduce?

Windows, Python 3.14.6, repo commit 5f1bfe9.

| Metric | Original (macOS) | Windows | Match |
|---|---|---|---|
| Lizard: functions with CCN above 15 | 4 | 4 (raw_main 26, program 25, _process_auth 24, collect_messages 21) | yes |
| Lizard: functions | 461 | 461 (6,988 NLOC, average CCN 2.9) | yes |
| Radon: blocks graded C or worse | 14 | 14 | yes |
| Radon: least maintainable file | argparser.py, about 24.7 | argparser.py, 24.67 | yes |
| Flake8 C901 (threshold 10) | 9 | 9 | yes |
| Flake8 with plugins: complexity findings (CCR001 + C901) | 22 | 22 | yes |
| Flake8 with plugins: all findings | 39 | 39 | yes |
| Tests (pytest, 1,028 collected) | 1,019 passed, 5 skipped, 4 xfailed | 989 passed, 16 failed, 19 skipped, 4 xfailed | **no** |
| Line coverage of `httpie` | 90.7% (389 of 4,187 statements missed) | 89.5% (438 missed) | close |
| Vulture candidates (confidence 60) | about 35 | 35 | yes |
| Pylint import-cycle paths | 5 | 5 | yes |
| Commits touching core.py since 2019 | 37 | 37 | yes |
| jscpd 4.0.5: clones at 50 tokens / at 30 tokens (4 lines) | 1 / 9 | 1 / 9 (same locations; 0.6% duplicated lines at 30 tokens) | yes |
| grimp import graph (`dsm.py`): modules / edges / strongly connected components | 78 / 208 / 3 | 78 / 208 / 3 | yes |
| SonarQube 25.10 Community: technical debt / debt ratio | 494 min / 0.2% | 494 min / 0.2% | yes |
| SonarQube: code smells / bugs / vulnerabilities / security hotspots | 61 / 3 / 1 / 2 | 61 / 3 / 1 / 2 | yes |

The metrics do not depend on the platform.

## Things worth knowing

- Tools count complexity differently. `_process_auth` is 14 in Flake8 (McCabe) and 24 in Lizard; `raw_main` is 31 and 26. Values from different tools should be compared with each tool's own threshold, not with each other.
- Flake8 with default rules reports only the 9 complexity warnings. With the same plugins as the original run (bugbear, cognitive-complexity) and the same command, Windows gives 13 CCR001 + 9 C901 = 22 complexity findings and 39 findings in total, the same as the original report (`raw/3_flake8_plugins.txt`).
- Duplication depends on the tool. Pylint's duplicate-code check found nothing (`raw/7c_pylint_duplicate_code.txt`), while jscpd (original run and this one, `raw/12_jscpd_30.txt`) found repeated handlers in `core.py` (lines 86-97 and 104-115). SonarQube also reports 0.0% duplication. As far as we know, Pylint compares code between files, and those handlers are in one file.
- Not everything is platform-independent: 16 tests fail on Windows (`raw/4b_pytest_coverage.txt`). 13 are in `tests/test_plugins_cli.py` (UnicodeDecodeError), 2 in `tests/test_encoding.py` (big5 charset detection) and 1 in `tests/test_cli_ui.py` (naked invocation). They are tests that depend on text encoding or on running external commands; the causes were not investigated. The total is the same 1,028 tests, and the Windows run skips 19 instead of 5. Coverage is a little lower; the failing and extra skipped tests are a likely reason, but this was not checked.
- By commit count `core.py` is fourth (`raw/7b_git_churn_by_file.txt`: definition.py 55, client.py 54, argparser.py 39, core.py 37). It is first in the hotspot ranking mainly because of its complexity.
- SonarQube was run on Windows with Docker Desktop (WSL2): server `sonarqube:25.10.0.114319-community`, scanner `sonar-scanner-cli:11.4`, same settings as the original script (`raw/10_sonarqube_scanner.txt`, `raw/11_sonarqube_measures.json`). The numbers above match. Difference in setup: the original scan imported the coverage XML (SonarQube coverage 90.7%); this one did not, so SonarQube shows 0.0% coverage. Debt and issue counts do not depend on coverage. Duplication is 0.0% in SonarQube.
- jscpd 4.0.5 was run with npx (Node.js, no Docker) using the original commands (`raw/12_jscpd_50.txt`, `raw/12_jscpd_30.txt`, JSON in `raw/jscpd_50/` and `raw/jscpd_30/`). The clone list is the same as the original run.

## Screenshots

- `screenshots/01_flake8_and_lizard_windows.png`: `flake8 httpie --max-complexity=10` and `lizard httpie -w` typed in cmd.exe.
- `screenshots/02_summary_table_windows.png`: output of `run_my_checks.ps1` with the expected-versus-got table.
- `screenshots/03_pylint_E0704_core_py_67.png`: Pylint's own message for the E0704 finding at `core.py:67:12`, used in the false-positive audit.
- `screenshots/04_vulture_width_ground_truth.png`: signature of the standard-library method that `_split_lines` overrides, used in the Vulture false-positive audit.
- `screenshots/05_vulture_log_windows.png`: the full Vulture log, in an editor.
- `screenshots/06_sonarqube_dashboard_windows.png`: SonarQube overview for `httpie-cli` from the local Docker server (Quality Gate passed; 1 security issue, 3 reliability issues, 61 maintainability issues, 2 security hotspots).
