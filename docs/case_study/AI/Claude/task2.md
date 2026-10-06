### 1. Subsystem Descriptions & Static Dependencies

#### A: CLI Argument Parsing & Context (`httpie/cli/`, httpie/context.py)

**Responsibilities**

- Turns `argv` and stdin into one validated `argparse.Namespace`.
- Owns the runtime `Environment` (streams, TTY flags, config, rich consoles).

**Core files and classes**

| File                            | Key elements                                                 |
| ------------------------------- | ------------------------------------------------------------ |
| cli/definition.py               | Module-level `parser`, built from a `ParserSpec`. Declares every option. |
| cli/options.py                  | `ParserSpec`, `Qualifiers`, `to_argparse()`. Declarative spec to `argparse`. |
| cli/argparser.py                | `HTTPieArgumentParser.parse_args(env, args)` runs a post-processing pipeline: `_apply_no_options`, `_process_request_type`, `_process_download_options`, `_setup_standard_streams`, `_process_output_options`, `_process_pretty_options`, `_process_format_options`, `_guess_method`, `_parse_items`, `_process_url`, `_process_auth`, `_process_ssl_cert`. Also `BaseHTTPieArgumentParser`, `HTTPieManagerArgumentParser`, `HTTPieHelpFormatter`. |
| cli/argtypes.py                 | `KeyValueArgType`, `SessionNameValidator`, `AuthCredentials`, `PARSED_DEFAULT_FORMAT_OPTIONS`. |
| cli/requestitems.py             | `RequestItems.from_args()` fills `.headers`, `.data`, `.files`, `.params`, `.multipart_data`. |
| cli/dicts.py                    | `HTTPHeadersDict` (a `CIMultiDict`), `RequestDataDict`, `RequestJSONDataDict`, `RequestFilesDict`, `RequestQueryParamsDict`, `MultipartRequestDataDict`. |
| cli/constants.py                | `OUT_REQ_HEAD/BODY`, `OUT_RESP_HEAD/BODY/META`, `PrettyOptions`, `PRETTY_MAP`, `RequestType`, `HTTP_OPTIONS`. |
| `cli/nested_json/`              | Nested-JSON key syntax: `parse`, `interpret_nested_json`, `NestedJSONSyntaxError`. |
| cli/exceptions.py, cli/utils.py | `ParseError`, `Manual`, `LazyChoices`.                       |
| `context.py`                    | `Environment` (stdin/stdout/stderr, `*_isatty`, encodings, lazy `config`, `rich_console`, `rich_error_console`, `log_error`, `as_silent`) and `LogLevel`. |

**Internal imports**

- `config`, `compat`, `encoding`, `utils`
- `plugins.registry` (auth plugins) and `plugins.builtin`
- `output.ui.palette` (from `context`), `output.formatters.colors` (from `definition`)
- `output.ui.{rich_palette, man_pages, rich_help}` (lazy)
- `sessions.VALID_SESSION_NAME_PATTERN` (from `argtypes`) and `ssl_` (from `definition`; `_is_key_file_encrypted` lazily in `argparser`)

**External packages**

- `argparse`
- `requests` (`requests.utils.get_netrc_auth` only)
- `multidict`
- `rich` (lazy: `Console`, `Text`)
- `colorama` (Windows only)
- `pygments` (indirectly, through `output.formatters.colors` at import time)
- stdlib: `curses`, `getpass`, `pathlib`, `dataclasses`, `enum`, `textwrap`, `warnings`
- `cli/nested_json/` imports only the stdlib.

------

#### B: HTTP Client & Transport Session (httpie/client.py, `sessions.py`, `adapters.py`)

**Responsibilities**

- Translates `Namespace` into a `requests.Request`, prepares it, and sends it through a configured `requests.Session`.
- Follows redirects manually.
- Persists HTTPie sessions (headers, cookies, auth).

**Core files and classes**

