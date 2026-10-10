# Section 3 — Part B: Individual Tool Evaluation Sheet (Claude Stream)

**Evidence basis**

- Source: branch `group-B` @ `479500f`; artifacts `docs/case_study/AI/Claude/Task1–4.md`. Each file equals the model's fenced output verbatim; the only diff is an added H1 title.
- Transcripts: Claude Code JSONL logs (Sonnet 5.5), 2026-10-05/06. The work was **not one continuous session**. It was 13 sessions: 4 produced the deliverables (Task 1, 2, 3, 4), and the rest were prompt-iteration runs, including 2 on Opus 5.5. Each deliverable session started cold, with no shared context.
- Not covered: nothing was executed (`requests` is not installed in the environment) and no PlantUML was rendered. Claims below were checked by reading `httpie/` on `group-B`.

---

## 1. Time-to-First-Insight

- **Session Latency & Timings:** The final Task 1 run took 1 prompt and 1 turn. The first Grep for `console_scripts` ran at 3 s, and `__main__.py` and `core.py` were read at 5 s. The complete tree arrived at **~80 s** after 34 tool calls. A shorter earlier prompt produced a 6 kB tree in ~42 s with 8 tool calls. First answers for Tasks 2–4 took ~105 s, ~167 s and ~47 s. Total model time for the four deliverables is ~7.5 min, excluding the 56- and 28-minute idle gaps before the Task 2/4 "copy/paste" follow-ups.
- **Orientation Efficiency:** Autonomous. The Task 1 prompt named no files. Claude found entry points with Grep (`console_scripts|entry_points`) and `Glob httpie/**/*.py`, then read `__main__.py → core.py → context.py → config.py` in parallel batches. No manual file pointers were needed in any final session.
- **Candidate Metric Score: Fast** — one prompt gave a complete, line-cited call tree in about 1.5 minutes.

## 2. Accuracy & Determinism

- **Code Grounding & Line-Level Verification:** About 50 cited anchors were spot-checked against `group-B`. Examples: `argparser.py:151/205/282/322/409/448/492`, `core.py:32/46/146/170`, `client.py:43/107/156/212/281/288/325`, `manager.py:18-24/48/59-64/66-80`, `registry.py:13-21`, `base.py:16/72/96/124/129/140`, `processing.py:19-23/26-58`, `streams.py:63/211/238/252`, `tasks/plugins.py:66`, `sessions.py:278`, `setup.cfg:75-79`. All resolved to the named symbol. Two were off by one, pointing at the `@property` line (`context.py:139`, `models.py:70`). Anchors agree across Tasks 1, 3 and 4.
- **Nuance Detection & Architectural Realities:**
  - *Confirmed correct:*
    - There is no `RequestData` class. `grep` finds zero hits, and Task 2 flags this against the prompt's own wording.
    - `Authorization:Bearer_token` is parsed by `process_header_arg` (`requestitems.py:126`, `arg.value or None`). `_process_auth` leaves `args.auth=None`, so `BearerAuthPlugin` is not invoked.
    - `HTTPieHTTPSAdapter` extends the bare `requests` `HTTPAdapter` re-exported by `adapters.py` (`ssl_.py:10,40`), so it does not inherit `HTTPieHTTPAdapter`.
    - Import-time vs runtime is handled correctly:
      - The `Environment()` default argument is evaluated at definition time (`core.py:36,148`).
      - `parser` is built at import of `definition.py:956`.
      - `core.main` imports `parser` lazily (`core.py:160`).
      - Plugins load before parsing (`core.py:46`), which explains the `--auth-type` `lazy_choices` (`definition.py:687-689`).
    - Task 4 places `AuthPlugin` in argparse post-processing and `ConverterPlugin` in the output stage. It also gives the entry-point groups as `httpie.plugins.<type>.v1`. The source supports all three, but `TASK4_PLUGIN_ARCHITECTURE.md` §3 says otherwise (`httpie.client` hook, `httpie.cli` hook, `httpie.plugins.v1`).
  - *Discrepancies and unsupported assumptions:*
    - Task 2 says A, B and C "never call each other". `client.py:315` calls `cli.nested_json.unwrap_top_level_list_if_needed`, and `cli/argparser.py:562-595` calls `output.ui.man_pages` and `rich_help`. The note holds only for the main data flow, and Task 2's own coupling table lists these edges.
    - Task 2 states `Response.headers` is an `HTTPHeadersDict` without qualification (boundary table and C4 label). Task 3 later shows the wrapper applies to `http://` only. The two files are not reconciled.
    - Task 3 §2.6 gives `build_requests_session(ssl_version, ciphers, verify)`. The real signature is `(verify, ssl_version, ciphers)` (`client.py:156-160`). Task 3's diagram and Task 1 have it right.
    - Task 3 §2.8, §2.11–2.12 and the on-the-wire `GET /get` message describe `requests` and `urllib3` internals (default headers, `.netrc`, DNS→TCP→TLS). These packages were never opened: the only attempt, `import requests`, failed with `ModuleNotFoundError`. These steps come from model background knowledge, not traced source. The diagram's request line lists 4 headers, while §2.8 says `Accept-Encoding`, `Accept` and `Connection` are also merged.
    - Task 3 is stated as a static trace, and Task 4's code samples are stated as not executed.
  - *Determinism:* Each task was run once per model. The same Task 1 prompt re-run on Opus produced a differently structured output (~10% line overlap), so run-to-run variance was not measured.
