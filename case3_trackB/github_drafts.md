# Case Study #3 – Track B GitHub drafts: branch, commits, issues, pull request

Status (2026-11-14): everything in this file is posted. The branch `case3-groupB` is pushed, issues #1 to #4 and #6 are open, and PR #5 is open. Steps 1 to 6 below record how each item was posted.

The big5 test fix is called "Issue 5" in this file, but its GitHub number is **#6**. Issues and pull requests share one number sequence, and PR #5 had already taken 5.

| Item | Value |
|---|---|
| Fork | `ABCWarrior/SOEN-6431-Group-Project` (public, fork of `httpie/cli`) |
| Branch | `case3-groupB`, based on `master` at `5b604c3` (HTTPie 3.2.4) |
| PR target | `master` **of the fork**, not upstream `httpie/cli` |
| Changed files | Clones C01–C04: `httpie/core.py`, `httpie/cli/argparser.py`, `httpie/manager/cli.py`, `extras/man/httpie.1` (81 insertions, 77 deletions), and the new `tests/test_clone_refactorings.py`. Issue 5: `tests/test_encoding.py` |
| Verified | `pytest` after C01–C04: 1031 passed, 5 skipped, 4 xfailed, 2 failed. The same 2 big5 charset tests also fail before the change. After the Issue 5 fix: **1033 passed, 0 failed** |

## Two things to know before posting

1. **Issues were disabled on the fork at first.** `gh` reported "repository has disabled issues". The `L0veRamen` login has write access, not admin, so only the owner (`ABCWarrior`) could turn them on, in **Settings → General → Features → Issues**.
2. **On a fork, `gh pr create` targets the upstream repository by default.** Always pass `-R ABCWarrior/SOEN-6431-Group-Project`. Without it, the PR is opened against `httpie/cli`.

## Step 1 — Review the change

```bash
git diff -- httpie extras
```

```bash
venv/bin/python -m pytest -q
```

## Step 2 — Create the four issues

Create the issues after Issues are turned on. Create them in this order, so that they get numbers 1 to 4 (the fork had no issues or PRs yet). Copy each title and body from the "Issue" sections below. Labels are optional, and a label must exist before you can apply it.

```bash
gh issue create -R ABCWarrior/SOEN-6431-Group-Project --title "[Clone C01] Duplicated Ctrl-C / SystemExit handlers in raw_main()" --body-file -
```

`--body-file -` reads the body from standard input. Paste the issue text, then press Ctrl-D. Repeat for C02, C03 and C04, or create the issues in the browser.

## Step 3 — Commit

Commit 1 holds the refactoring and its tests:

```bash
git add httpie/core.py httpie/cli/argparser.py httpie/manager/cli.py extras/man/httpie.1 tests/test_clone_refactorings.py
```

```bash
git commit -m "Refactor duplicated CLI error handling and argument parsing (clones C01-C04)" -m "C01: extract handle_interrupt_or_exit() in raw_main(). C02: pull the shared parse_args() preamble up into BaseHTTPieArgumentParser._parse_common_args(). C03: extract get_failed_action(). C04: extract plugin_targets_argument() and fix the 'targets to install' help text of 'plugins uninstall'; man page regenerated. Adds 14 regression tests."
```

Commit 2 holds the Track B evidence. It leaves out the `.docx` reports on purpose, because the final report contains student IDs and the fork is public.

```bash
git add case3_trackB/prompt_log.md case3_trackB/github_drafts.md case3_trackB/pr_body.md case3_trackB/refactoring.diff case3_trackB/scan_results case3_trackB/tools case3_trackB/figures
```

```bash
git commit -m "Add Case Study 3 Track B evidence (prompt log, scans, figures, drafts)"
```

## Step 4 — Push and open the pull request

```bash
git push -u origin case3-groupB
```

Before you open the PR, check the issue numbers in `case3_trackB/pr_body.md`. The file assumes #1 to #4.

```bash
gh pr create -R ABCWarrior/SOEN-6431-Group-Project --base master --head case3-groupB --title "Refactor duplicated CLI error handling and argument-parsing code (clones C01-C04)" --body-file case3_trackB/pr_body.md
```

## Step 5 — Put the links into the report

