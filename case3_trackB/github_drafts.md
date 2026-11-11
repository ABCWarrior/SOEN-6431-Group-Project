# Case Study #3 – Track B GitHub drafts: branch, commits, issues, pull request

Nothing in this file has been posted. The refactoring is in the local working tree of `case3-groupB`; no commit, push, issue or PR exists yet. Review the changes first, then follow the steps below.

| Item | Value |
|---|---|
| Fork | `ABCWarrior/SOEN-6431-Group-Project` (public, fork of `httpie/cli`) |
| Branch | `case3-groupB` (local only, based on `master` @ `5b604c3`, HTTPie 3.2.4) |
| PR target | `master` **of the fork**, not upstream `httpie/cli` |
| Changed files | `httpie/core.py`, `httpie/cli/argparser.py`, `httpie/manager/cli.py`, `extras/man/httpie.1` (81 insertions, 77 deletions), new `tests/test_clone_refactorings.py` |
| Verified | `pytest`: 1031 passed, 5 skipped, 4 xfailed, 2 failed (the same 2 big5 charset tests fail before the change) |

## Before you post: two things to know

1. **Issues are disabled on the fork.** `gh` reports "repository has disabled issues", and the `L0veRamen` login has write access, not admin. The owner (`ABCWarrior`) has to turn them on: repository **Settings → General → Features → Issues**.
2. **`gh pr create` defaults to the upstream repository on a fork.** Always pass `-R ABCWarrior/SOEN-6431-Group-Project`, otherwise the PR is opened against `httpie/cli`.

## Step 1 — Review the change

```bash
git diff -- httpie extras
```

```bash
venv/bin/python -m pytest -q
```

## Step 2 — Create the four issues (after Issues are enabled)

Create them in this order so they get numbers 1 to 4 (the fork has no issues or PRs yet). Copy each title and body from the "Issue" sections below. Labels are optional; they must exist before they can be applied.

```bash
gh issue create -R ABCWarrior/SOEN-6431-Group-Project --title "[Clone C01] Duplicated Ctrl-C / SystemExit handlers in raw_main()" --body-file -
```

(`--body-file -` reads the body from standard input: paste the issue text, then press Ctrl-D. Repeat for C02, C03 and C04, or create the issues in the browser.)

## Step 3 — Commit

Commit 1, the refactoring and its tests:

```bash
git add httpie/core.py httpie/cli/argparser.py httpie/manager/cli.py extras/man/httpie.1 tests/test_clone_refactorings.py
```

```bash
git commit -m "Refactor duplicated CLI error handling and argument parsing (clones C01-C04)" -m "C01: extract handle_interrupt_or_exit() in raw_main(). C02: pull the shared parse_args() preamble up into BaseHTTPieArgumentParser._parse_common_args(). C03: extract get_failed_action(). C04: extract plugin_targets_argument() and fix the 'targets to install' help text of 'plugins uninstall'; man page regenerated. Adds 14 regression tests."
```

Commit 2, the Track B evidence. The `.docx` reports are left out on purpose: the final report carries student IDs and the fork is public.

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

