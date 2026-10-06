# Task 3: Feature Tracing & Dynamic Execution Flow

## 1. Step-by-Step Execution Call Trace

### Phase 1: Ingestion & CLI Argument Parsing

1. **Entry Point & Environment Initialisation:**
   * Execution begins in `httpie/__main__.py:main()`, invoking `httpie.core.main()`.
   * `httpie.core.main()` invokes `raw_main()` in `httpie/core.py` with default arguments (`args=sys.argv`, `env=Environment()`).
   * `Environment.__init__()` in `httpie/context.py` binds initial execution attributes (stdin, stdout, stderr, character encodings, and terminal detection flags such as `stdout_isatty`).
   * `raw_main()` normalises byte arguments to strings using `decode_raw_args()`, and loads installed plugins via `httpie.plugins.manager.PluginManager.load_installed_plugins(env.config.plugins_dir)`.

2. **CLI Argument Parsing & Item Classification:**
   * `raw_main()` invokes `parser.parse_args(args=args, env=env)` on `HTTPieArgumentParser` (`httpie/cli/argparser.py`).
   * `HTTPieArgumentParser.parse_args()` executes `super().parse_known_args()`, matching tokens:
     * `method` $\rightarrow$ `'GET'`
     * `url` $\rightarrow$ `'https://httpbin.org/get'`
     * Remaining unparsed tokens $\rightarrow$ `['Authorization:Bearer_token']` stored in `args.request_items`.
   * `HTTPieArgumentParser._setup_standard_streams()` inspects TTY status and output redirection configurations.
   * `HTTPieArgumentParser._process_output_options()` inspects `--print` or defaults to `'print=None'`, setting `args.output_options = 'all'` or stdout defaults (`OUTPUT_OPTIONS_DEFAULT = 'hb'`).
   * `HTTPieArgumentParser._process_pretty_options()` sets `args.prettify = PRETTY_MAP['all']` if `env.stdout_isatty` evaluates to `True`.
   * `HTTPieArgumentParser._parse_items()` passes the token list to `httpie.cli.requestitems.RequestItems.from_args()`:
     * Token `'Authorization:Bearer_token'` is parsed using `KeyValueArgType` with separator `:` (`SEPARATOR_HEADER`).
     * It is appended to `self.headers`, producing an `HTTPHeadersDict` populated with `{'Authorization': 'Bearer_token'}`.
   * `HTTPieArgumentParser._process_url()` validates the URL against `URL_SCHEME_RE`. As `'https://'` is present, the target URL remains untouched.
   * `HTTPieArgumentParser._process_auth()` evaluates authentication parameters. No `--auth` flags were supplied, so explicit auth handler overrides are bypassed.
   * Parsed args (`argparse.Namespace`) is returned to `raw_main()`, which then transfers execution control to `httpie.core.program(args=parsed_args, env=env)`.

---

### Phase 2: Transport Assembly & Dispatch

1. **Request Assembly:**
   * In `httpie/core.py:program()`, `ProcessingOptions.from_raw_args(args)` constructs the rendering configuration object (`ProcessingOptions`).
   * `program()` invokes `httpie.client.collect_messages(env=env, args=args)`.
   * `httpie.client.make_request_kwargs()`:
     * Calls `make_default_headers(args)` to add baseline headers, notably `User-Agent: HTTPie/<version>`.
     * Merges user-specified headers (`args.headers`) containing `Authorization: Bearer_token`.
     * Applies `finalize_headers()` to strip extraneous whitespace and convert header values into byte/ASCII strings where required.
     * Invokes `httpie.uploads.prepare_request_body()`, returning `None` for data because no body items were supplied for this GET command.
     * Returns a dictionary of request keyword arguments (`method='get'`, `url='https://httpbin.org/get'`, `headers=HTTPHeadersDict`, `data=None`, `params=[]`).

