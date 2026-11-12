## What this PR does

Extracts `_set_request_body()` in `HTTPieArgumentParser` so that `_body_from_file()` and
`_body_from_input()` share one path for the "there can only be one source of request data" check
and for the assignment to `self.args.data`.

**Clone:** C17 — `httpie/cli/argparser.py`, **Type 3** (gapped/modified).
C17 is not in the C01–C16 inventory of the first Track B run: it was found by the second,
independent agent run (Aider CLI v0.86.2 + `gemini/gemini-3.8-flash`) and refactored by that agent.
Both callers repeated `_ensure_one_data_source(...)` + `self.args.data = ...` with slightly
different collision lists (`data` + `files` vs `has_stdin_data` + `data` + `files`).

## Change

```diff
+    def _set_request_body(self, data, *conflicting_sources):
+        self._ensure_one_data_source(*conflicting_sources)
+        self.args.data = data
+
     def _body_from_file(self, fd):
-        self._ensure_one_data_source(self.args.data, self.args.files)
-        self.args.data = getattr(fd, 'buffer', fd)
+        self._set_request_body(
+            getattr(fd, 'buffer', fd),
+            self.args.data,
+            self.args.files,
+        )

     def _body_from_input(self, data):
-        self._ensure_one_data_source(self.has_stdin_data, self.args.data,
-                                     self.args.files)
-        self.args.data = data.encode()
+        self._set_request_body(
+            data.encode(),
+            self.has_stdin_data,
+            self.args.data,
+            self.args.files,
+        )
```

`httpie/cli/argparser.py`, +15/−5. Pattern: **Extract Method / Parameterize Method**.

## Verification

- `pytest tests/test_clone_refactorings.py -v` → **14 passed** (0.19 s), the regression suite added
  for the C01–C04 refactorings.
- Full suite on the author's Windows venv: 982 passed, 37 failed, 19 skipped, 4 xfailed. The
  failures are environmental and pre-date this branch: 16 multipart/upload tests cannot import
  `requests_toolbelt`, 11 `test_plugins_cli` tests hit a Windows console `UnicodeDecodeError`, 2 are
  the big5 charset-detection failures documented in §2.1 of the report, 1 is a CLI-UI assertion.
  None of them is in the two functions this PR touches (they could not run: those are exactly the
  upload tests). Stated as a limit, not as a pass.

## Behaviour and residual risk

The extraction keeps the argument list passed to `_ensure_one_data_source()` and the order of the
successful path unchanged. One ordering change: `getattr(fd, "buffer", fd)` and `data.encode()`
are now evaluated **before** the mutual-exclusion check. For a stdin payload that is both
un-encodable and in collision with another data source, the error reported would now be
`UnicodeEncodeError` instead of the argparse error; no test covers that combination. Recorded in
the report, §4.2.

## Evidence

- Agent transcript and prompt log: `case3_trackB/aider_prompt_log.md` (friction F1–F7, including the
  line-coordinate errors audited in report §4.1 AI-6/AI-7).
- The commit was authored by the agent itself (Aider `--auto-commits`), not by hand.
- Report: §1.5 (cross-check against the Claude run), §2.5 (this run's artifacts, Figures B6–B9).
