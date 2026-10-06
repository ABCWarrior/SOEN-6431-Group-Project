# Task 2: Subsystem Mapping, Communication Contracts & C4 Architecture

## 1. Subsystem Descriptions & Static Dependencies

### Subsystem A: CLI Argument Parsing & Context
* **Primary Responsibilities & Core Classes:**
  * Coordinates global runtime context and handles standard I/O stream configuration, TTY detection, quiet levels, and terminal color capabilities (`httpie.context.Environment`).
  * Parses command-line inputs, key-value request items, credentials, formatting options, and URL shorthands (`httpie.cli.argparser.HTTPieArgumentParser`, `httpie.cli.argparser.BaseHTTPieArgumentParser`).
  * Organizes and validates request inputs such as headers, query parameters, multipart data, and form/JSON payloads (`httpie.cli.requestitems.RequestItems`, `httpie.cli.argtypes.*`).
  * Provides multi-map and case-insensitive header container primitives (`httpie.cli.dicts.HTTPHeadersDict`, `httpie.cli.dicts.MultiValueOrderedDict`).
* **Static Dependencies:**
  * **Internal Modules:** `httpie.config` (`Config`, `DEFAULT_CONFIG_DIR`), `httpie.plugins.registry` (`plugin_manager`), `httpie.encoding`, `httpie.utils` (`ExplicitNullAuth`, `get_content_type`), `httpie.cli.constants`, `httpie.cli.exceptions`, `httpie.cli.nested_json`.
  * **External Packages:** `argparse`, `sys`, `os`, `re`, `errno`, `curses` (POSIX), `colorama` (Windows), `rich` (`rich.console.Console`, `rich.text.Text`).

---

### Subsystem B: HTTP Client & Transport Session
* **Primary Responsibilities & Core Classes:**
  * Translates parsed CLI options into concrete HTTP requests, managing chunking, compression, and request body compilation (`httpie.client.collect_messages`, `make_request_kwargs`, `make_send_kwargs`).
  * Manages custom transport adapters preserving duplicate header names and providing custom cipher/TLS configurations (`httpie.adapters.HTTPieHTTPAdapter`, `httpie.ssl_.HTTPieHTTPSAdapter`).
  * Handles persistent session storage, session-bound headers, credentials, and cookie lifecycle across transactions (`httpie.sessions.Session`, `httpie.sessions.get_httpie_session`).
* **Static Dependencies:**
  * **Internal Modules:** `httpie.cli.dicts` (`HTTPHeadersDict`), `httpie.cli.constants`, `httpie.cli.nested_json`, `httpie.context` (`Environment`), `httpie.models` (`RequestsMessage`), `httpie.plugins.registry` (`plugin_manager`), `httpie.ssl_` (`HTTPieCertificate`, `HTTPieHTTPSAdapter`), `httpie.uploads` (`prepare_request_body`, `compress_request`), `httpie.utils` (`get_expired_cookies`, `url_as_host`), `httpie.cookies` (`HTTPieCookiePolicy`), `httpie.legacy`.
  * **External Packages:** `requests` (`requests.Session`, `requests.Request`, `requests.PreparedRequest`, `requests.Response`, `requests.auth.AuthBase`), `urllib3`, `http.client`, `http.cookiejar`.

---

### Subsystem C: Output Processing & Stream Rendering
* **Primary Responsibilities & Core Classes:**
  * Wraps raw request and response data into uniform domain message abstractions (`httpie.models.HTTPRequest`, `httpie.models.HTTPResponse`, `httpie.models.HTTPMessage`).
  * Applies syntax highlighting, XML/JSON pretty-printing, and formatting pipelines to headers and payloads (`httpie.output.formatters.colors.ColorFormatter`, `httpie.output.formatters.xml`, Pygments lexer integrations).
  * Writes messages or raw data streams to the designated output target (stdout, stderr, pager, or file) according to terminal capabilities and stream buffering requirements (`httpie.output.writer.write_message`, `write_stream`, `write_raw_data`).
  * Manages terminal UI elements like progress spinners and themes (`httpie.output.ui.rich_progress.*`, `httpie.output.ui.palette.*`, `httpie.output.ui.rich_palette.*`).
* **Static Dependencies:**
  * **Internal Modules:** `httpie.models` (`RequestsMessage`, `OutputOptions`, `RequestsMessageKind`), `httpie.output.models` (`ProcessingOptions`), `httpie.context` (`Environment`, `LogLevel`), `httpie.cli.constants`, `httpie.utils` (`split_cookies`, `parse_content_type_header`).
  * **External Packages:** `pygments` (lexers, formatters, token systems), `rich` (theme, console, progress, pager utilities), `requests` (response/request object references).

