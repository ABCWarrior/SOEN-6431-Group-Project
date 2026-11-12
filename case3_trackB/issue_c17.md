# Issue — [Clone C17] Duplicated request-body exclusivity check in `HTTPieArgumentParser`

**Labels:** `clone`, `refactoring`, `case-study-3`

**Clone type:** Type 3 (gapped/modified) · 3 lines × 2, different collision argument lists

**Location (at `869f1c7`, the state the audit ran on):**
- `httpie/cli/argparser.py:401-406` — `_body_from_file()`
- `httpie/cli/argparser.py:410-416` — `_body_from_input()`

**Detection:** Aider CLI v0.86.2 + `gemini/gemini-3.8-flash`, second Track B run
(`case3_trackB/aider_prompt_log.md`, Candidate Pair 3). Not reported by the first run (C01–C16).
The line ranges the agent printed (297–303, 305–311) are wrong; the ranges above were re-derived
from git.

**Problem:** Both methods run the same two steps — `_ensure_one_data_source(...)` followed by
`self.args.data = ...` — but they pass different collision lists: `_body_from_file()` checks
`args.data` and `args.files`, `_body_from_input()` also checks `has_stdin_data`. The two copies
have therefore already diverged in what they consider a conflict, and any future addition to the
data sources (or to the check itself) has to be made twice.

**Proposed refactoring:** *Extract Method / Parameterize Method* → `_set_request_body(data,
*conflicting_sources)` that performs the check and the assignment; both callers delegate, keeping
their own collision lists.

**Acceptance criteria:** the same arguments reach `_ensure_one_data_source()` in the same order;
the successful path is unchanged; `pytest tests/test_clone_refactorings.py` passes; the upload and
stdin paths (`tests/test_uploads.py`, `tests/test_binary.py`) still pass where their dependencies
are installed.

**Known risk of the fix:** the extraction evaluates `getattr(fd, "buffer", fd)` and `data.encode()`
before the check instead of after it. A stdin payload that is both un-encodable and in collision
with another data source would report `UnicodeEncodeError` instead of the argparse error.

**State:** fixed by the agent in commit `0806f6f` on branch `case3-groupB-aider`
(PR: `case3-groupB-aider` → `case3-groupB`).