2. **Session & Transport Adapter Construction:**
   * `httpie.client.build_requests_session()` creates an instance of `requests.Session()`.
   * It mounts custom transport adapters:
     * `HTTPieHTTPAdapter` mounted to `http://`.
     * `HTTPieHTTPSAdapter` mounted to `https://`, configured with TLS verification settings (`verify=True`) and cipher suites via `make_send_kwargs_mergeable_from_env()`.
   * `requests_session.prepare_request(request)` compiles the `requests.Request` into a `requests.PreparedRequest`.
   * `httpie.client.transform_headers()` verifies header constraints and ensures duplicate entries or content lengths are adjusted appropriately.

3. **Dispatch & Response Capture:**
   * `collect_messages()` yields the initial `prepared_request` (a `requests.PreparedRequest`) to `httpie.core.program()`.
   * Since `args.offline` is `False`, `collect_messages()` executes `requests_session.send()`:
     * Passes `prepared_request`, `timeout=None`, and `stream=True`.
     * Urllib3 pool managers establish the TLS handshake with `httpbin.org:443` and transmit the raw HTTP request bytes.
     * The response line, headers, and body socket are captured into a `requests.Response` object.
     * `response._httpie_headers_parsed_at = monotonic()` records the completion timestamp for elapsed time reporting.
   * `collect_messages()` yields the response instance back to `httpie.core.program()`.

---

### Phase 3: Egress & Stream Rendering

1. **Message Classification & Wrapper Packaging:**
   * Inside the `for message in messages:` iteration loop of `httpie.core.program()`:
     * When processing the yielded `PreparedRequest`:
       * `OutputOptions.from_message(message, args.output_options)` sets output controls (`headers=False`, `body=False` based on default `'hb'` targeting responses).
       * No request content is written to stdout.
     * When processing the yielded `Response`:
       * `OutputOptions.from_message(message, args.output_options)` resolves `RequestsMessageKind.RESPONSE`, setting `headers=True`, `body=True`, `meta=False`.
       * `exit_status = http_status_to_exit_status(message.status_code)`.

2. **Rendering Pipeline & Terminal Output:**
   * `program()` invokes `httpie.output.writer.write_message()` (`httpie/output/writer.py`):
     * Wraps the raw `requests.Response` inside the domain model `httpie.models.HTTPResponse`.
     * Constructs a stream pipeline using `httpie.output.streams.BufferedPrettyStream` or `EncodedStream`.
     * The stream pipeline invokes the formatters, including `httpie.output.formatters.colors.ColorFormatter`:
       * Pygments parses the response status line and headers (`HTTP/1.1 200 OK`, `Content-Type: application/json`, etc.), tokenising and colourising them with ANSI escape sequences according to the selected theme.
       * The response body is fetched from `response.iter_content()` and decoded. Pygments detects JSON syntax via `application/json`, formatting indents and applying syntax colours.
   * `write_message()` invokes `write_stream(stream, outfile=env.stdout, flush=True)`:
     * The formatted and colourised stream is written out to `env.stdout.buffer` (or standard stdout).
   * `program()` finishes cleanly and returns `ExitStatus.SUCCESS` (`0`), exiting via `sys.exit(0)`.

---

## 2. State & Data Transformation Table

