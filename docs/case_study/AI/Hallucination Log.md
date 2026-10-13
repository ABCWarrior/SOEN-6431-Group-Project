## Case 1: Semantic Generalization & False Adapter Inheritance (`adapters.py` vs. `ssl_.py`)

### 1. AI Inaccurate Claim (Track B: Generative Agent)
* **Context:** In Task 2 (Subsystem Mapping) and Task 3 (Dynamic Sequence Trace), the LLM (Gemini 3.8-Flash / Aider) claimed that both custom transport adapters inherit the same response-wrapping capabilities:
  > *"Subsystem B manages custom transport adapters preserving duplicate header names and providing custom cipher/TLS configurations (`httpie.adapters.HTTPieHTTPAdapter`, `httpie.ssl_.HTTPieHTTPSAdapter`)."* (Task 2, Section 1.B)
* **Hallucinated Assertion:** The agent asserted that for HTTPS requests, response headers are also wrapped inside `HTTPHeadersDict` at the adapter level to preserve multi-value headers with duplicate names.

---

### 2. Traditional Tool Verification (Track A: Deterministic Audit)
During Phase 3 reconciliation, Track A audited the claimed inheritance hierarchy using deterministic IDE symbol inspection and Python AST runtime reflection:

* **Deterministic Inspection Command:**
  ```bash
  python -c "
  from httpie.adapters import HTTPieHTTPAdapter
  from httpie.ssl_ import HTTPieHTTPSAdapter
  print('Is subclass:', issubclass(HTTPieHTTPSAdapter, HTTPieHTTPAdapter))
  print('HTTPS MRO:', [c.__name__ for c in HTTPieHTTPSAdapter.__mro__])
  "
  ```
* **Ground-Truth Output Returned:**
  ```text
  Is subclass: False
  HTTPS MRO: ['HTTPieHTTPSAdapter', 'HTTPAdapter', 'BaseAdapter', 'object']
  ```
* **Static Symbol Check (`grep`):**
  Searching for `build_response` across transport implementations revealed zero occurrences in `httpie/ssl_.py`:
  ```bash
  grep -rn "def build_response" httpie/
  # Output: httpie/adapters.py:7:    def build_response(self, req, resp):
  ```
  `HTTPieHTTPSAdapter` does not implement or override `build_response()` anywhere in the codebase.

---

### 3. Ground-Truth Source Code Evidence

#### A. HTTP Adapter Implementation (`httpie/adapters.py`, Lines 7–13)
`HTTPieHTTPAdapter` explicitly hooks into the response lifecycle to preserve duplicate headers:
```python
class HTTPieHTTPAdapter(HTTPAdapter):

    def build_response(self, req, resp):
        """Wrap the original headers with the `HTTPHeadersDict`
        to preserve multiple headers that have the same name"""
        response = super().build_response(req, resp)
        response.headers = HTTPHeadersDict(getattr(resp, 'headers', {}))
        return response
```

#### B. HTTPS Adapter Implementation (`httpie/ssl_.py`, Lines 10 & 44–55)
`HTTPieHTTPSAdapter` imports bare `HTTPAdapter` directly from requests, **bypassing** `HTTPieHTTPAdapter` entirely:
```python
from .adapters import HTTPAdapter  # Imports bare requests.adapters.HTTPAdapter

class HTTPieHTTPSAdapter(HTTPAdapter):  # Direct inheritance from requests base
    def __init__(self, verify: bool, ssl_version: str = None, ciphers: str = None, **kwargs):
        self._ssl_context = self._create_ssl_context(verify=verify, ssl_version=ssl_version, ciphers=ciphers)
        super().__init__(**kwargs)

    # Note: Only overrides init_poolmanager, proxy_manager_for, and cert_verify.
    # build_response() is completely absent!
```

---

### 4. Root Cause & Architectural Impact Analysis
* **Root Cause (Naming-Bias & Semantic Generalization):** 
  Because of lexical and conceptual symmetry (`HTTPieHTTPAdapter` vs. `HTTPieHTTPSAdapter`), the LLM relied on probabilistic pattern matching rather than resolving the static inheritance tree. It assumed feature parity without verifying the Class Hierarchy.
