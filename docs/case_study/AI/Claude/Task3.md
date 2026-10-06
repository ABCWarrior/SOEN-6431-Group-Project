# Task 3: Feature Tracing & Dynamic Execution Flow

# HTTPie Feature Trace: `http GET https://httpbin.org/get Authorization:Bearer_token`

Static trace of the source tree (`httpie/`, version 3.2.4). Line numbers refer to the checked-out files.

## 0. Key observations

- **`Authorization:Bearer_token` is a header request item, not `--auth`.** The `:` separator classifies it as a header, so the value is sent as the literal string `Bearer_token` (no `Bearer ` prefix is added). `BearerAuthPlugin` (`plugins/builtin.py`) runs only for `--auth-type=bearer --auth=...`, and it is not invoked here.
- **No request is printed by default.** On a TTY the default `output_options` is `hb` (response headers and body). The request message is yielded, but `OutputOptions(headers=False, body=False).any()` is false, so `write_message` returns immediately.
- **The response body is read lazily.** `stream=True` is forced in `make_send_kwargs_mergeable_from_env`. The body bytes are not consumed until the output stream calls `Response.iter_content()` during rendering.
- **`HTTPieHTTPSAdapter` does not inherit `HTTPieHTTPAdapter`.** `ssl_.py` imports `HTTPAdapter` from `.adapters`, which is a re-export of `requests.adapters.HTTPAdapter`. The `build_response` override that wraps headers in `HTTPHeadersDict` therefore applies to `http://` only, not `https://`.

---

## 1. Step-by-Step Execution Call Trace

### Phase 0: Process bootstrap

| # | Call | File |
|---|------|------|
| 0.1 | Console script `http = httpie.__main__:main` | `setup.cfg` (`[options.entry_points]`) |
| 0.2 | `__main__.main()` → `from httpie.core import main` → `main()` | `httpie/__main__.py:6` |
| 0.3 | `core.main(args=sys.argv, env=Environment())` imports the module-level `parser` (`to_argparse(options)`, an `HTTPieArgumentParser`) and calls `raw_main(parser, main_program=program, args, env)` | `httpie/core.py:146`, `httpie/cli/definition.py:956` |
| 0.4 | `raw_main()` splits `program_name, *args`, calls `decode_raw_args(args, env.stdin_encoding)`, and checks `is_daemon_mode(args)` | `httpie/core.py:32` |
| 0.5 | `plugin_manager.load_installed_plugins(env.config.plugins_dir)` loads third-party plugins on top of the built-ins registered in `plugins/registry.py` (Basic, Digest and Bearer auth; Headers, JSON, XML and Color formatters) | `httpie/plugins/manager.py:66` |
| 0.6 | `config.default_options` are prepended if present. `parser.parse_args(args=args, env=env)` is called inside `try/except`. On success `check_updates(env)` runs, then `main_program(args=parsed_args, env=env)` | `httpie/core.py:46-103` |

### Phase 1: Ingestion (CLI tokens → request structures)