- **Candidate Metric Score: High Accuracy** — no invented symbols or lines were found in the sample; the defects are one overstated claim, one unreconciled cross-task statement, one parameter-order slip, and unverified third-party internals.

## 3. Abstraction & Scannability

- **Structural Presentation:**
  - Task 1 is a nested call tree with `[file]` tags, followed by a Layer | File | Symbol map.
  - Task 2 has per-subsystem tables, a coupling-edge table, A→B and B→C boundary-model tables, and a C4-PlantUML diagram.
  - Task 3 has phase-ordered step tables with `file:line`, a 22-row state-transformation table with the four required columns, and a sequence diagram with typed participants, `box` grouping, `autonumber`, and 5 `activate` / 5 `deactivate`.
  - Task 4 follows discovery → types table → two contract code samples → reference table.
  - The diagrams were not rendered. No `plantuml` was on PATH, so syntax validity is unverified beyond paired `@startuml`/`@enduml`. Task 2's diagram also needs network access for its `!include`.
- **Signal-to-Noise Ratio:** Tasks 2 and 3 open with short lists of non-obvious findings. Boundaries and contracts are isolated: the `Namespace` hand-off, the `RequestsMessage` generator, and the `request_body_read_callback` reverse channel. Noise: Task 1 also covers the daemon and `httpie` manager paths outside the main request flow. Task 3 is 23 kB with multi-call table cells.
- **Candidate Metric Score: High** — consistently structured and scannable, but several cells are dense and the diagrams are unrendered.

## 4. Setup & Tooling Friction

- **Environment & Execution Barriers:** In the four deliverable sessions the logs show no compaction, interruptions, permission refusals or rate-limit errors. The one non-zero tool exit was Task 3's `python -c "import requests,urllib3"` (`ModuleNotFoundError`), and the output of the `sed` and `grep` commands in the same call still returned. Workflow friction came from two sources:
  - Tasks 2 and 4 needed a second turn ("give me markdown to copy/paste"), which regenerated ~15 kB and ~7.8 kB (33 s and 18 s).
  - Cold-start sessions re-read the same files. The Task 3 prompt says "subsystems identified earlier", but that session had no earlier output, and Claude did not note this.
- **Generation Stability:** No truncation was found (no `max_tokens` stop; the longest reply, 23.4 kB, ended with `@enduml` and notes). No hand-fixing was needed: the committed files match the fenced output. In a preliminary Task 1 session, a search for a local PlantUML jar hit the 60 s tool timeout and moved to the background. The final Task 2 and 3 sessions ran no PlantUML check.
- **Candidate Metric Score: Low Friction** — no blocking errors; the cost was one extra formatting turn on two tasks plus repeated file reads.

## 5. Handling Scale / Complexity (`httpie/` = 9,817 lines of `.py`)

- **Cross-Subsystem Correlation:** Task 3 follows one command through `__main__` → `core.raw_main` → `cli/{argparser,argtypes,requestitems}` → `client.collect_messages` → `adapters`/`ssl_` → `models.OutputOptions` → `output/{writer,streams,processing,formatters}` and back to the exit code. It handles the generator hand-off correctly: `yield prepared_request` (`client.py:107`), then `write_message` returns early because `OutputOptions.any()` is false, then the generator resumes to `yield response`. The Task 3 run read 20 files and Task 1 read 18, using whole-file reads rather than retrieval.
- **Context Retention & Deep Code Traversal:** Within a session there was no loss: peak input context was ~78–110k tokens per run and there was no compaction. Across tasks, retention was **not tested**, since each task ran in a separate session. Consistency came from re-deriving the same facts from source, and two cross-task inconsistencies (§2) went unreconciled. Import-time vs runtime ordering and plugin extension points were consistent across Tasks 1 and 4.
- **Candidate Metric Score: High Scalability** — the 9.8 kLOC package fit comfortably within one context window per task; multi-task context retention is not evidenced.
