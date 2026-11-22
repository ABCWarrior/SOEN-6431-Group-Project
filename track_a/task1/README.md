# Task 1 – Clone Inventory & Hotspot Identification (Track A)

> Brief: *Locate and list the top clone pairs/clusters across the codebase, noting token counts, line lengths, and affected files.*

All numbers below are produced by the commands in [../command_log.md](../command_log.md). Full tables are in [tables.md](tables.md); raw data is in the CSV files in this folder.

## 1. Scope and method

| Item | Value |
|---|---|
| Target | `httpie/` package, commit `5b604c3` (78 `.py` files) |
| Size | 9,817 physical lines; **7,813 code lines**; 1,824 blank; 445 comment-only; 39,547 CPD tokens |
| Primary detector | PMD 7.29.0 CPD, `--language python`, minimum tile size (MTS) swept over 25 / 35 / 50 / 75 / 100 tokens, text + XML + CSV + Markdown reports |
| Cross-check 1 | pylint 4.1.3 `symilar` (line-based, cross-file only), `-d 3` and `-d 4` |
| Cross-check 2 | Function-level AST/token clone metric calculator (`track_a/scripts/ast_clone_scan.py`, standard library only): every function's tokens are normalised (identifiers → `ID`, literals → `LIT`, comments and docstrings dropped), and every pair of functions with ≥ 30 tokens is compared with `difflib` similarity ≥ 0.75 |
| Secondary scope | `tests/` (6,378 code lines), CPD at MTS 50 / 100, for reference only |