* **Architectural Reality:** 
  The feature of multi-header preservation at the adapter boundary only applies to cleartext `http://` transport. Under `https://`, HTTPie relies purely on requests' default `CaseInsensitiveDict` unless converted later down the pipeline. Track B's architectural diagram falsely presented uniform adapter behavior.

## Case 2: Idealized Architectural Decoupling & Boundary Hallucination (`client.py` vs. `cli/nested_json.py`)

### 1. AI Inaccurate Claim (Track B: Claude Code / Sonnet 5.5)
* **Context:** In Task 2 (Subsystem Mapping & Dependency Graph), Claude formulated an explicit architectural rule regarding subsystem boundaries:
  > *"Structural notes: A, B and C never call each other. `httpie/core.py` (`raw_main` / `program`) orchestrates all three."* (Task 2, Structural Notes & Boundary Contracts)
* **Hallucinated Assertion:** The AI asserted that Subsystem A (CLI Parsing & Ingestion) and Subsystem B (HTTP Client & Transport) maintain strict architectural decoupling, communicating solely via data models passed through the `httpie.core` orchestrator without direct inter-subsystem method invocations.

---

### 2. Traditional Tool Verification (Track A: Deterministic Audit)
During Phase 3 reconciliation, Track A audited static cross-subsystem imports and call hierarchies using deterministic AST dependency tracking and IDE symbol references:

* **Static Dependency Grep Check:**
  Auditing inter-module couplings within Subsystem B immediately refuted the isolation claim:
  ```bash
  grep -rn "from .cli" httpie/client.py
  # Output: httpie/client.py:20:from .cli.nested_json import unwrap_top_level_list_if_needed
  ```
* **IDE Call Hierarchy / AST Trace:**
  Inspecting usages of Subsystem A's nested JSON parser showed direct runtime execution inside Subsystem B's request assembly pipeline:
  `client.py:make_request_kwargs()` $\rightarrow$ `client.py:json_dict_to_request_body()` $\rightarrow$ `cli/nested_json.py:unwrap_top_level_list_if_needed()`.

---

### 3. Ground-Truth Source Code Evidence

#### Direct Subsystem B Coupling to Subsystem A (`httpie/client.py`, Lines 20 & 284–291)
Contrary to the claimed decoupling, `client.py` directly imports and invokes parsing routines from `httpie.cli`:
```python
# Line 20: Direct import across subsystem boundary
from .cli.nested_json import unwrap_top_level_list_if_needed

# Lines 284-291: Direct invocation during request body compilation
def json_dict_to_request_body(data: Dict[str, Any]) -> str:
    # Subsystem B directly relies on Subsystem A's syntax unwrapper
    data = unwrap_top_level_list_if_needed(data)
    if data:
        data = json.dumps(data)
    else:
        data = ''
    return data
```

Additionally, in Task 3 (§2.6), Claude demonstrated a secondary parameter hallucination by recording the function signature as `build_requests_session(ssl_version, ciphers, verify)`, whereas the ground truth (`client.py:140-144`) enforces `(verify: bool, ssl_version: str = None, ciphers: str = None)`.

---

### 4. Root Cause & Architectural Impact Analysis
* **Root Cause (Clean Architecture & Layering Bias):** 
  Large Language Models exhibit a systematic inductive bias toward "idealized architectures" (strict layered separation of concerns). When asked to synthesize subsystem boundaries, the generative agent hallucinated an absolute decoupling rule rather than reporting the imperfect reality of legacy cross-package coupling.
* **Architectural Reality:** 
  In real-world codebases, boundary leaks exist. Subsystem B is tightly coupled to Subsystem A's internal JSON parsing abstractions. Relying solely on GenAI abstractions would mislead engineers into believing Subsystem B is fully reusable as an independent HTTP library without `httpie.cli`.