| Report location | What to paste |
|---|---|
| §2.4 table, rows Issue 1 to 4 | The four issue URLs |
| §2.4 table, row Commit(s) | The two commit hashes (`git log --oneline -2`) |
| §2.4 table, row Pull request | The PR URL |
| §2.4 Figure G1 | A screenshot of the Issues list |
| §2.4 Figure G2 | A screenshot of the PR "Files changed" tab |
| §5, Chen Qian row | The issue, commit and PR links |
| "Core tasks" table, task 3 status | Change it to "Done" |

## Step 6 — Post Issue 5 and add it to PR #5

One commit on `case3-groupB` holds the fix and the report update. When you push the branch, the commit is added to the open PR #5.

```bash
git push origin case3-groupB
```

Create the issue, using the "Issue 5" section below as the body. GitHub numbers it #6.

```bash
gh issue create -R ABCWarrior/SOEN-6431-Group-Project --title "[Test] big5 charset-detection tests fail with charset-normalizer >= 3.4.2" --body-file -
```

Replace the PR body with the updated `pr_body.md`, which now also says "closes #6":

```bash
gh pr edit 5 -R ABCWarrior/SOEN-6431-Group-Project --body-file case3_trackB/pr_body.md
```

---

## Issue 1 — [Clone C01] Duplicated Ctrl-C / SystemExit handlers in `raw_main()`

**Labels:** `clone`, `refactoring`, `case-study-3`

**Clone type:** Type 1 (exact) · 51 tokens × 2 · 11 lines × 2

**Location:**

- `httpie/core.py:86-96` (argument-parsing phase)
- `httpie/core.py:104-114` (program-execution phase)

**Detection:** Claude Code (Track B). The Track B token scanner confirms it at 25 and 50 tokens, both with exact matching and with identifiers ignored.

**Problem:** The two `try` blocks in `raw_main()` have identical `except KeyboardInterrupt` and `except SystemExit` handlers. Each handler writes a newline to stderr, re-raises if `--traceback` is set, and maps the exception to an exit status. Any change to how interrupts and exits are handled has to be made twice.

**Proposed refactoring:** *Extract Method*. Add a nested helper, `handle_interrupt_or_exit(e)`, that returns the `ExitStatus`. Both phases then use `except (KeyboardInterrupt, SystemExit) as e: exit_status = handle_interrupt_or_exit(e)`.

**Acceptance criteria:** The behaviour does not change: the same exit codes, the same stderr output, and the same re-raise with `--traceback`. The full test suite passes. New regression tests pin the behaviour of both phases.

---

## Issue 2 — [Clone C02] Duplicated `parse_args()` preamble in `BaseHTTPieArgumentParser` and `HTTPieArgumentParser`

**Labels:** `clone`, `refactoring`, `case-study-3`

**Clone type:** Type 3 (gapped or modified) · 110 / 113 tokens · 17 lines × 2

**Location:**

- `httpie/cli/argparser.py:90-106` (`BaseHTTPieArgumentParser.parse_args`)
- `httpie/cli/argparser.py:151-167` (`HTTPieArgumentParser.parse_args`)

**Detection:** Claude Code found the whole pair. At 25 tokens, the token scanner reports only two separate fragments (29 and 33 tokens), and at 50 tokens it reports nothing. The reason is that the copy adds `self.env.args = ...` and replaces `getattr(self.args, 'ignore_stdin', False)` with `self.args.ignore_stdin`.

**Problem:** The subclass re-implements the preamble of the base class instead of extending it. A fix to stdin or `--debug` handling in one copy does not reach the other.

**Proposed refactoring:** *Extract Method / Pull Up Method*. Add `BaseHTTPieArgumentParser._parse_common_args()`, which returns the unknown options. The subclass calls it and then runs its own processing steps (Template Method style).

**Acceptance criteria:** `env.args` still points at the namespace before parsing starts, because the code that renders usage errors reads it. The full test suite passes.

---

## Issue 3 — [Clone C03] Duplicated "failed argparse action" inspection in usage rendering

**Labels:** `clone`, `refactoring`, `case-study-3`

**Clone type:** Type 3 · 59 / 71 tokens · 11–12 lines

**Location:**

- `httpie/cli/argparser.py:59-69` (`HTTPieHelpFormatter.add_usage`)
- `httpie/cli/argparser.py:580-591` (`HTTPieArgumentParser.print_usage`)

