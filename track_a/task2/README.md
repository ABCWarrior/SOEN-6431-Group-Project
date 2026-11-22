# Task 2 – Clone Classification & Semantic Audit (Track A)

> Brief: *Classify identified clones into Type 1 (Exact), Type 2 (Renamed), Type 3 (Gapped/Modified), or Type 4 (Semantic). Contrast static tool detection capabilities against GenAI semantic insights.*

Inputs: every clone reported by the three Track A detectors in Task 1 (12 CPD groups, 2 symilar pairs, 47 AST-scan pairs), plus a manual semantic search for Type 4 clones. Full tables: [tables.md](tables.md). Data: `clone_classification.csv`, `pair_metrics.csv`, `ast_pairs_adjudicated.csv`, `detector_precision.txt`. Script: `track_a/scripts/classify_clones.py`.

## 1. Taxonomy and classification procedure

| Type | Definition used (Roy & Cordy) | Objective test applied to each occurrence pair |
|---|---|---|
| Type 1 – exact | Identical except whitespace, layout, comments | raw token sequences identical |
| Type 2 – renamed | Syntactically identical; identifiers, literals or type names differ | identical after normalising identifiers → `ID`, literals → `LIT` ("blind" tokens) |
| Type 3 – gapped | Copied fragments with statements added, removed or changed | blind similarity ≥ 0.70 but not identical |
| Type 4 – semantic | Same behaviour or responsibility, different syntax | no syntactic similarity (blind < 0.70); established by reading the code |

Procedure for every candidate:
1. **Delimit** the clone region by hand to a complete syntactic unit: a function, a handler block or a rule tuple. CPD's region is only the maximal *exact* token run; for example, CPD stops in the middle of `self.format_options[` at the first differing literal.
2. **Measure** raw and blind identity and similarity for every pair of occurrences (Python `tokenize` + `difflib`) and derive the *metric-suggested* type.
3. **Read** the code and record the verdict (true clone / false positive), the type and the rationale.
4. **Check** the manual type against the metric-suggested type. A built-in consistency check also verifies that each of the 12 CPD groups maps to exactly one audited clone region.

## 2. Results

**22 audited clones → 17 true clones + 5 false positives.**

| Type | Count | Clone IDs |
|---|---|---|
| Type 1 | 1 | CL01 |
| Type 2 | 4 | CL06, CL08, CL15, CL16 |
| Type 3 | 9 | CL02, CL03, CL04, CL12, CL13, CL14, CL17, CL18, CL19 |
| Type 4 | 3 | CL20, CL21, CL22 |
| False positive | 5 | CL05, CL07, CL09, CL10, CL11 (all from CPD) |

**Manual vs metric agreement:** 16 of 17 true clones agree. The exception is CL08 (`except argparse.ArgumentTypeError as e` vs `except ParseError as e`). The metric says Type 3 only because the qualified name adds two tokens (`argparse .`). A differing type name is a Type 2 variation, so Type 2 is kept and the disagreement is documented.

### Type 1 – exact (1)
* **CL01** `core.py:86–96` ↔ `104–114`. The `except KeyboardInterrupt` / `except SystemExit` handlers are repeated in the outer and inner `try` of `raw_main()`. Raw identical, 51 tokens; the only clone CPD reports at MTS 50.

### Type 2 – renamed (4)
* **CL06** `formatters/headers.py:6–8`, `json.py:8–10`, `xml.py:55–57`. Three plugin constructors differ only in the option literals (`'headers','sort'` / `'json','format'` / `'xml','format'`). Blind identical; raw similarity 0.935.
* **CL15** `formatters/colors.py:81–86` ↔ `98–103`. `format_headers` / `format_metadata`: the same `pygments.highlight(...).strip()` call with renamed parameter and lexer. Blind 1.0. **Missed by CPD.**
* **CL16** `ssl_.py:55–57` ↔ `59–61`. `init_poolmanager` / `proxy_manager_for` inject `ssl_context` and delegate to `super()`. Blind 1.0. **Missed by CPD.**
* **CL08** `cli/argparser.py:431–434` ↔ `459–462`. The same `except … as e: if self.args.traceback: raise; self.error(e.args[0])` clause with a different exception type.

