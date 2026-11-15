Closes #1, closes #2, closes #3, closes #4, closes #6

### Summary
Removes four code clones found in the Case Study #3 Track B audit (agentic AI, Claude Code). Behaviour is unchanged except for one help-text fix (C04). The PR also fixes the 2 big5 tests that failed before any change (#6).

| Clone | Type | Pattern | Files |
|---|---|---|---|
| C01 | Type 1 | Extract Method | `httpie/core.py` |
| C02 | Type 3 | Extract / Pull Up Method (Template Method style) | `httpie/cli/argparser.py` |
| C03 | Type 3 | Extract Function | `httpie/cli/argparser.py` |
| C04 | Type 2 | Extract Function (+ fixes help-text defect) | `httpie/manager/cli.py`, `extras/man/httpie.1` |
| #6 | test data | Replace the big5 sample | `tests/test_encoding.py` |

### Verification
- `pytest`: **1033 passed, 0 failed**, 5 skipped, 4 xfailed. Baseline before the change: 1017 passed, 2 failed (`tests/test_encoding.py::test_terminal_output_{request,response}_charset_detection[big5-…]`). After C01–C04 alone: 1031 passed, the same 2 failures.
- #6: charset-normalizer 3.4.2 and later rejects big5 for the old sample (卷首 repeated) and picks `johab`. The new sample, Article 1 of the UDHR in Traditional Chinese, is detected as big5 on every version checked (2.0.12, 3.0.1, 3.3.2, 3.4.0 to 3.4.4, 3.5.0 to 3.5.2).
- 14 new regression tests in `tests/test_clone_refactorings.py`. The C01 tests also pass against the **original** `core.py`, so behaviour is unchanged.
- Token clone scan (exact, 50 tokens): 1 → 0 duplications. (exact, 25 tokens): 13 → 9.
- Cognitive complexity (flake8-cognitive-complexity): `raw_main` 49 → 40, `HTTPieArgumentParser.parse_args` 11 → 8.
- `flake8`: no new warnings.

### Evidence
`case3_trackB/`: prompt log, scan results before and after, refactoring diff, figures.

### AI disclosure
Clone discovery, refactoring patches and tests were generated with Claude Code (Claude Opus 5.5) and re-verified in a second session (Claude Fable 5.2). A team member reviewed each change against the source before posting.
