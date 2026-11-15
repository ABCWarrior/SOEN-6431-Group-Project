Closes #1, closes #2, closes #3, closes #4, closes #6

### Summary

This PR removes four code clones that the Case Study #3 Track B audit found with Claude Code. The behaviour does not change, except for one help-text fix in C04.

The PR also fixes three things that kept the tests from passing:

- the 2 big5 tests that already failed before any change (#6),
- the CI workflows, which no longer ran on the current GitHub runners,
- two test failures caused by newer versions of pyOpenSSL and Python 3.12.

| Item | Clone type | Refactoring | Files |
|---|---|---|---|
| C01 | Type 1 | Extract Method | `httpie/core.py` |
| C02 | Type 3 | Extract Method and Pull Up Method (Template Method style) | `httpie/cli/argparser.py` |
| C03 | Type 3 | Extract Function | `httpie/cli/argparser.py` |
| C04 | Type 2 | Extract Function, plus the help-text fix | `httpie/manager/cli.py`, `extras/man/httpie.1` |
| #6 | Test data | Replace the big5 sample | `tests/test_encoding.py` |

### Verification

- `pytest` gives **1033 passed, 0 failed**, 5 skipped, 4 xfailed.
- With pyOpenSSL 26.1.0 (`HTTPIE_TEST_WITH_PYOPENSSL=1`), it gives 1032 passed, 0 failed, 6 skipped, 4 xfailed.
- Before the change, the baseline was 1017 passed and 2 failed: `tests/test_encoding.py::test_terminal_output_{request,response}_charset_detection[big5-…]`. After C01–C04 alone, it was 1031 passed with the same 2 failures.
- Issue #6: from version 3.4.2, charset-normalizer rejects big5 for the old sample (卷首 repeated) and picks `johab`. The new sample is Article 1 of the UDHR in Traditional Chinese. Every version checked detects it as big5: 2.0.12, 3.0.1, 3.3.2, 3.4.0 to 3.4.4, and 3.5.0 to 3.5.2.
- `tests/test_clone_refactorings.py` adds 14 regression tests. The C01 tests also pass against the **original** `core.py`, which shows that the behaviour is unchanged.
- Token clone scan, exact matching: duplications drop from 1 to 0 at 50 tokens, and from 13 to 9 at 25 tokens.
- Cognitive complexity (flake8-cognitive-complexity): `raw_main` drops from 49 to 40, and `HTTPieArgumentParser.parse_args` from 11 to 8.
- `flake8` reports no new warnings.

### CI workflow fixes

`ubuntu-latest` now runs Ubuntu 26.04. That release has no builds of Python 3.7, 3.8 and 3.9, which are past end of life, so `actions/setup-python` failed before any step ran. GitHub has also retired the `macos-13` runner. This PR makes Python 3.11 the baseline, because 3.10 is close to end of life.

- `code-style.yml`, `benchmark.yml` and `content.yml`: Python 3.9 becomes `"3.11"`.
- `coverage.yml`: Python 3.10 becomes `"3.11"`.
- `tests.yml`: the Python matrix changes from 3.7–3.12 to 3.11–3.13, and `macos-13` becomes `macos-latest`.
- All five workflows: `actions/setup-python@v4` becomes `@v5`.
- Check Markdown Style: `case3_trackB/github_drafts.md` and this file get blank lines around headings and lists, so `make doc-check` passes.

### Test fixes for newer dependency versions

- **pyOpenSSL.** In the `pyopenssl: 1` jobs, `test_digest_auth[https-…]` failed with `ValueError: Context has already been used to create a Connection, it cannot be mutated again`. HTTPie shares one SSL context across connections. urllib3 sets `verify_mode` on that context for each new connection, here the retry after the digest `401`. pyOpenSSL 26.2.0 turned this from a deprecation warning into an error. `setup.cfg` now pins `pyopenssl<26.2` in the `dev` extras. Only the test suite injects pyOpenSSL, so HTTPie at runtime is not affected.
- **Python 3.12.** `test_naked_invocation[args3]` failed because recent 3.12 releases print the list of invalid choices without quotes (`choose from all, colors, format, none`). Python 3.11, 3.13.18 and 3.14 quote the list. `tests/test_cli_ui.py` now builds the expected message from the running `argparse`, instead of hard-coding one format.

### Evidence

`case3_trackB/` holds the prompt log, the scan results before and after, the refactoring diff, and the figures.

### AI disclosure

Claude Code (Claude Opus 5.5) found the clones and generated the refactoring patches and tests. A second session (Claude Fable 5.2) re-verified them. A team member reviewed each change against the source before posting.
