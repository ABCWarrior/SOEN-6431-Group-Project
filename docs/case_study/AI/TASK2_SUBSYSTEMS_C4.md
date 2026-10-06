# Task 2 Traceability & Rationale Matrix: Subsystem Mapping & C4 Architecture

## Prompt

Analyze the HTTPie codebase for Subsystem Mapping & C4 Architecture.

Context & Target Subsystems:
Analyze the 3 core subsystems powering HTTPie's primary pipeline (CLI parsing -> HTTP client/session -> Output formatting & rendering):
- Subsystem A: CLI Argument Parsing & Context (httpie/cli/, httpie/context.py)
- Subsystem B: HTTP Client & Transport Session (httpie/client.py, httpie/sessions.py, httpie/adapters.py)
- Subsystem C: Output Processing & Stream Rendering (httpie/output/)

Required Output Format (Deliver exactly these 3 sections):

### 1. Subsystem Descriptions & Static Dependencies
For each of the 3 subsystems:
- Detail primary responsibilities and core files/classes.
- Map static dependencies: internal module imports and external packages (argparse, requests, urllib3, rich, pygments).

### 2. Communication Contracts & Data Boundaries
- Detail the communication interfaces between Subsystem A -> B, and Subsystem B -> C.
- Explicitly define the concrete boundary data models passed between them (e.g., Environment, RequestData, PreparedRequest, HTTPResponse, OutputOptions).

### 3. C4 Component Diagram (PlantUML)
Provide a complete, syntax-valid PlantUML C4 Component diagram (@startuml to @enduml) using standard C4-PlantUML syntax (`!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml`).
The diagram must visually model:
- The User / CLI Terminal
- The HTTPie Application Container enclosing the 3 Components
- External dependencies and targets (Remote Server, Stdout, External Python packages)
- Data flow arrows labeled with the exact boundary models passed.

## 1. Specification Cross-Reference & Coverage Mapping

| Assignment Requirement Source | Explicit Specification Text | Addressed in Task 2 Prompt? | Justification & Architectural Mapping in HTTPie |
| :--- | :--- | :---: | :--- |
| **Page 2: Primary Focus** | *"Trace CLI argument parsing down to network stream rendering."* | **YES** | The 3 selected subsystems (`cli/`, `client.py`+`sessions.py`, `output/`) form the exact, unbroken pipeline executing this primary domain focus. |
| **Page 3: Core Task 2** | *"Identify top 3 core modules/subsystems and map static dependencies."* | **YES** | Maps external packages (`argparse`, `requests`/`urllib3`, `rich`/`pygments`) and internal imports across the three subsystems. |
| **Page 3: Core Task 2** | *"...and communication contracts."* | **YES** | Explicitly queries interface definitions and parameter/return type contracts between modules. |
| **Page 7: Section 1 Deliverable** | *"C4 Component Diagram: Reconstructed architecture diagram detailing core modules and data boundaries."* | **YES** | Enforces official C4-PlantUML syntax (`C4_Component.puml`), modeling boundaries via concrete data structures (`Environment`, `PreparedRequest`, `OutputOptions`). |
| **Page 7: Section 1 Deliverable** | *"Core Subsystem Explanations: Clear documentation addressing Tasks 1–4."* | **YES** | Generates the textual architecture documentation required to accompany the visual diagram in Section 1. |

---

## 2. Architectural Boundary Justification (Why these 3 Subsystems?)

Rather than selecting arbitrary packages, these three subsystems were chosen because they define the architectural backbone of HTTPie:

1. **Subsystem A: CLI Argument Parsing & Context (`httpie/cli/`, `httpie/context.py`)**
   - *Boundary Role:* Ingestion layer. Translates raw POSIX CLI inputs and environment variables into structured domain configuration (`Environment`, `ParsedArgs`).
   - *Dependency Boundary:* Wraps standard library `argparse` with HTTPie-specific syntax parsers (`HTTPieArgumentParser`, `KeyValueArgType`).

2. **Subsystem B: HTTP Client & Transport Session (`httpie/client.py`, `httpie/sessions.py`)**
   - *Boundary Role:* Execution layer. Converts parsed arguments into executable network requests and manages persistent state (cookies, sessions).
   - *Dependency Boundary:* Encapsulates external `requests.Session` and `urllib3` using custom transport adapters (`HTTPieHTTPAdapter`) and SSL policies (`httpie/ssl_.py`).

3. **Subsystem C: Output Processing & Stream Rendering (`httpie/output/`)**
   - *Boundary Role:* Egress layer. Consumes raw byte streams and HTTP response metadata to produce human-readable, formatted terminal outputs.
   - *Dependency Boundary:* Interfaces with terminal formatters and external syntax libraries (`pygments`, `rich`) and handles output redirection/streaming (`stdout` vs. file download pipes).

---

## 3. Data Boundary Traceability

To fulfill the explicit rubric requirement on **"Data Boundaries"**, the prompt mandates tracking five concrete boundary models:
* `Environment`: Shared execution context (streams, dev flags, config directory).
* `RequestData` / `RequestHeadersDict`: Output of Subsystem A passed into Subsystem B.
* `requests.PreparedRequest`: Lower-level representation consumed by the transport layer.
* `HTTPResponse` / `requests.Response`: Network response payload handed from Subsystem B to Subsystem C.
* `OutputOptions`: Formatting rules derived during CLI initialization governing stream display.
