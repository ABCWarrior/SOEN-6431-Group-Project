# Track A (Subgroup A) – Tasks 1 & 2: clone inventory and classification for HTTPie

| Where | What |
|---|---|
| [command_log.md](command_log.md) | Every command run, with flags and results (for the report's Section 2, Track A Artifacts) |
| [task1/README.md](task1/README.md) | **Task 1** findings: CPD threshold sweep, cross-checks, top clone pairs, hotspots |
| [task1/tables.md](task1/tables.md) | Task 1 tables generated from the CSVs (raw inventory, consolidated list, hotspots) |
| [task2/README.md](task2/README.md) | **Task 2** findings: Type 1–4 classification, Type 4 audit, false-positive audit, detector capability, GenAI comparison template |
| [task2/tables.md](task2/tables.md) | Task 2 tables generated from the CSVs (classification, pair metrics, AST pair verdicts) |
| `task1/cpd/`, `task1/symilar/`, `task1/ast_scan/` | Raw tool outputs (text / XML / CSV / Markdown) |
| `scripts/` | `clone_inventory.py`, `ast_clone_scan.py`, `classify_clones.py`, `render_tables.py` (standard library only) |
| `screenshots/` | Terminal screenshots to capture (list at the end of the command log) |

Headline: 17 confirmed clones in `httpie/` (1 × Type 1, 4 × Type 2, 9 × Type 3, 3 × Type 4) and 5 CPD false positives. CPD at the default 50 tokens finds 1 of the 17; the three Track A detectors together find 14; the three Type 4 clones were found only by manual semantic audit. `httpie/` itself was not modified.