| Execution Stage | Input Data Structure | Output Data Structure | Governing Class / File |
| :--- | :--- | :--- | :--- |
| **CLI Ingestion** | `sys.argv: List[str]` (`['http', 'GET', 'https://httpbin.org/get', 'Authorization:Bearer_token']`) | `args: argparse.Namespace` (`method='GET'`, `url='https://...'`, `request_items=[KeyValueArg]`) | `HTTPieArgumentParser`<br>`httpie/cli/argparser.py` |
| **Request Item Extraction** | `List[KeyValueArg]` | `HTTPHeadersDict({'Authorization': 'Bearer_token'})` | `RequestItems`<br>`httpie/cli/requestitems.py` |
| **Request Kwargs Assembly** | `args: argparse.Namespace`, `env: Environment` | `request_kwargs: Dict[str, Any]` (`method='get'`, `headers=HTTPHeadersDict`, `data=None`) | `make_request_kwargs()`<br>`httpie/client.py` |
| **Request Preparation** | `requests.Request(**request_kwargs)` | `prepared_request: requests.PreparedRequest` | `requests.Session`<br>`httpie/client.py` |
| **Transport Dispatch** | `prepared_request: requests.PreparedRequest` | `response: requests.Response` (raw socket / stream attached) | `HTTPieHTTPSAdapter`<br>`httpie/ssl_.py` & `httpie/client.py` |
| **Message Classification** | `response: requests.Response` | `output_options: OutputOptions` (`kind=RESPONSE`, `headers=True`, `body=True`) | `OutputOptions`<br>`httpie/models.py` |
| **Domain Model Adaptation** | `response: requests.Response` | `http_message: HTTPResponse` | `HTTPResponse`<br>`httpie/models.py` |
| **Formatting & Highlighting** | `HTTPResponse`, `ProcessingOptions` | Formatted ANSI Byte / Text Stream | `ColorFormatter`<br>`httpie/output/formatters/colors.py` |
| **Terminal Rendering** | Formatted ANSI Stream | Rendered terminal text on `env.stdout` | `write_stream()`<br>`httpie/output/writer.py` |

---

## 3. PlantUML Sequence Diagram

```plantuml
@startuml
autonumber
skinparam BoxPadding 10
skinparam ParticipantPadding 10

actor User as usr
boundary "Terminal / OS" as term

box "Subsystem A: CLI Parsing & Context" #EBF3FB
    boundary "HTTPieArgumentParser" as parser
    participant "RequestItems" as reqitems
    control "Core Dispatcher\n(httpie.core)" as core
end box

box "Subsystem B: HTTP Client & Transport" #F9FBE7
    participant "client.py" as client
    participant "requests.Session" as req_session
    participant "HTTPieHTTPSAdapter" as adapter
end box

entity "Remote Server\n(httpbin.org)" as srv

box "Subsystem C: Output Processing & Rendering" #F3E5F5
    participant "OutputOptions" as outopts
    participant "HTTPResponse\n(Domain Model)" as model
    participant "ColorFormatter\n(Pygments)" as formatter
    boundary "Writer\n(output/writer.py)" as writer
end box

usr -> term: http GET https://httpbin.org/get Authorization:Bearer_token
activate term

term -> core: main(args, env)
activate core

core -> parser: parse_args(env, args)
activate parser

parser -> parser: _setup_standard_streams()
parser -> reqitems: from_args(['Authorization:Bearer_token'])
activate reqitems
reqitems --> parser: HTTPHeadersDict({'Authorization': 'Bearer_token'})
deactivate reqitems

parser -> parser: _process_output_options() & _process_pretty_options()
parser --> core: args (argparse.Namespace)
deactivate parser

core -> core: program(args, env)
core -> client: collect_messages(env, args)
activate client

client -> client: make_request_kwargs(env, args)
client -> client: build_requests_session()
client -> req_session: prepare_request(requests.Request)
activate req_session
req_session --> client: prepared_request (PreparedRequest)
deactivate req_session

client -->> core: yield prepared_request

client -> req_session: send(prepared_request, stream=True)
activate req_session
req_session -> adapter: send(prepared_request)
activate adapter
adapter -> srv: TLS Handshake & GET /get HTTP/1.1\nHost: httpbin.org\nAuthorization: Bearer_token
activate srv
srv --> adapter: HTTP/1.1 200 OK (Headers + Body Stream)
deactivate srv
adapter --> req_session: requests.Response
deactivate adapter
req_session --> client: requests.Response
deactivate req_session

client -->> core: yield response (requests.Response)
deactivate client

core -> outopts: from_message(response, args.output_options)
activate outopts
outopts --> core: OutputOptions(kind=RESPONSE, headers=True, body=True)
deactivate outopts

core -> writer: write_message(response, env, output_options, processing_o