| # | Call | What happens |
|---|------|--------------|
| 1.1 | `HTTPieArgumentParser.parse_args(env, args)` (`cli/argparser.py:151`) → `argparse.parse_known_args` | Three positionals are defined in `cli/definition.py:57-94`: `method` (`nargs='?'`), `url`, and `request_items` (`nargs='*'`, `type=KeyValueArgType(*SEPARATOR_GROUP_ALL_ITEMS)`). Tokens bind as `method='GET'`, `url='https://httpbin.org/get'`, `request_items=['Authorization:Bearer_token']`. |
| 1.2 | `KeyValueArgType.__call__('Authorization:Bearer_token')` (`cli/argtypes.py:64`) → `tokenize()` | It looks for the earliest and longest separator among `:`, `;`, `:@`, `==`, `=`, `:=`, `@` and others. It finds `:` at position 13 and returns `KeyValueArg(key='Authorization', value='Bearer_token', sep=':', orig=...)`. The URL is never passed through this type, so the `://` in it is not mistaken for a separator. |
| 1.3 | `_apply_no_options` → `_process_request_type` | `args.json = args.form = args.multipart = False`. |
| 1.4 | `_process_download_options`, `_setup_standard_streams` | No `--download`, `--output` or `--quiet`, so `env.stdout` is unchanged. |
| 1.5 | `_process_output_options` (`argparser.py:492`) | `output_options = OUTPUT_OPTIONS_DEFAULT = 'hb'` on a TTY, or `'b'` when stdout is redirected. |
| 1.6 | `_process_pretty_options` → `_process_format_options` | `prettify = PRETTY_MAP['all'] = ['format','colors']` on a TTY, or `[]` when redirected. `format_options` is parsed into a dict (`headers.sort`, `json.format`, `json.indent=4`, `json.sort_keys`, `xml.*`). |
| 1.7 | `_guess_method` (`argparser.py:409`) | `'GET'` matches `^[a-zA-Z]+$`, so it is kept as the method. |
| 1.8 | `_parse_items` (`argparser.py:448`) → `RequestItems.from_args(request_item_args, request_type)` (`cli/requestitems.py:37`) | The rules table maps `':'` to `(process_header_arg, instance.headers)`. `process_header_arg` returns `arg.value or None`. The value is stored via `HTTPHeadersDict.add('Authorization', 'Bearer_token')`. Result: `args.headers`, `args.data` (empty `RequestJSONDataDict`), `args.files`, `args.params` and `args.multipart_data` are set. |
| 1.9 | `_process_url` (`argparser.py:205`) | The URL already matches `URL_SCHEME_RE`, so it is unchanged. |
| 1.10 | `_process_auth` (`argparser.py:282`) | `args.auth is None`, `auth_type is None` and the URL has no `user:pass@`, so no auth plugin is selected and `args.auth` stays `None`. |
| 1.11 | `_process_ssl_cert` | `cert_key_pass = SSLCredentials(None)`. No key is set, so there is no prompt. |
| 1.12 | Stdin check (`parse_args`) | If stdin is not a TTY and `--ignore-stdin` is absent, `_body_from_file(env.stdin)` is called. This is the environmental trap in scripts and CI: the body is read from stdin and the method may be forced to POST when it is not given. |
| 1.13 | Returns the finalized `argparse.Namespace` to `raw_main`, then to `program(args, env)` | `httpie/core.py:170` |

### Phase 2: Transport assembly and dispatch