| File                    | Key elements                                                 |
| ----------------------- | ------------------------------------------------------------ |
| `client.py`             | `collect_messages()` is a generator and the main entry point. Helpers: `make_request_kwargs`, `make_send_kwargs`, `make_send_kwargs_mergeable_from_env`, `build_requests_session`, `make_default_headers`, `finalize_headers`, `transform_headers`, `apply_missing_repeated_headers`, `ensure_path_as_is`, `max_headers` (patches `http.client._MAXHEADERS`). |
| `sessions.py`           | `get_httpie_session()` and `Session(BaseConfigDict)`. It handles `update_headers`, `cookies`, `auth`, `remove_cookies`, `save()` and legacy format migration. |
| `adapters.py`           | `HTTPieHTTPAdapter.build_response()` re-wraps `response.headers` as `HTTPHeadersDict`, so repeated headers survive. |
| `ssl_.py` (adjacent)    | `HTTPieHTTPSAdapter`, `HTTPieCertificate`, `AVAILABLE_SSL_VERSION_ARG_MAPPING`. |
| `uploads.py` (adjacent) | `prepare_request_body`, `get_multipart_data_and_content_type`, `compress_request`. |

**Internal imports**

- `context.Environment`
- `cli.dicts`, `cli.constants`, `cli.nested_json` (B depends on A)
- `models.RequestsMessage`
- `plugins.registry` (transport plugins and auth)
- `config.BaseConfigDict`, `cookies.HTTPieCookiePolicy`, `legacy.*`
- `uploads`, `ssl_`, `compat`, `encoding`, `utils`

**External packages**

- `requests`: `Session`, `Request`, `PreparedRequest`, `adapters.HTTPAdapter`, `auth.AuthBase`, `cookies.RequestsCookieJar`, `utils.super_len`
- `urllib3`: `disable_warnings`, `util.SKIP_HEADER`, `SKIPPABLE_HEADERS`, `util.ssl_` (in `ssl_.py`)
- `requests_toolbelt`: `MultipartEncoder`, lazy
- stdlib: `http.client`, `http.cookiejar`, `http.cookies`, `ssl`, `json`, `zlib`, `urllib.parse`, `time.monotonic`

------

#### C: Output Processing & Stream Rendering (`httpie/output/`)

**Responsibilities**

- Selects a stream strategy (raw, encoded, pretty, buffered pretty).
- Formats headers, body and metadata through plugins, then writes bytes to `env.stdout`.

**Core files and classes**

| File            | Key elements                                                 |
| --------------- | ------------------------------------------------------------ |
| `writer.py`     | `write_message`, `write_stream`, `write_stream_with_colors_win`, `write_raw_data`, `build_output_stream_for_message`, `get_stream_type_and_kwargs`. |
| `streams.py`    | `BaseStream`, `RawStream`, `EncodedStream`, `PrettyStream`, `BufferedPrettyStream`, `DataSuppressedError`, `BinarySuppressedError`. |
| `processing.py` | `Conversion` (converter plugins by MIME), `Formatting` (runs enabled `FormatterPlugin`s). |
| `models.py`     | `ProcessingOptions(NamedTuple)` with `from_raw_args()` and `get_prettify(env)`. |
| `formatters/`   | `colors.ColorFormatter` (Pygments), `headers`, `json`, `xml`. |
| `lexers/`       | `http`, `json` (`EnhancedJsonLexer`), `metadata`.            |
| `ui/`           | `palette`, `rich_palette`, `rich_help`, `rich_progress`, `rich_utils`, `man_pages`. |
| `utils.py`      | `load_prefixed_json`.                                        |

**Internal imports**

- `context.Environment`
- `models` (shared kernel): `HTTPMessage`, `HTTPRequest`, `HTTPResponse`, `OutputOptions`, `RequestsMessage`, `RequestsMessageKind`
- `plugins` (`FormatterPlugin`, `ConverterPlugin`) and `plugins.registry`
- `cli.dicts`, `cli.constants`, `cli.argtypes` (C depends on A)
- `encoding`, `utils`

**External packages**

- `pygments`: lexers, `Terminal256Formatter`, `TerminalFormatter`, styles
- `rich`: `Console`, `Table`, `Text`, `Progress`
- `defusedxml` (lazy, in the XML formatter)
- `requests` (`writer.py` builds a bare `requests.PreparedRequest` for upload chunks)
- stdlib: `json`, `re`, `errno`, `abc`, `itertools`

------

#### Cross-subsystem static coupling

