Closes #1, closes #2, closes #3, closes #4

### Summary
Removes four code clones found in the Case Study #3 Track B audit (agentic AI, Claude Code). Behaviour is unchanged except for one help-text fix (C04).

| Clone | Type | Pattern | Files |
|---|---|---|---|
| C01 | Type 1 | Extract Method | `httpie/core.py` |
| C02 | Type 3 | Extract / Pull Up Method (Template Method style) | `httpie/cli/argparser.py` |
| C03 | Type 3 | Extract Function | `httpie/cli/argparser.py` |
| C04 | Type 2 | Extract Function (+ fixes help-text defect) | `httpie/manager/cli.py`, `extras/man/httpie.1` |

### Verification
- `pytest`: **1031 passed**, 5 skipped, 4 xfailed, 2 failed. Baseline before the change: 1017 passed, same 2 failures (`tests/test_encoding.py::test_terminal_output_{request,response}_charset_detection[big5-…]`). Those come from the `charset-normalizer` version installed locally, not from this change.
- 14 new regression tests in `tests/test_clone_refactorings.py`. The C01 tests also pass against the **original** `core.py`, so behaviour is unchanged.
- Token clone scan (exact, 50 tokens): 1 → 0 duplications. (exact, 25 tokens): 13 → 9.
- Cognitive complexity (flake8-cognitive-complexity): `raw_main` 49 → 40, `HTTPieArgumentParser.parse_args` 11 → 8.
- `flake8`: no new warnings.

### Evidence
`case3_trackB/`: prompt log, scan results before and after, refactoring diff, figures.

### AI disclosure
Clone discovery, refactoring patches and tests were generated with Claude Code (Claude Opus 5.5) and re-verified in a second session (Claude Fable 5.2). A team member reviewed each change against the source before posting.