---

## 2. Communication Contracts & Data Boundaries

### Subsystem A $\rightarrow$ Subsystem B (CLI Parsing $\rightarrow$ Client & Transport)
* **Interface Contract:** Function call to `httpie.client.collect_messages(env, args, request_body_read_callback)` orchestrated by `httpie.core.program()`.
* **Concrete Boundary Data Models:**
  * `httpie.context.Environment`: Carries active standard I/O streams (stdin, stdout, stderr), terminal configuration, quiet flags, color capabilities, and configuration directories.
  * `argparse.Namespace`: Carries fully parsed and validated CLI arguments, including:
    * `url`: Final transformed target URL.
    * `method`: Inferred or explicitly supplied HTTP method.
    * `headers`: Instances of `httpie.cli.dicts.HTTPHeadersDict`.
    * `data`, `files`, `params`, `multipart_data`: Structured request content containers.
    * `auth`: Authentication credentials (`AuthCredentials` or `requests.auth.AuthBase` instance from plugins).
    * `output_options`: Output display control string (e.g., `'hb'`).
    * Session, SSL, and transport parameters (`session`, `verify`, `cert`, `cert_key`, `ssl_version`, `ciphers`).

### Subsystem B $\rightarrow$ Subsystem C (Client & Transport $\rightarrow$ Output Processing)
* **Interface Contract:** Generator stream loop in `httpie.core.program()` iterating over yielded messages from `collect_messages()` and invoking `httpie.output.writer.write_message()`.
* **Concrete Boundary Data Models:**
  * `httpie.models.RequestsMessage`: A union type representing either `requests.PreparedRequest` or `requests.Response`.
  * `httpie.models.OutputOptions`: Encapsulates message classification (`RequestsMessageKind.REQUEST` vs `RequestsMessageKind.RESPONSE`) and boolean display flags (`headers`, `body`, `meta`).
  * `httpie.output.models.ProcessingOptions`: Stylistic rendering parameters derived from CLI args (`prettify`, `color_scheme`, `format_options`, `sorted_keys`).
  * `httpie.models.HTTPMessage` (`HTTPRequest` / `HTTPResponse`): Concrete adapters wrapping `requests.PreparedRequest` and `requests.Response` respectively, exposing standardized iteration, metadata, and header serialization methods consumed by output formatters.

---

## 3. C4 Component Diagram (PlantUML)

```plantuml
@startuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml

LAYOUT_WITH_LEGEND()

Person(user, "User / Developer", "Executes HTTPie CLI commands from terminal")

System_Ext(remote_server, "Remote HTTP Server", "Receives HTTP requests and serves HTTP responses")
System_Ext(terminal_out, "Standard Output / File", "Terminal display stdout/stderr or redirected file stream")

Container_Boundary(httpie_app, "HTTPie Application") {
    Component(subsystem_a, "CLI & Context Component", "Python / argparse, context.py", "Parses arguments, configures standard streams, resolves auth plugins, and sets up execution Environment.")
    Component(subsystem_b, "HTTP Client & Transport Component", "Python / client.py, sessions.py, adapters.py", "Prepares requests, manages persistent sessions, handles SSL/TLS, and executes transport over network.")
    Component(subsystem_c, "Output Processing & Rendering Component", "Python / output/*, models.py", "Wraps raw HTTP messages, executes formatting/colouring pipelines, and streams content to output targets.")
}

System_Ext(pkg_requests, "requests & urllib3", "External HTTP library and connection pool")
System_Ext(pkg_rich_pygments, "rich & pygments", "External UI, formatting, and syntax-highlighting libraries")

Rel(user, subsystem_a, "Invokes CLI command", "CLI args, stdin")

Rel(subsystem_a, subsystem_b, "Initiates request execution", "Environment, argparse.Namespace (HTTPHeadersDict, Auth, Data)")
Rel(subsystem_b, pkg_requests, "Builds & dispatches requests", "requests.Request, requests.Session")
Rel(pkg_requests, remote_server, "Transmits wire HTTP packets", "HTTP / HTTPS")
Rel(remote_server, pkg_requests, "Transmits raw wire response", "HTTP / HTTPS")
Rel(pkg_requests, subsystem_b, "Returns response", "requests.Response")

Rel(subsystem_b, subsystem_c, "Yields HTTP transactions", "RequestsMessage (PreparedRequest, Response), Environment, OutputOptions, ProcessingOptions")
Rel(subsystem_c, pkg_rich_pygments, "Highlights and applies styles", "Tokens, Text, Theme")
Rel(subsystem_c, terminal_out, "Renders formatted streams", "Formatted bytes / text (stdout / stderr)")

@enduml
```