| Edge  | Evidence                                                     |
| ----- | ------------------------------------------------------------ |
| B → A | `client` and `sessions` import `cli.dicts`, `cli.constants`, `cli.nested_json`. |
| A → B | `cli.argtypes` imports `sessions`; `cli.definition` imports `ssl_`. |
| C → A | `output.models` imports `cli.constants` and `cli.argtypes`.  |
| A → C | `context` imports `output.ui.palette`; `cli.definition` imports `output.formatters.colors`. |
| B ↔ C | No direct imports. They connect only through `models.py` and `core.py`. |

A↔B and A↔C are bidirectional imports. The coupling is real, not just the ordered pipeline you described.

------

### 2. Communication Contracts & Data Boundaries

#### A → B

**Interface:** a synchronous in-process call.

- `core.raw_main()` calls `parser.parse_args(args=args, env=env)`, which returns the `Namespace`.
- `core.program()` then calls `collect_messages(env, args=args, request_body_read_callback=cb)`.

**Boundary data models**

| Model                                                        | Defined in                                    | Contents / role                                              |
| ------------------------------------------------------------ | --------------------------------------------- | ------------------------------------------------------------ |
| `argparse.Namespace` (`args`)                                | produced by `HTTPieArgumentParser.parse_args` | Fully validated and defaulted. Fields B reads: `method`, `url`, `headers`, `data`, `files`, `params`, `multipart_data`, `auth`, `auth_plugin`, `session`, `session_read_only`, `timeout`, `follow`, `max_redirects`, `max_headers`, `verify`, `cert`, `cert_key`, `cert_key_pass`, `proxy`, `ssl_version`, `ciphers`, `chunked`, `compress`, `offline`, `path_as_is`, `boundary`, `json`, `form`, `multipart`, `all`, `debug`. |
| `HTTPHeadersDict`                                            | cli/dicts.py                                  | Multi-value, case-insensitive headers. A `None` value means "suppress this header". |
| `RequestDataDict` / `RequestJSONDataDict` / `MultipartRequestDataDict` / `RequestFilesDict` / `RequestQueryParamsDict` | cli/dicts.py                                  | Flattened `RequestItems` output: `args.data`, `args.files`, `args.params`, `args.multipart_data`. |
| `Environment`                                                | `context.py`                                  | Passed alongside `args`. B uses `env.config.directory` (session location) and `env` for body preparation and session warnings. |
| `request_body_read_callback: Callable[[bytes], None]`        | closure in `core.program`                     | A reverse channel. B calls it for each body chunk read, and `core` forwards the chunk to C's `write_raw_data`. |

**Internal translation inside B** (not exposed to C)

- `make_request_kwargs()` returns `{method, url, headers, data, auth, params}`, which becomes a `requests.Request`.
- `make_send_kwargs()` and `make_send_kwargs_mergeable_from_env()` produce `{timeout, allow_redirects=False}` and `{proxies, stream=True, verify, cert}`.

#### B → C

**Interface:** a lazy generator. `collect_messages()` yields `RequestsMessage` values and `core.program()` pulls them one at a time.

- Each request is yielded before it is sent.
- Each response is yielded after `Session.send()` returns.
- Intermediate redirect responses are yielded only with `--all`.

**Boundary data models**

| Model                                                        | Defined in                          | Contents / role                                              |
| ------------------------------------------------------------ | ----------------------------------- | ------------------------------------------------------------ |
| `RequestsMessage = Union[requests.PreparedRequest, requests.Response]` | `models.py`                         | The only per-message payload.                                |
| `requests.PreparedRequest`                                   | `requests`                          | `method`, `url`, `headers` (HTTPie-fixed to preserve repeats), `body` (`str`, `bytes`, or a streaming iterator). Header values may be `bytes` or `SKIP_HEADER`. |
| `requests.Response` (decorated)                              | `requests`, via `HTTPieHTTPAdapter` | Opened with `stream=True`, so the body is unread. `.headers` is an `HTTPHeadersDict`. `._httpie_headers_parsed_at` is a monotonic timestamp used for the "Elapsed time" metadata. |
| `RequestsMessageKind` (`REQUEST` / `RESPONSE`)               | `models.py`                         | Inferred by `infer_requests_message_kind()`.                 |
| `OutputOptions(kind, headers, body, meta)`                   | `models.py`                         | Built per message by `core` via `OutputOptions.from_message(message, args.output_options)`. `core` may override `body` for streamed uploads. |
| `ProcessingOptions(debug, traceback, stream, style, prettify, response_mime, response_charset, json, format_options)` | output/models.py                    | Built once via `ProcessingOptions.from_raw_args(args)`. It is the Namespace subset that C needs. |
| `Environment`                                                | `context.py`                        | Provides `stdout`, `stdout_isatty`, `is_windows`, `stderr`, `colors`. |

