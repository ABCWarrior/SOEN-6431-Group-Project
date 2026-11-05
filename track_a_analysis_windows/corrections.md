# Corrections to the Track A report

Found while checking the report against the source files and the generated tables, and re-checked a second time (git and the files themselves, 2026-11-05). Each one is a one-line fix in `../track_a_analysis/TRACK_A_REPORT.md`.

| Where | Report says | Source says | Status |
|---|---|---|---|
| 1.4, the `_process_auth()` snippet | "One branch at lines 330-334" | the quoted `if/else` starts at line 326 (`if self.args.auth is None or not plugin.auth_parse:`) and ends at line 331 (`credentials = self.args.auth`) of `httpie/cli/argparser.py`. Line 330 is a comment that the snippet leaves out. The numbers are the same at the commit named in the report (5b604c3) and at HEAD (5f1bfe9). | confirmed |
| 1.2 table, row 9 (`rich_help.py`) | score 21.8 | `debt_summary_table.md` has 21.7. `raw/debt_summary_by_file.csv` rounds to two decimals (21.75); the table is printed with one decimal from the unrounded value, so it is below 21.75 and rounds to 21.7. The 21.8 looks like the two-decimal 21.75 rounded a second time. | confirmed (reasoning from `hotspots.py` lines 133 and 149; the unrounded value was not printed) |
| whole report | no references | the hotspot idea behind the weights is cited in `weights_justification.md` (Tornhill, 2015); nothing else is cited | optional |

Not a correction, but worth knowing:

- The report's screen captures are browser views of the logs, not native terminal windows (the capture manifest says so). Real terminal captures of Lizard, Flake8, Pylint and Vulture are in `screenshots/`.
- On the Windows machine, `git status` shows a clean working tree except for the new `track_a_analysis_windows/` folder, so the re-run did not change any source file.
