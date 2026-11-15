Closes #1, closes #2, closes #3, closes #4, closes #6

### Summary

Removes four code clones found in the Case Study #3 Track B audit (agentic AI, Claude Code). Behaviour is unchanged except for one help-text fix (C04). The PR also fixes the 2 big5 tests that failed before any change (#6), and fixes the CI workflows and two version-related test failures so the full matrix can pass on the current GitHub runners.

| Clone | Type | Pattern | Files |
|---|---|---|---|
| C01 | Type 1 | Extract Method | `httpie/core.py` |
| C02 | Type 3 | Extract / Pull Up Method (Template Method style) | `httpie/cli/argparser.py` |
| C03 | Type 3 | Extract Function | `httpie/cli/argparser.py` |
| C04 | Type 2 | Extract Function (+ fixes help-text defect) | `httpie/manager/cli.py`, `extras/man/httpie.1` |
| #6 | test data | Replace the big5 sample | `tests/test_encoding.py` |

### Verification

- `pytest`: **1033 passed, 0 failed**, 5 skipped, 4 xfailed. With pyOpenSSL (`HTTPIE_TEST_WITH_PYOPENSSL=1`, pyOpenSSL 26.1.0): 1032 passed, 0 failed, 6 skipped, 4 xfailed. Baseline before the change: 1017 passed, 2 failed (`tests/test_encoding.py::test_terminal_output_{request,response}_charset_detection[big5-…]`). After C01–C04 alone: 1031 passed, the same 2 failures.
- Issue #6: charset-normalizer 3.4.2 and later rejects big5 for the old sample (卷首 repeated) and picks `johab`. The new sample, Article 1 of the UDHR in Traditional Chinese, is detected as big5 on every version checked (2.0.12, 3.0.1, 3.3.2, 3.4.0 to 3.4.4, 3.5.0 to 3.5.2).
- 14 new regression tests in `tests/test_clone_refactorings.py`. The C01 tests also pass against the **original** `core.py`, so behaviour is unchanged.
- Token clone scan (exact, 50 tokens): 1 → 0 duplications. (exact, 25 tokens): 13 → 9.
- Cognitive complexity (flake8-cognitive-complexity): `raw_main` 49 → 40, `HTTPieArgumentParser.parse_args` 11 → 8.
- `flake8`: no new warnings.

### CI workflow fixes

`ubuntu-latest` now resolves to Ubuntu 26.04, which has no builds of the end-of-life Python 3.7, 3.8 and 3.9, so `actions/setup-python` failed before any step ran. The `macos-13` runner has also been retired. Python 3.11 is now the baseline, since 3.10 is close to end of life.

- Code Style (`code-style.yml`): Python 3.9 → `"3.11"`. The same change is made in `benchmark.yml` and `content.yml`, which also pinned 3.9.
- Coverage (`coverage.yml`): Python 3.10 → `"3.11"`.
- Tests (`tests.yml`): Python matrix 3.7–3.12 → 3.11–3.13, and `macos-13` → `macos-latest`.
- All five workflows: `actions/setup-python@v4` → `@v5`.
- Check Markdown Style: blank lines added around headings and lists in `case3_trackB/github_drafts.md` and this file, so `make doc-check` passes.
- Tests with pyOpenSSL (`pyopenssl: 1` jobs): `test_digest_auth[https-…]` failed with `ValueError: Context has already been used to create a Connection, it cannot be mutated again`. HTTPie shares one SSL context across connections, urllib3 sets `verify_mode` on it for every new connection (here, the retry after the digest `401`), and pyOpenSSL 26.2.0 turned that from a deprecation warning into an error. `setup.cfg` now pins `pyopenssl<26.2` in the `dev` extras. pyOpenSSL is only injected by the test suite, so HTTPie at runtime is not affected.
- Python 3.12 (`test_naked_invocation[args3]`): recent 3.12 releases print the invalid-choice list without quotes (`choose from all, colors, format, none`), while 3.11, 3.13.18 and 3.14 quote it. `tests/test_cli_ui.py` now builds the expected message from the running `argparse` instead of hard-coding one format.

### Evidence

`case3_trackB/`: prompt log, scan results before and after, refactoring diff, figures.

### AI disclosure

Clone discovery, refactoring patches and tests were generated with Claude Code (Claude Opus 5.5) and re-verified in a second session (Claude Fable 5.2). A team member reviewed each change against the source before posting.