### Type 3 – gapped / modified (9)
* **CL03** `cli/argparser.py:90–105` ↔ `151–167`. The subclass re-implements the base `parse_args` instead of calling it: one statement added, `self.` → `super().`, `getattr(...)` → direct attribute access. CPD splits it into two overlapping groups (CG03 + CG06).
* **CL02** `cli/argparser.py:59–69` ↔ `580–591`. The `sys.exc_info()` inspection of the failing `argparse.Action`; the second copy has an extra condition and a different consequent.
* **CL04** `output/lexers/metadata.py:38–47` ↔ `49–57`. Pygments rule tuples with a different regex and one extra group (declarative data).
* **CL12 / CL13** `legacy/v3_1_0_session_cookie_format.py` ↔ `legacy/v3_2_0_session_header_format.py`. `post_process()` (blind 0.919) and `pre_process()` (0.795) copied between versioned migration modules with renamed constants. **CL13 is missed by CPD and symilar.**
* **CL14** `__main__.py:6–14` ↔ `manager/__main__.py:51–57`. The Ctrl+C → exit 130 wrapper; the http entry point adds lazy imports and `.value`.
* **CL17, CL18, CL19**: sibling methods with the same skeleton and different details (`uploads.py` `__iter__` pair, `rich_progress.py` `stop()` pair, `argparser.py` `_body_from_file` / `_body_from_input`). Found only by the AST scan.

### Type 4 – semantic (3), found only by the manual audit
No Track A tool reports these. Their normalised similarity is 0.41 / 0.51 / 0.60, below the Type 3 threshold.

* **CL20, "coerce str to bytes", re-implemented 4 times** (each excerpt condensed onto one line):
  ```python
  # uploads.py:65  (the helper)
  def as_bytes(data):            if isinstance(data, str): return data.encode() else: return data
  # models.py:163  HTTPRequest.body
  body = self._orig.body;        if isinstance(body, str): body = body.encode();  return body or b''
  # uploads.py:257 compress_request() - same module as as_bytes, but does not call it
  if isinstance(request.body, str): body_bytes = request.body.encode()  elif hasattr(request.body, 'read'): ...
  # client.py:201  finalize_headers()
  if isinstance(value, str): value = value.encode()
  ```
* **CL21, "is this body JSON?", decided twice:** `colors.py:180–187` sniffs with `json.loads(body)`, while `formatters/json.py:18–24` parses with `load_prefixed_json(body)`. The developers acknowledge it in the code: `# FIXME: the body also gets parsed in json.py`.
* **CL22, "load a JSON file, tolerating a missing or broken file":** `config.read_raw_config()` (`config.py:65–77`) vs `update_warnings._read_data_error_free()` (`internal/update_warnings.py:31–37`). A partial semantic clone: only the error policy differs (raise `ConfigFileError` vs return `{}`).

Searched but **not** classified as clones: byte-size and duration formatting (one implementation each, in `rich_progress.py`), and version comparison (single helper `utils.is_version_greater`, reused correctly).

## 3. False-positive audit (static tools)

**CPD: 5 of 12 groups are false positives**, all in the "repeated signature" family that token-based tools cannot distinguish from copied logic:

| ID | Location | CPD tokens | Why it is not duplication |
|---|---|---|---|
| CL05 | `core.py:146–149` ↔ `manager/__main__.py:32` | 31 | Only the parameter list `args: List[Union[str, bytes]] = sys.argv, env: Environment = Environment()) -> ExitStatus` matches; the bodies are unrelated |
| CL07 | `output/ui/rich_progress.py:62–65` ↔ `97–100` | 30 | `(BaseDisplay): def start(self, *, total, at, description) -> None:` – two overrides must share the signature |
| CL09 | `rich_progress.py:14–16 / 63–65 / 98–100` | 26 | Abstract method plus two overrides (interface conformance) |
| CL10 | `config.py:97–99` ↔ `sessions.py:183–185` | 25 | `return data` + the `post_process_data` hook signature; Template Method override, different bodies |
| CL11 | `uploads.py:149–152` ↔ `195–198` | 25 | Shared keyword parameters, because one function forwards to the other |