Check the issue numbers in `case3_trackB/pr_body.md` first (it assumes #1 to #4), then:

```bash
gh pr create -R ABCWarrior/SOEN-6431-Group-Project --base master --head case3-groupB --title "Refactor duplicated CLI error handling and argument-parsing code (clones C01-C04)" --body-file case3_trackB/pr_body.md
```

## Step 5 — Put the links into the report

| Report location | What to paste |
|---|---|
| §2.4 table, rows Issue 1 to 4 | the four issue URLs |
| §2.4 table, row Commit(s) | the two commit hashes (`git log --oneline -2`) |
| §2.4 table, row Pull request | the PR URL |
| §2.4 Figure G1 | screenshot of the Issues list |
| §2.4 Figure G2 | screenshot of the PR "Files changed" tab |
| §5, Chen Qian row | issue, commit and PR links |
| "Core tasks" table, task 3 status | change to "Done" |

---

## Issue 1 — [Clone C01] Duplicated Ctrl-C / SystemExit handlers in `raw_main()`

**Labels:** `clone`, `refactoring`, `case-study-3`

**Clone type:** Type 1 (exact) · 51 tokens × 2 · 11 lines × 2

**Location:**
- `httpie/core.py:86-96` (argument-parsing phase)
- `httpie/core.py:104-114` (program-execution phase)

**Detection:** Claude Code (Track B). Confirmed by the Track B token scanner at 25 and 50 tokens, in exact and ignore-identifiers modes.

**Problem:** Both `try` blocks in `raw_main()` contain byte-for-byte identical `except KeyboardInterrupt` and `except SystemExit` handlers (write newline to stderr, optionally re-raise with `--traceback`, map to an exit status). Any change to interrupt/exit semantics has to be made twice.

**Proposed refactoring:** *Extract Method* → nested `handle_interrupt_or_exit(e)` helper returning the `ExitStatus`; both phases use `except (KeyboardInterrupt, SystemExit) as e: exit_status = handle_interrupt_or_exit(e)`.

**Acceptance criteria:** behaviour unchanged (exit codes, stderr output, `--traceback` re-raise); full test suite passes; new regression tests pin both phases.

---

## Issue 2 — [Clone C02] Duplicated `parse_args()` preamble in `BaseHTTPieArgumentParser` and `HTTPieArgumentParser`

**Labels:** `clone`, `refactoring`, `case-study-3`

**Clone type:** Type 3 (gapped/modified) · 110 / 113 tokens · 17 lines × 2

**Location:**
- `httpie/cli/argparser.py:90-106` (`BaseHTTPieArgumentParser.parse_args`)
- `httpie/cli/argparser.py:151-167` (`HTTPieArgumentParser.parse_args`)

**Detection:** Claude Code (whole pair). The token scanner only reports two disjoint fragments (29 and 33 tokens) at 25 tokens and nothing at 50, because the copy inserts `self.env.args = ...` and swaps `getattr(self.args, 'ignore_stdin', False)` for `self.args.ignore_stdin`.

**Problem:** the subclass re-implements the base-class preamble instead of extending it, so a fix to stdin or `--debug` handling in one copy does not reach the other.

**Proposed refactoring:** *Extract Method / Pull Up Method* → `BaseHTTPieArgumentParser._parse_common_args()` returns the unknown options; the subclass calls it and then runs its own processing pipeline (Template-Method style).

**Acceptance criteria:** `env.args` still points at the namespace before parsing starts (it is read while usage errors are rendered); full test suite passes.

---

## Issue 3 — [Clone C03] Duplicated "failed argparse action" inspection in usage rendering

**Labels:** `clone`, `refactoring`, `case-study-3`

**Clone type:** Type 3 · 59 / 71 tokens · 11–12 lines

**Location:**
- `httpie/cli/argparser.py:59-69` (`HTTPieHelpFormatter.add_usage`)
- `httpie/cli/argparser.py:580-591` (`HTTPieArgumentParser.print_usage`)

**Detection:** Claude Code. The token scanner reports a 44-token fragment at 25 tokens and nothing at 50.

**Problem:** Both blocks call `sys.exc_info()`, run the same three-part `isinstance` check and even carry the same copy-pasted comment (with the same typos). The second copy adds an `option_strings` condition.

**Proposed refactoring:** *Extract Function* → module-level `get_failed_action() -> Optional[argparse.Action]`.

**Acceptance criteria:** an invalid option value still shows that option in the short usage; full test suite passes.

---

## Issue 4 — [Clone C04] Copy-pasted plugin `TARGET` argument specs (with a copy-paste defect)

**Labels:** `clone`, `bug`, `refactoring`, `case-study-3`

**Clone type:** Type 2 (literal changes) · 26–27 tokens × 3

**Location:** `httpie/manager/cli.py:61-88` (`install`, `upgrade`, `uninstall` entries of `COMMANDS['plugins']`)

**Detection:** Claude Code. The token scanner reports it only at 25 tokens with identifiers and literals ignored (27 tokens).

**Defect caused by the clone:** the `uninstall` copy still says `'help': 'targets to install'`, which is shipped in `httpie plugins uninstall --help` and in the generated man page (`extras/man/httpie.1`).

**Proposed refactoring:** *Extract Function* → `plugin_targets_argument(verb)`; regenerate the man page with `extras/scripts/generate_man_pages.py`.

**Acceptance criteria:** each subcommand's help names its own verb; the man page diff touches only the two intended lines.

---

## Pull request — Refactor clone pairs C01–C04 (Case Study #3, Track B)

**Title:** `Refactor duplicated CLI error handling and argument-parsing code (clones C01-C04)`

**Base:** `master` of `ABCWarrior/SOEN-6431-Group-Project` · **Head:** `case3-groupB`

**Body:** see `case3_trackB/pr_body.md` (the same text, ready for `--body-file`).
