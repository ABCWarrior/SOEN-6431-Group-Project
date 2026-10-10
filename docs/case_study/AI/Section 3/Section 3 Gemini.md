# Part A: Individual Tool Evaluation Sheet
### Model & Tool: Aider CLI (`v0.86.2`) + Google `gemini-3.8-flash`

---

### Metric 1: Time-to-First-Insight
* **Target:** How quickly did the tool deliver the first meaningful architectural understanding (Task 1 Call Tree)?
* **Empirical Data (From the log):**
  * Initial trial-and-error setup time: **~45 minutes** (resolving deprecated model endpoints from 18:01 to 18:06, quota exhaustion on `gemini-3.1-pro`, evaluating `deepseek-chat` balance limits from 18:29 to 18:52, and resolving CLI command typos).
  * Net time to generate complete Task 1 call tree: **< 2 minutes** (achieved at `18:07:22` on AST repo-map alone, and re-verified with staged files at `19:54:16`).
  * Total active querying analysis time for all 4 tasks: **~15–20 minutes**.
* **Key Observations:**
  * Once the endpoint was properly configured, Aider's 4,096-token AST repo-map enabled immediate zero-wait exploration of the 265 files without requiring manual file indexing.
* **Track B Candidate Rating:** **Very High / Fast** (Once endpoint was stabilized).

---

### Metric 2: Accuracy & Determinism
* **Target:** Did the tool produce ground-truth facts, or did it overgeneralize/hallucinate?
* **Empirical Data (From the log & Ground-Truth Verification):**
  * **Verified Structural Accuracies:**
    * Task 1 call flow was structurally sound (`httpie/__main__.py` $\rightarrow$ `core.py` $\rightarrow$ `argparser.py` $\rightarrow$ `client.py:collect_messages` $\rightarrow$ `models.py`).
    * Correctly avoided prompt-injected traps: when the prompt suggested `RequestData` as an example boundary model, the agent correctly identified that HTTPie passes an `argparse.Namespace` carrying `HTTPHeadersDict` and `RequestItems`.
    * Correctly classified `Authorization:Bearer_token` as a standard header token parsed by `KeyValueArgType` rather than assuming a custom `AuthPlugin` was triggered.
  * **Empirical Discrepancies & Hallucinations Identified:**
    1. *Unstaged Source Line Hallucination (Task 4):* When asked for exact line numbers defining base classes, the model cited `httpie/plugins/base.py (lines 14–37)` for `AuthPlugin` and `(lines 40–51)` for `TransportPlugin`. Because `plugins/base.py` was never added to the chat context, the agent confabulated plausible line numbers. In ground-truth source code (HTTPie v3.2.4), `AuthPlugin` begins at line 48 and `TransportPlugin` begins at line 83.
    2. *AST-Only Method Abstraction (Task 1, Session 7 vs. Session 13):* When running solely on the AST map (`18:07:22`), the agent hallucinated legacy/helper constructs (`enable_plugins()` and `BaseConfigDict.ensure_directory()`). Explicitly staging `httpie/core.py` into working memory at `19:54:16` corrected the call trace to the exact ground-truth method: `PluginManager.load_installed_plugins(directory=env.config.plugins_dir)`.
* **Key Observations:**
  * Structural call flows and communication contracts are highly deterministic and accurate, but line-level specifics will be hallucinated if target source files are not explicitly injected via `/add`.
* **Track B Candidate Rating:** **Medium / High Plausibility with Unstaged Confabulation**.

---

### Metric 3: Abstraction & Scannability
* **Target:** How easy was it for a human engineer to quickly comprehend the output diagrams and tables?
* **Empirical Data (From the log):**
  * Directly synthesized valid, ready-to-render **PlantUML C4 Component diagrams** (Task 2) using standard C4-PlantUML container boundaries.
  * Generated a syntax-valid **UML 2.0 Sequence Diagram** (Task 3) featuring typed BCE participants (`actor`, `boundary`, `control`, `participant`, `entity`), lifecycle activations, and numbered message flows.
  * Synthesized a clean 4-column **State & Data Transformation Table** mapping input to output across subsystem boundaries.
* **Key Observations:**
  * Filtered out ~95% of standard library boilerplate and utility noise, synthesizing clean architectural abstractions that eliminated the need for manual diagram drafting.
* **Track B Candidate Rating:** **Very High**.

---

### Metric 4: Setup & Tooling Friction
* **Target:** What friction, configuration barriers, or obstacles were encountered during installation and execution?
* **Empirical Data (From the log):**
  * *Local CLI setup:* Near zero friction (`pip install aider-chat` in virtual environment).
  * *API & Infrastructure friction:* Very high initial friction:
    * Model deprecation errors (`404 NOT_FOUND` for Gemini 1.5 Pro, 2.5 Pro, and 2.5 Flash).
    * Free-tier quota exhaustion (`429 RateLimitError` on Gemini 3.1 Pro Preview).
    * Upstream credit depletion on DeepSeek (`400 Insufficient Balance`).
    * Transient upstream service spikes (`503 Service Unavailable` on Gemini 3.8 Flash).
    * Accidental syntax typos (`aider aider`) creating unintended local files.
* **Key Observations:**
  * Friction shifted entirely away from traditional local compilation/tooling dependencies (C-compilers, Graphviz binaries) to cloud API availability, quota policies, and provider model naming churn.
* **Track B Candidate Rating:** **Medium / High API Friction**.

---

### Metric 5: Handling Scale / Complexity
* **Target:** How well did the tool manage the full 12 kLOC codebase without losing context or crashing?
* **Empirical Data (From the log):**
  * Repository scale: 265 files in `.git`.
  * Context mapping: Aider effectively compressed the entire repository into a **4,096-token AST repo-map**, maintaining global awareness across module boundaries.
  * Context staging: Required manually staging 7 core files (~18k tokens sent) to eliminate method-level hallucinations.
  * Generation ceilings: Hit maximum output token limits on comprehensive diagrams and traces, requiring multi-turn `continue` loops in Tasks 2 and 3.
* **Key Observations:**
  * The combination of Tree-Sitter AST mapping and selective file staging handled 12 kLOC with ease, but extensive architectural diagrams remain constrained by LLM single-turn output token limits.
* **Track B Candidate Rating:** **Medium / Constrained by Output Token Ceilings**.