**Detection:** Claude Code. At 25 tokens, the token scanner reports a 44-token fragment. At 50 tokens, it reports nothing.

**Problem:** Both blocks call `sys.exc_info()` and run the same three-part `isinstance` check. They even have the same copied comment, typos included. The second copy adds a condition on `option_strings`.

**Proposed refactoring:** *Extract Function*. Add a module-level `get_failed_action() -> Optional[argparse.Action]`.

**Acceptance criteria:** When an option has an invalid value, the short usage message still shows that option. The full test suite passes.

---

## Issue 4 — [Clone C04] Copy-pasted plugin `TARGET` argument specs (with a copy-paste defect)

**Labels:** `clone`, `bug`, `refactoring`, `case-study-3`

**Clone type:** Type 2 (changed literals) · 26–27 tokens × 3

**Location:** `httpie/manager/cli.py:61-88` (the `install`, `upgrade` and `uninstall` entries of `COMMANDS['plugins']`)

**Detection:** Claude Code. The token scanner reports it (27 tokens) only at 25 tokens with identifiers and literals ignored.

**Defect caused by the clone:** The `uninstall` copy still says `'help': 'targets to install'`. This text ships in `httpie plugins uninstall --help` and in the generated man page (`extras/man/httpie.1`).

**Proposed refactoring:** *Extract Function*. Add `plugin_targets_argument(verb)`, then regenerate the man page with `extras/scripts/generate_man_pages.py`.

**Acceptance criteria:** The help text of each subcommand names its own verb. The man page diff changes only the two intended lines.

---

## Issue 5 — [Test] big5 charset-detection tests fail with charset-normalizer >= 3.4.2

**GitHub number:** #6 (PR #5 took number 5)

**Labels:** `bug`, `tests`, `case-study-3`

**Type:** A defect in the test data, not a clone. The baseline run before the refactoring found it (`pytest` at `5b604c3`: 1017 passed, 2 failed).

**Location:**

- `tests/test_encoding.py:17` (the `big5` entry of `CHARSET_TEXT_PAIRS`)
- Failing tests: `test_terminal_output_response_charset_detection[big5-…]` and `test_terminal_output_request_charset_detection[big5-…]`

**Problem:** The big5 sample repeats two characters, 卷首, for 70 bytes. From version 3.4.2, charset-normalizer scores this sample as 20 % "uncommon CJK" (`CjkUncommonPlugin`). That score equals the rejection threshold, so charset-normalizer drops big5. Only `johab` is left, and HTTPie prints Hangul (뻥솤…) instead of the Chinese text.

`setup.cfg` allows `charset_normalizer>=2.0.0`, so a fresh install gets a version on which the test fails. HTTPie's own `detect_encoding()` works correctly. The sample is too artificial for the detector.

| charset-normalizer | 2.0.12 | 3.0.1 | 3.3.2 | 3.4.0 | 3.4.1 | 3.4.2 | 3.4.3 | 3.4.4 | 3.5.0 | 3.5.1 | 3.5.2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Old sample (卷首 × n) | big5 | big5 | big5 | big5 | big5 | johab | johab | johab | johab | johab | johab |
| New sample (UDHR art. 1) | big5 | big5 | big5 | big5 | big5 | big5 | big5 | big5 | big5 | big5 | big5 |

**Proposed fix:** Replace the sample with a real Traditional Chinese sentence: Article 1 of the Universal Declaration of Human Rights (43 characters, 86 bytes in big5). The test still checks the same thing: HTTPie detects a big5 body whose `Content-Type` has no charset. Nothing in `httpie/` changes.

**Acceptance criteria:**

- `test_charset_text_pairs` still passes: the sample is longer than `TOO_SMALL_SEQUENCE` and is not valid UTF-8.
- `tests/test_encoding.py` gives 53 passed, and the full suite has 0 failures.
- Every charset-normalizer version in the table detects the new sample as big5.

---

## Pull request — Refactor clone pairs C01–C04 (Case Study #3, Track B)

**Title:** `Refactor duplicated CLI error handling and argument-parsing code (clones C01-C04)`

**Base:** `master` of `ABCWarrior/SOEN-6431-Group-Project` · **Head:** `case3-groupB`

**Body:** The text is in `case3_trackB/pr_body.md`, ready for `--body-file`.