| # | Call | What happens |
|---|------|--------------|
| 2.1 | `ProcessingOptions.from_raw_args(args)` (`output/models.py:35`) | Copies `debug, traceback, stream, style, prettify, response_mime, response_charset, json, format_options` into a `NamedTuple`. |
| 2.2 | `collect_messages(env, args, request_body_read_callback)` (`client.py:43`), a **generator** | Nothing runs until the first `next()` in `program()`'s `for message in messages` loop. No `--session` is used, so the session branch is skipped. |
| 2.3 | `make_request_kwargs(env, args, base_headers=None, ...)` (`client.py:325`) | `make_default_headers` gives `{'User-Agent': 'HTTPie/<version>'}`. No `Accept` or `Content-Type` is added because `args.data` is empty. `headers.update(args.headers)` adds `Authorization`. `finalize_headers` strips and `.encode()`s values (`b'Bearer_token'`). `prepare_request_body` leaves the empty body falsy. Result: `{'method':'get','url':...,'headers':HTTPHeadersDict,'data':<empty>,'auth':None,'params':[]}`. |
| 2.4 | `make_send_kwargs(args)` (`client.py:281`) | `{'timeout': args.timeout or None, 'allow_redirects': False}`. HTTPie handles redirects itself. |
| 2.5 | `make_send_kwargs_mergeable_from_env(args)` (`client.py:288`) | `{'proxies': {}, 'stream': True, 'verify': True, 'cert': None}`. The `--verify` string is mapped via `{'yes':True,'no':False,...}`. |
| 2.6 | `build_requests_session(ssl_version, ciphers, verify)` (`client.py:156`) | Creates `requests.Session()` and mounts `HTTPieHTTPAdapter` on `http://` and `HTTPieHTTPSAdapter(ciphers, verify, ssl_version)` on `https://`. Then it mounts every `plugin_manager.get_transport_plugins()` adapter at its prefix. |
| 2.7 | `HTTPieHTTPSAdapter.__init__` → `_create_ssl_context` (`ssl_.py:40,71`) | `create_urllib3_context(ciphers, ssl_version=resolve_ssl_version(...), cert_reqs=CERT_REQUIRED)` and `ensure_default_certs_loaded(ctx)`. `init_poolmanager` and `proxy_manager_for` inject this `ssl_context` into the urllib3 pool manager. `cert_verify` handles the `HTTPieCertificate` wrapper. |
| 2.8 | `requests.Request(**request_kwargs)` → `requests_session.prepare_request(request)` | Session defaults are merged (`Accept-Encoding`, `Accept`, `Connection`; HTTPie's `User-Agent` wins). requests may also look up `.netrc` credentials when `auth` is empty and `trust_env` is on. The result is a `PreparedRequest`. |
| 2.9 | `transform_headers(request, prepared_request)` (`client.py:212`) | Fixes `Content-Length` for `OPTIONS` and calls `apply_missing_repeated_headers` to restore repeated headers. `--path-as-is` and `--compress` are off, so those branches are skipped. |
| 2.10 | `yield prepared_request` (`client.py:107`) | Control returns to `program()`. `OutputOptions.from_message(message, 'hb')` gives `kind=REQUEST, headers=False, body=False`, so `write_message()` returns immediately and nothing is printed. `initial_request = message`. |
| 2.11 | The generator resumes: `requests_session.merge_environment_settings(url, proxies, stream, verify, cert)` | Merges `HTTP(S)_PROXY`, `REQUESTS_CA_BUNDLE` and `CURL_CA_BUNDLE` from the environment. |
| 2.12 | `with max_headers(args.max_headers): requests_session.send(prepared_request, **merged, timeout=..., allow_redirects=False)` (`client.py:113`) | `Session.send` → `get_adapter('https://...')` → `HTTPieHTTPSAdapter.send` → `cert_verify` → urllib3 `HTTPSConnectionPool.urlopen`. The steps are DNS (`getaddrinfo`), TCP connect to `:443`, TLS handshake using the injected `SSLContext`, then the request line and headers are written. With `stream=True` the call returns once the response headers are parsed. |
| 2.13 | `response._httpie_headers_parsed_at = monotonic()`. `get_expired_cookies(response.headers.get('Set-Cookie',''))`. `response.next` is `None` (200, no redirect), so the code reaches `yield response` and then `break` | `client.py:119-134`. A DNS or connect failure would surface as `requests.exceptions.ConnectionError`, mapped in `raw_main` (`core.py:124-137`) to a friendly message and `ExitStatus.ERROR`. |

### Phase 3: Egress and rendering

| # | Call | What happens |
|---|------|--------------|
| 3.1 | `program()` receives the `Response` | `OutputOptions.from_message(response, 'hb')` gives `kind=RESPONSE, headers=True, body=True, meta=False`. `final_response = message`. `check_status` is off. |
| 3.2 | `write_message(requests_message, env, output_options, processing_options)` (`output/writer.py:27`) | Builds `write_stream_kwargs = {stream: build_output_stream_for_message(...), outfile: env.stdout, flush: env.stdout_isatty or processing_options.stream}`. |
| 3.3 | `build_output_stream_for_message` → `get_stream_type_and_kwargs` (`writer.py:122,153`) | `message_type = HTTPResponse`. Auto-streaming is checked via `Content-Type == text/event-stream` (not the case for `application/json`). **TTY path:** `BufferedPrettyStream` with `conversion=Conversion()` and `formatting=Formatting(env, groups=['format','colors'], color_scheme, explicit_json, format_options)`. **Redirected path:** `RawStream(chunk_size=100 KiB)`, with no formatting and body only by default. |
| 3.4 | `Formatting.__init__` (`output/processing.py:29`) | `plugin_manager.get_formatters_grouped()`. For each group, each plugin class is instantiated and kept if `p.enabled`. The `format` group gives `HeadersFormatter`, `JSONFormatter` and `XMLFormatter`. The `colors` group gives `ColorFormatter`, which disables itself if `env.colors` is falsy. |
| 3.5 | `yield from BufferedPrettyStream(msg=HTTPResponse(response), output_options, **kwargs)`, driven by `BaseStream.__iter__` (`output/streams.py:63`) | Yields in order: headers, `b'\r\n\r\n'`, body chunks, then the trailing `\n\n` separator (TTY only). |
| 3.6 | Headers: `PrettyStream.get_headers()` → `HTTPResponse.headers` (`models.py:70`) | Builds the `HTTP/<version> 200 OK` status line plus `Name: value` lines from `response.headers`. `Formatting.format_headers` then runs `HeadersFormatter.format_headers` (sorts lines after the status line), then `ColorFormatter.format_headers` (`pygments.highlight` with `HttpLexer` and `TerminalFormatter` or `Terminal256Formatter`). The result is `.encode(output_encoding)`. |
| 3.7 | Body: `BufferedPrettyStream.iter_body()` (`streams.py:238`) → `HTTPResponse.iter_body(10 KiB)` → `requests.Response.iter_content()` | **This is where the body bytes are actually read from the socket.** Chunks are accumulated into a `bytearray` and checked for NUL bytes (binary suppression). |
| 3.8 | `process_body(body)` → `decode_chunk` → `smart_decode(bytes, charset)` → `formatting.format_body(content, mime='application/json')` | `JSONFormatter` (`formatters/json.py`) runs `load_prefixed_json` then `json.dumps(indent=4, sort_keys=True, ensure_ascii=False)`. `XMLFormatter` skips (mime mismatch). `ColorFormatter.format_body` → `get_lexer('application/json')` → `EnhancedJsonLexer` → `pygments.highlight`. The result is `smart_encode(..., output_encoding)`. |
| 3.9 | `write_stream(stream, outfile=env.stdout, flush=True)` (`writer.py:61`) | `buf = outfile.buffer`. For each `chunk` in the stream: `buf.write(chunk)`, then `outfile.flush()`. On Windows with colors, `write_stream_with_colors_win` writes chunks containing `\x1b[` as decoded text so colorama can translate the ANSI codes. |
| 3.10 | Return path | `program()` returns `ExitStatus.SUCCESS` and the `finally` closes `output_file` only if one was specified. `raw_main` → `core.main` → `__main__.main()` returns `exit_status.value` to `sys.exit`. |

---

## 2. State & Data Transformation Table

| Execution Stage | Input Data Structure | Output Data Structure | Governing Class / File |
|---|---|---|---|
| Process entry | `sys.argv: List[str]`, `Environment()` | `args: List[str]` (decoded), `env.program_name='http'` | `core.raw_main`, `core.decode_raw_args`, `context.Environment` |
| Plugin loading | entry-point groups `httpie.plugins.*.v1` | `plugin_manager: PluginManager(list)` of plugin classes (built-ins plus installed) | `plugins/manager.py`, `plugins/registry.py` |
| Positional binding | `['GET','https://httpbin.org/get','Authorization:Bearer_token']` | `Namespace(method='GET', url='https://…', request_items=[…])` | `cli/definition.py` (`to_argparse`), `HTTPieArgumentParser` |
| Item tokenization | `str 'Authorization:Bearer_token'` | `KeyValueArg(key='Authorization', value='Bearer_token', sep=':', orig=…)` | `cli/argtypes.py: KeyValueArgType` |
| Item classification | `List[KeyValueArg]`, `request_type=None` | `RequestItems(headers=HTTPHeadersDict{Authorization:Bearer_token}, data={}, files={}, params={}, multipart_data={})` | `cli/requestitems.py: RequestItems.from_args`, `process_header_arg` |
| Namespace finalization | raw `Namespace` + `Environment` (TTY or not) | final `Namespace`: `output_options='hb'`, `prettify=['format','colors']`, `format_options={…}`, `auth=None`, `headers`, `data`, `params` | `cli/argparser.py: _process_*`, `_parse_items`, `_guess_method` |
| Output config capture | final `Namespace` | `ProcessingOptions` (NamedTuple) | `output/models.py` |
| Request kwargs assembly | `Namespace`, `Environment` | `dict(method='get', url, headers=HTTPHeadersDict(bytes values), data=<empty>, auth=None, params=[])` | `client.make_request_kwargs`, `make_default_headers`, `finalize_headers`, `uploads.prepare_request_body` |
| Send settings | `Namespace` | `send_kwargs{timeout, allow_redirects=False}`; `mergeable{proxies={}, stream=True, verify=True, cert=None}` | `client.make_send_kwargs*` |
| Session and TLS setup | `verify, ssl_version, ciphers` | `requests.Session` with `HTTPieHTTPAdapter` (`http://`), `HTTPieHTTPSAdapter` (`https://`, holds `ssl.SSLContext`), plus plugin adapters | `client.build_requests_session`, `ssl_.py`, `adapters.py` |
| Request preparation | `requests.Request(**request_kwargs)` | `requests.PreparedRequest` (method, URL, merged headers, empty body) | `requests.Session.prepare_request`, `client.transform_headers` |
| Request message emission | `PreparedRequest` | generator `yield`, then `OutputOptions(REQUEST, headers=False, body=False)`, so write is skipped | `client.collect_messages`, `models.OutputOptions.from_message`, `core.program` |
| Env-merged send | `PreparedRequest` + `mergeable` kwargs | merged `proxies, stream, verify, cert` | `Session.merge_environment_settings` |
| Network dispatch | `PreparedRequest` | TLS-encrypted bytes on the wire, then `requests.Response` (`stream=True`, body unread, `raw`=urllib3 response) | `HTTPieHTTPSAdapter.send`, `cert_verify` (`ssl_.py`), urllib3 pool |
| Response emission | `requests.Response` | generator `yield response`; `_httpie_headers_parsed_at` set; `OutputOptions(RESPONSE, headers=True, body=True)` | `client.collect_messages`, `core.program` |
| Stream selection | `Response`, `OutputOptions`, `ProcessingOptions`, `Environment` | `BufferedPrettyStream` (TTY) or `RawStream` (piped) | `output/writer.py: get_stream_type_and_kwargs` |
| Formatter assembly | `groups=['format','colors']`, `format_options` | `Formatting.enabled_plugins=[HeadersFormatter, JSONFormatter, XMLFormatter, ColorFormatter]` (those with `enabled=True`) | `output/processing.py: Formatting` |
| Header rendering | `HTTPResponse.headers: str` (status line plus `Name: value`) | `bytes` (sorted, ANSI-colored, encoded to terminal encoding) | `models.HTTPResponse`, `HeadersFormatter`, `ColorFormatter` |
| Body read | `Response.iter_content(10240)` | `bytearray` of raw JSON bytes | `streams.BufferedPrettyStream.iter_body` |
| Body formatting | `bytes` → `str` (`smart_decode`) | pretty JSON `str` (indent 4, sorted keys) → ANSI-highlighted `str` → `bytes` | `JSONFormatter`, `ColorFormatter`, `get_lexer`/`EnhancedJsonLexer`, `encoding.smart_*` |
| Terminal write | `Iterable[bytes]` | bytes written to `env.stdout.buffer` (flushed per chunk on TTY) | `writer.write_stream` (`write_stream_with_colors_win` on Windows with colors) |
| Process exit | `ExitStatus` (enum) | integer process exit code | `status.ExitStatus`, `__main__.main` |

---

## 3. PlantUML Sequence Diagram

```plantuml
@startuml
title HTTPie: http GET https://httpbin.org/get Authorization:Bearer_token
autonumber
skinparam shadowing false
skinparam sequenceMessageAlign left
skinparam maxMessageSize 220

actor "User" as U

box "CLI Ingestion & Context" #E8F1FB
  boundary "CLI\n(__main__.py, cli/argparser.py,\nargtypes.py, requestitems.py)" as CLI
  control "Core Dispatcher\n(core.py: raw_main / program)" as CORE
end box

box "HTTP Client & Transport" #EAF7EA
  participant "Transport / Client\n(client.py, adapters.py, ssl_.py)" as TR
end box

entity "Remote Server\nhttpbin.org:443" as SRV

box "Output & Stream Rendering" #FDF3E3
  participant "Output Pipeline\n(writer.py, streams.py, processing.py,\nformatters/*)" as OUT
  boundary "Terminal Output\n(env.stdout)" as TERM
end box

== Phase 0/1: Ingestion ==
U -> CLI : shell invokes console script "http" with argv
activate CLI
CLI -> CORE : core.main(args=sys.argv: List[str], env=Environment())
activate CORE
CORE -> CORE : raw_main(parser, program, args, env)\ndecode_raw_args(args, env.stdin_encoding): List[str]
CORE -> CORE : plugin_manager.load_installed_plugins(env.config.plugins_dir)
CORE -> CLI : HTTPieArgumentParser.parse_args(env: Environment, args: List[str]): Namespace
CLI -> CLI : argparse.parse_known_args() binds method='GET', url='https://httpbin.org/get', request_items=['Authorization:Bearer_token']
CLI -> CLI : KeyValueArgType.__call__('Authorization:Bearer_token'): KeyValueArg(key='Authorization', value='Bearer_token', sep=':')
CLI -> CLI : _process_output_options(): 'hb'; _process_pretty_options(): ['format','colors']; _guess_method(): 'GET'
CLI -> CLI : _parse_items(): RequestItems.from_args(List[KeyValueArg], request_type) -> process_header_arg() -> HTTPHeadersDict
CLI -> CLI : _process_url(); _process_auth() (auth stays None, no plugin); _process_ssl_cert()
CLI --> CORE : argparse.Namespace(method, url, headers: HTTPHeadersDict, data={}, params, output_options='hb', prettify, auth=None, verify='yes', ...)

== Phase 2: Transport Assembly & Dispatch ==
CORE -> CORE : ProcessingOptions.from_raw_args(args: Namespace): ProcessingOptions
CORE -> TR : collect_messages(env, args, request_body_read_callback): Iterable[RequestsMessage]
activate TR
TR -> TR : make_request_kwargs(env, args): dict(method='get', url, headers=HTTPHeadersDict, data, auth=None, params)
TR -> TR : make_send_kwargs(args): timeout, allow_redirects=False\nmake_send_kwargs_mergeable_from_env(args): proxies, stream=True, verify=True, cert=None
TR -> TR : build_requests_session(verify, ssl_version, ciphers): requests.Session\nmount('http://', HTTPieHTTPAdapter); mount('https://', HTTPieHTTPSAdapter(SSLContext))
TR -> TR : requests.Request(method, url, headers, data, auth, params)\nSession.prepare_request(Request): PreparedRequest
TR -> TR : transform_headers(request, prepared_request)
TR -->> CORE : yield PreparedRequest (generator yield)
CORE -> OUT : write_message(PreparedRequest, env, OutputOptions(REQUEST, headers=False, body=False), processing_options)
activate OUT
OUT --> CORE : return None (output_options.any() is False, nothing printed)
deactivate OUT
CORE -> TR : next(messages) resumes collect_messages()
TR -> TR : Session.merge_environment_settings(url, proxies, stream, verify, cert): dict
TR -> SRV : Session.send(PreparedRequest, stream=True, verify=True, timeout, allow_redirects=False)\nHTTPieHTTPSAdapter.send() -> cert_verify() -> DNS, TCP :443, TLS handshake (SSLContext)
TR -> SRV : GET /get HTTP/1.1\nHost: httpbin.org\nUser-Agent: HTTPie/3.2.4\nAuthorization: Bearer_token
SRV --> TR : HTTP/1.1 200 OK + headers (Content-Type: application/json); body left unread (stream=True)
TR -> TR : response._httpie_headers_parsed_at = monotonic(); response.next is None
TR -->> CORE : yield requests.Response (generator yield)
deactivate TR

== Phase 3: Egress & Rendering ==
CORE -> OUT : write_message(Response, env, OutputOptions(RESPONSE, headers=True, body=True), ProcessingOptions)
activate OUT
OUT -> OUT : build_output_stream_for_message() -> get_stream_type_and_kwargs(): (BufferedPrettyStream, kwargs{env, conversion=Conversion(), formatting=Formatting(env, ['format','colors'], ...)})
OUT -> OUT : BufferedPrettyStream(msg=HTTPResponse(Response), output_options).__iter__()
OUT -> OUT : get_headers(): HTTPResponse.headers: str -> HeadersFormatter.format_headers() -> ColorFormatter.format_headers() (pygments HttpLexer): bytes
OUT -> SRV : iter_body(10240) -> Response.iter_content(10240) reads the lazy body via response.raw
SRV --> OUT : JSON body: bytes
OUT -> OUT : process_body(bytearray): smart_decode(); JSONFormatter.format_body() (indent=4, sort_keys); ColorFormatter.format_body() (EnhancedJsonLexer); smart_encode(): bytes
OUT -->> OUT : yield headers bytes, b'\\r\\n\\r\\n', body bytes, b'\\n\\n' (stream generator)
loop for chunk in stream
  OUT -> TERM : write_stream(stream, outfile=env.stdout, flush=True): buf.write(chunk: bytes); outfile.flush()
end
OUT --> CORE : return None
deactivate OUT
CORE --> CLI : ExitStatus.SUCCESS
deactivate CORE
CLI --> U : sys.exit(exit_status.value) = 0
deactivate CLI
@enduml
```

**Diagram notes:**
- `Output Pipeline` is added as a lifeline inside the Output box so the rendering phase has an actor. `core.py` calls into it, and it writes to `Terminal Output`.
- The remote server is drawn outside the three boxes because it is an external system.
- The redirected-stdout branch (`RawStream`, body only, no formatters) and the Windows colorama writer (`write_stream_with_colors_win`) are not drawn as separate paths.