**Call into C:** `write_message(requests_message, env, output_options, processing_options)`.

**Inside C**

- The message is wrapped in `HTTPRequest` or `HTTPResponse`, which are `HTTPMessage` adapters from `models.py`.
- `get_stream_type_and_kwargs()` picks a stream class and builds a `Formatting` with `Conversion` for pretty output.
- The stream yields `bytes` chunks, which go to `env.stdout.buffer`.

**Side channel:** `write_raw_data()` in C wraps raw upload chunks into a synthetic `PreparedRequest` (`is_body_upload_chunk=True`). That is the `request_body_read_callback` path from B to C.

------

### 3. C4 Component Diagram (PlantUML)

```
@startuml HTTPie_C4_Component
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml

LAYOUT_WITH_LEGEND()
title C4 Component Diagram - HTTPie Primary Pipeline (CLI parsing > HTTP client/session > Output rendering)

Person(user, "User / CLI Terminal", "Runs: http [options] URL [request-items]. May pipe data on stdin.")

System_Ext(remote, "Remote HTTP Server", "Target API or website. HTTP/1.x over TCP/TLS.")
System_Ext(stdout, "Stdout / Stderr", "Terminal (TTY) or redirected file/pipe.")
SystemDb_Ext(files, "Config & Session Files", "config.json and sessions/<host>/<name>.json (cookies, headers, auth)")

System_Ext(pkg_cli, "argparse, multidict", "stdlib / PyPI: option parsing, case-insensitive multi-dict")
System_Ext(pkg_http, "requests, urllib3, requests-toolbelt", "PyPI: Session, adapters, TLS, multipart")
System_Ext(pkg_render, "pygments, rich, defusedxml, colorama", "PyPI: lexers/formatters, consoles, safe XML, Windows ANSI")

Container_Boundary(httpie, "HTTPie Application (Python CLI process, orchestrated by core.py)") {
    Component(cli, "A: CLI Parsing & Context", "httpie/cli/, httpie/context.py", "HTTPieArgumentParser, RequestItems, Environment. Validates argv/stdin into a Namespace and owns the runtime Environment.")
    Component(client, "B: HTTP Client & Session", "httpie/client.py, sessions.py, adapters.py", "collect_messages(), HTTPieHTTPAdapter, HTTPieHTTPSAdapter, Session. Builds, sends and follows requests.")
    Component(output, "C: Output & Stream Rendering", "httpie/output/", "write_message(), BaseStream family, Formatting, Conversion. Selects stream strategy, formats, writes bytes.")
}

Rel(user, cli, "argv + stdin", "shell")

Rel(cli, client, "argparse.Namespace (args) + Environment + request_body_read_callback", "core.program() > collect_messages()")
Rel(client, output, "Iterable[RequestsMessage] (PreparedRequest | Response) + OutputOptions + ProcessingOptions + Environment", "core.program() > write_message()")

Rel(client, remote, "PreparedRequest (HTTP request)", "requests.Session.send()")
Rel(remote, client, "requests.Response (stream=True, headers = HTTPHeadersDict)", "HTTP response")

Rel(output, stdout, "bytes chunks", "env.stdout.buffer.write()")
Rel(cli, stdout, "usage / error messages", "env.log_error(), argparse help")

Rel(cli, files, "reads config.json (default_options, plugins_dir)", "Environment.config")
Rel(client, files, "loads / saves Session JSON", "get_httpie_session(), Session.save()")

Rel(cli, pkg_cli, "parses options, header multidicts", "import")
Rel(client, pkg_http, "Request / Session / adapters / TLS context", "import")
Rel(output, pkg_render, "Pygments lexers+formatters, rich Console, defusedxml", "import")

SHOW_LEGEND()
@enduml
```

Layout and `LAYOUT_WITH_LEGEND()` / `SHOW_LEGEND()` behaviour depends on your PlantUML version and C4-PlantUML revision. I did not render the diagram, so a syntax check by rendering it is still outstanding. The `!include` URL needs network access when it renders.