Why three detectors: CPD compares exact token runs. For Python, the `--ignore-identifiers` / `--ignore-literals` flags produced byte-identical output (command log #5–6), so CPD cannot see renamed (Type 2) or gapped (Type 3) clones. `symilar` covers cross-file line matches; the AST scanner covers renamed and gapped clones at function level.

## 2. CPD threshold sweep (precision vs recall)

| `--minimum-tokens` | Clone groups | Duplicated lines | Clones still reported |
|---|---|---|---|
| 25 | **12** | 74 | all 12 (7 true clones, 5 false positives; see Task 2) |
| 35 | 2 | 16 | CL01 `core.py` handlers, CL02 `argparser.py` usage inspection |
| 50 (brief default) | 1 | 11 | CL01 only |
| 75 | 0 | 0 | – |
| 100 | 0 | 0 | – |

At the brief's default of 50 tokens, CPD reports a single clone. HTTPie's duplication is fine-grained: no clone is longer than 51 tokens / 11 lines, so a useful inventory needs MTS = 25. That adds false positives, which Task 2 removes. The 12 groups at MTS 25 cover **128 lines = 1.64 %** of the code. One CPD run takes about 1.2 s; scanning `httpie/` and `tests/` together (about 2× the code) still takes 1.28 s, so JVM start-up dominates.

## 3. Raw detector output

* **CPD (MTS 25): 12 groups.** 9 intra-file, 3 cross-file; 10 pairs and 2 three-way clusters (`formatters/{headers,json,xml}.py`, `rich_progress.py` signatures). Largest: 51 tokens / 11 lines (`core.py:86–96` ↔ `104–114`). Full list: Table 1.1.
* **symilar (`-d 3`): 2 cross-file pairs**, 9 duplicate lines (0.09 %). Both are missed by CPD: the legacy session-format `post_process()` pair and the two entry-point Ctrl+C wrappers. At `-d 4` it finds nothing; with `--ignore-signatures` only 4 lines remain.
* **AST scan: 47 function pairs** at similarity ≥ 0.75 (461 functions, 49,770 pairs compared in 1.9 s). After reading each pair (Task 2), 10 pairs (8 distinct clones) are real and 37 are coincidental shapes. Its 5 pairs at similarity 1.0 are all real Type 2 clones that CPD cannot see.

## 4. Top clone pairs / clusters (consolidated, after the Task 2 audit)

17 confirmed clones, ranked by **shared tokens**: tokens the copies really have in common after normalisation, summed over the pairs in a cluster. "CPD tokens" is the CPD match length when CPD found it.

| Rank | ID | Affected files : lines | Lines / occ. | Shared tokens | CPD tokens | Found by | Type |
|---|---|---|---|---|---|---|---|
| 1 | CL13 | `legacy/v3_1_0_session_cookie_format.py:36–64` ↔ `legacy/v3_2_0_session_header_format.py:26–46` (`pre_process`) | 29 / 21 | 91 | – | AST scan | 3 |
| 2 | CL03 | `cli/argparser.py:90–105` ↔ `151–167` (two `parse_args` methods) | 16 / 17 | 91 | 33 + 30 | CPD | 3 |
| 3 | CL06 | `output/formatters/headers.py:6–8`, `json.py:8–10`, `xml.py:55–57` (`__init__`) | 3 / 3 / 3 | 62 | 30 | CPD, AST | 2 |
| 4 | CL02 | `cli/argparser.py:59–69` ↔ `580–591` (`add_usage` / `print_usage`) | 11 / 12 | 57 | 44 | CPD | 3 |
| 5 | CL20 | `uploads.py:65–69`, `models.py:163–169`, `uploads.py:257–262`, `client.py:201–203` (str → bytes) | 5 / 7 / 6 / 3 | 51 | – | manual only | 4 |
| 6 | CL12 | `legacy/v3_1_0…:67–81` ↔ `legacy/v3_2_0…:49–64` (`post_process`) | 15 / 16 | 51 | – | symilar, AST | 3 |
| 7 | CL01 | `core.py:86–96` ↔ `104–114` (Ctrl+C / SystemExit handlers) | 11 / 11 | 51 | 51 | CPD | 1 |
| 8 | CL04 | `output/lexers/metadata.py:38–47` ↔ `49–57` (lexer rules) | 10 / 9 | 43 | 33 | CPD | 3 |
| 9 | CL18 | `output/ui/rich_progress.py:86–94` ↔ `132–141` (`stop`) | 9 / 10 | 41 | – | AST scan | 3 |
| 10 | CL15 | `output/formatters/colors.py:81–86` ↔ `98–103` | 6 / 6 | 38 | – | AST scan | 2 |
| 11–17 | CL17, CL19, CL16, CL22, CL08, CL14, CL21 | see Table 1.2 | | 35 → 21 | | | |

For Type 4 clones (CL20–CL22) the shared-token figure only measures surface overlap; their duplication is in behaviour, not text.

## 5. Hotspots

**Files, raw CPD view (MTS 25, before false-positive removal):** `cli/argparser.py` (4 groups, 51 lines, 10.5 %), `core.py` (2 groups, 26 lines, 10.1 %), `output/ui/rich_progress.py` (2 groups, 11 lines, 9.7 %), `output/lexers/metadata.py` (20.4 %), `output/formatters/headers.py` (35.7 %).

**Files, confirmed clones only (Types 1–4, after Task 2):**

| File | Code LOC | True clones | Cloned lines | Density |
|---|---|---|---|---|
| `cli/argparser.py` | 487 | 4 (CL02, CL03, CL08, CL19) | 79 | 16.2 % |
| `legacy/v3_2_0_session_header_format.py` | 55 | 2 (CL12, CL13) | 37 | 67.3 % |
| `legacy/v3_1_0_session_cookie_format.py` | 82 | 2 (CL12, CL13) | 44 | 53.7 % |
| `uploads.py` | 204 | 2 (CL17, CL20) | 25 | 12.3 % |
| `output/formatters/colors.py` | 325 | 2 (CL15, CL21) | 20 | 6.2 % |
| `output/formatters/json.py` | 27 | 2 (CL06, CL21) | 10 | 37.0 % |
| `core.py` | 257 | 1 (CL01) | 22 | 8.6 % |

The confirmed clones cover **333 lines = 4.26 %** of the code, about 2.6 × CPD's raw 1.64 %. CPD at MTS 25 both over-reports (false positives) and under-reports (misses Type 2–4).

**Packages (raw CPD view):** `httpie/cli` (4 groups, 2.0 %), top-level modules (4, 1.7 %), `httpie/output` (4, 2.1 %). Removing false positives changes the picture in two ways. Both CPD groups in `rich_progress.py` are false-positive signatures; its one real clone (CL18, the two `stop()` methods) is found only by the AST scan. `httpie/legacy`, invisible to CPD, becomes the densest package.

**Hotspot interpretation (architecture):**
1. **CLI argument parsing (`cli/argparser.py`)** is the main hotspot. The parser hierarchy re-implements base logic in the subclass (CL03), and `sys.exc_info()` inspection (CL02) and error handling (CL08) are repeated. This matches the brief's focus for HTTPie ("argument parsing duplication").
2. **Command-line execution blocks (`core.py`, `__main__.py`, `manager/__main__.py`)**: the Ctrl+C / SystemExit handling is copied inside `raw_main()` (CL01) and across the two entry points (CL14).
3. **Versioned session migrations (`legacy/`)**: whole functions copied between version modules (CL12, CL13), the highest density in the code base.
4. **Output formatters (`output/formatters/`)**: the plugin constructors (CL06), the colour-formatter methods (CL15), and JSON detection done twice (CL21).

## 6. Test suite (secondary)

`tests/` (6,378 code lines) has 4 CPD groups at MTS 50 (largest 76 tokens / 10 lines in `test_cli.py`) and none at 100. Test clones are larger than any production clone, which is typical of repeated test fixtures. They are outside the inventory, which targets production code.

## 7. Key Task 1 findings

* HTTPie has **low, fine-grained duplication**: no clone above 51 CPD tokens, 0 groups at MTS ≥ 75.
* The brief's default (MTS 50) finds 1 of the 17 real clones; MTS 25 finds 6 (plus 5 false positives).
* Using the three Track A detectors together finds 14 of 17. The remaining 3 are Type 4 and need semantic review (Task 2).
* Hotspot #1 is `cli/argparser.py`; the densest are the two `legacy/` modules (54–67 %).