The pairwise metrics show why a tool cannot tell these apart from real clones: CL05, CL09 and CL10 are *raw-identical* (they would score as Type 1), and CL07 is blind-identical. Only reading the code reveals that the matched tokens are a signature, not logic.

**AST scanner: 37 of 47 pairs are false positives.** Blind normalisation makes short functions with the same *shape* look identical:
* 13 constructor / attribute-assignment idioms (e.g. `KeyValueArg.__init__` ↔ `NestedJSONSyntaxError.__init__`, blind 0.947)
* 13 short control-flow helpers (`isinstance` if/else, try → raise, create/append/return, lazy cache)
* 8 thin delegation wrappers (one keyword-argument call, `kwargs` + `super()`)
* 3 mirror or inverse operations (e.g. `HTTPMessage.content_type` decode vs `HTTPRequest.body` encode; `Session.pre_process_data` vs `post_process_data`)

29 of the 37 are cross-file. Adding a second condition, raw similarity ≥ 0.60 (the copies must share real identifiers), raises precision from 21 % to 56 % **without losing any true clone**.

## 4. Static detection capability (Track A summary)

| Detector | Precision (after audit) | Recall over the 17 confirmed clones | Type 1 | Type 2 | Type 3 | Type 4 |
|---|---|---|---|---|---|---|
| CPD, MTS 50 | 1/1 = 100 % | 1/17 | 1/1 | 0/4 | 0/9 | 0/3 |
| CPD, MTS 25 | 7/12 groups = 58 % | 6/17 | 1/1 | 2/4 | 3/9 | 0/3 |
| symilar `-d 3` | 2/2 = 100 % | 2/17 | 0/1 | 0/4 | 2/9 | 0/3 |
| AST scan ≥ 0.75 | 10/47 pairs = 21 % (56 % with raw ≥ 0.60) | 8/17 | 0/1 | 3/4 | 5/9 | 0/3 |
| **All Track A tools combined** | – | **14/17** | 1/1 | 4/4 | 9/9 | **0/3** |

Recall uses our 17 confirmed clones as the reference set; clones that none of our methods found cannot be counted, so these are upper bounds.

**What static tools do well:** deterministic and repeatable output (identical results on every run), exact file/line/token positions, fast (about 1.2 s per CPD run, 1.9 s for 49,770 AST comparisons), and full coverage of Type 1 and, together with the normalised AST scan, Type 2 and 3.

**What they cannot do:**
1. **Type 4 (0/3):** behaviour-level duplication has no textual footprint.
2. **Tell copied logic from mandatory repetition** (signatures, overrides, idioms). Every false positive above needed a human reading.
3. **Explain intent or suggest a refactoring:** CPD reports only positions and token counts.
4. **CPD for Python specifically:** it cannot abstract names or literals (the ignore flags have no effect), so 2 of 4 Type 2 clones (CL15, CL16) and 6 of 9 Type 3 clones are invisible to it.

## 5. Contrast with GenAI semantic insights (to complete with Subgroup B)

The Track B results are not produced by Track A. To compare like with like, Subgroup B should fill in this table using the **same clone IDs**, and add any AI-only finding as a new row after checking the cited lines exist (a hallucination check):

| Clone | Type (Track A) | Detected by AI? (Y/N) | AI's type | AI evidence / prompt | Notes (hallucination, wrong lines, …) |
|---|---|---|---|---|---|
| CL01 | 1 | | | | |
| CL06, CL08, CL15, CL16 | 2 | | | | |
| CL02, CL03, CL04, CL12, CL13, CL14, CL17, CL18, CL19 | 3 | | | | |
| CL20, CL21, CL22 | 4 | | | | |
| CL05, CL07, CL09, CL10, CL11 | FP | did the AI also flag these? | | | |
| *(new AI-only rows)* | | Y | | | verified against source? |

Questions the comparison should answer:
* Does the AI find any of the three Type 4 families (CL20–CL22) that Track A finds only by manual audit?
* Does the AI avoid the 5 CPD signature false positives?
* Are the AI's line numbers and token counts accurate, or approximate or invented (precision of evidence)?
* Is the AI's output repeatable across runs (CPD's is byte-identical)?
