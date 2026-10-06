### 1. Step-by-Step Execution Call Trace

`Authorization:Bearer_token` is a plain header item, because `:` is `SEPARATOR_HEADER`. It is not `-A bearer`, so `BearerAuthPlugin` is never involved. The value is the literal string `Bearer_token` (underscore, no space).

#### Phase 1: Ingestion (httpie/__main__.py, `core.py`, `cli/*`)

1. The

    

   ```
   http
   ```

    

   console script calls

    

   ```
   httpie.__main__:main
   ```

   , which calls

    

   ```
   core.main()
   ```

    

   (

   core.py:146

   ).

   - `main` imports the pre-built parser (`definition.parser = to_argparse(options)`, definition.py:956).
   - It calls `raw_main(parser, program, sys.argv, Environment())`.

2. ```
   raw_main
   ```

    

   (

   core.py:32

   ) prepares the run:

   - `decode_raw_args` turns every argument into `str`.
   - The `--daemon` check is skipped.
   - `plugin_manager.load_installed_plugins(env.config.plugins_dir)` loads installed plugins. The built-in plugins were already registered at import time (registry.py:13).
   - `env.config.default_options` is prepended to the arguments.

3. ```
   HTTPieArgumentParser.parse_args(env, args)
   ```

    

   (

   argparser.py:151

   ) runs

    

   ```
   parse_known_args
   ```

   . The positionals are declared at

    

   definition.py:57-94

   :

   - `method='GET'` (the `?` quantifier is `nargs=OPTIONAL`).
   - `url='https://httpbin.org/get'`.
   - `request_items` is built by `KeyValueArgType(*SEPARATOR_GROUP_ALL_ITEMS).__call__`.

4. ```
   KeyValueArgType.__call__
   ```

    

   (

   argtypes.py:64

   ) tokenizes the item, honoring

    

   ```
   \
   ```

    

   escapes, then picks the earliest and longest separator.

   - `Authorization:Bearer_token` becomes `KeyValueArg(key='Authorization', value='Bearer_token', sep=':', orig=...)`.

5. Post-processing in

    

   argparser.py:169-180

   , in this order:

   - `_process_request_type`.
   - `_process_download_options`.
   - `_setup_standard_streams`.
   - `_process_output_options`: a TTY gets `'hb'`; redirected stdout gets `'b'`.
   - `_process_pretty_options`: a TTY sets `prettify=['format','colors']`.
   - `_process_format_options`.
   - `_guess_method`: `GET` matches `^[a-zA-Z]+$`, so it is kept.
   - `_parse_items`.
   - `_process_url`: the scheme is already present.
   - `_process_auth`: a no-op, because `args.auth is None` and no `--auth-type` was given.
   - `_process_ssl_cert`: sets `cert_key_pass=SSLCredentials(None)`.

6. ```
   _parse_items
   ```

    

   calls

    

   ```
   RequestItems.from_args
   ```

    

   (

   requestitems.py:36

   ).

   - The rules table maps `':'` to `process_header_arg` plus `instance.headers`.
   - The value goes in via `HTTPHeadersDict.add('Authorization','Bearer_token')` (dicts.py:18).
   - `headers`, `data`, `files`, `params` and `multipart_data` are copied onto the `Namespace`.

7. Back in `raw_main`, `check_updates(env)` (update_warnings.py:141) runs. It can print an update warning and spawn a detached `fetch_updates` daemon every 2 weeks. Then `program(args, env)` runs (core.py:170).

#### Phase 2: Transport assembly and dispatch (`client.py`, `ssl_.py`, `adapters.py`)

`collect_messages` is a generator, so nothing runs until the first `next()` in `for message in messages` (core.py:213).

1. `program` first builds `ProcessingOptions.from_raw_args(args)` (output/models.py:35).

2. First

    

   ```
   next()
   ```

    

   on

    

   ```
   collect_messages
   ```

    

   (

   client.py:43

   ). Session handling is skipped. It runs:

   - ```
     make_request_kwargs
     ```

      

     (

     client.py:325

     ):

     - `make_default_headers` gives `User-Agent: HTTPie/<ver>`. No `Accept` or `Content-Type` is added, because there is no data.
     - `headers.update(args.headers)`.
     - `finalize_headers` strips the values and encodes them to `bytes`.
     - `prepare_request_body` receives an empty `RequestJSONDataDict` and passes it through unchanged.
     - The result is `{method:'get', url, headers, data:{}, auth:None, params:<empty iterator>}`.

   - `make_send_kwargs` gives `{timeout:None, allow_redirects:False}`.

   - `make_send_kwargs_mergeable_from_env` gives `{proxies:{}, stream:True, verify:True, cert:None}`.

   - ```
     build_requests_session(verify=True, ssl_version=None, ciphers=None)
     ```

      

     (

     client.py:156

     ):

     - It builds a `requests.Session`.
     - It mounts `HTTPieHTTPAdapter` on `http://`.
     - It mounts `HTTPieHTTPSAdapter` on `https://` (httpie/ssl_.py:40). Its constructor builds one shared `SSLContext` via `create_urllib3_context(cert_reqs=CERT_REQUIRED)` plus `ensure_default_certs_loaded`.
     - It mounts any transport plugins.

   - ```
     requests.Request(**kwargs)
     ```

     , then

      

     ```
     Session.prepare_request
     ```

     :

     - This merges the session defaults (`Accept: */*`, `Accept-Encoding`, `Connection`).
     - It also does the netrc lookup, which is the caveat in the observations below.
     - It produces a `PreparedRequest` with the upper-cased method.

   - `transform_headers` / `apply_missing_repeated_headers` (client.py:212).

   - `yield prepared_request` (client.py:107).

3. `core.program` stores `initial_request`. `OutputOptions.from_message(msg, 'hb')` gives `headers=False, body=False`, because `H` and `B` are absent from `'hb'`. `write_message` returns immediately, so the request is not printed by default.

4. Second

    

   ```
   next()
   ```

    

   resumes the generator (

   client.py:108-133

   ):

   - `merge_environment_settings` merges env proxies, CA bundle and cert settings.
   - The `max_headers(0)` context manager sets `http.client._MAXHEADERS = inf`.
   - `Session.send(...)` picks the adapter by longest prefix, here `HTTPieHTTPSAdapter`.
   - `cert_verify` (httpie/ssl_.py:63) and `init_poolmanager` (httpie/ssl_.py:55) inject the shared context.
   - urllib3 then does DNS, TCP, the TLS handshake and `GET /get`. With `stream=True` the body is left unread.
   - `response._httpie_headers_parsed_at = monotonic()`.
   - `response.next` is `None`, because `allow_redirects=False` and there is no 3xx. So the generator does `yield response` and breaks.

#### Phase 3: Egress and rendering (`output/*`)

1. `OutputOptions.from_message(response, 'hb')` gives `(RESPONSE, headers=True, body=True, meta=False)`. `write_message` is called (core.py:234).

2. ```
   build_output_stream_for_message
   ```

    

   (

   writer.py:122

   ) calls

    

   ```
   get_stream_type_and_kwargs
   ```

    

   (

   writer.py:153

   ).

   - `Content-Type: application/json` is not `text/event-stream`, so `is_stream=False`.
   - A TTY with `['format','colors']` selects `BufferedPrettyStream`.
   - `Formatting(groups, env, color_scheme, explicit_json, format_options)` (processing.py:26) instantiates `HeadersFormatter`, `JSONFormatter`, `XMLFormatter` and `ColorFormatter`.
   - It also creates a `Conversion()`.

3. ```
   BufferedPrettyStream(msg=HTTPResponse(response), ...)
   ```

    

   is built, and

    

   ```
   BaseStream.__iter__
   ```

    

   (

   streams.py:63

   ) runs:

   - Headers:

      

     ```
     HTTPResponse.headers
     ```

      

     builds

      

     ```
     HTTP/1.1 200 OK\r\n...
     ```

     . Then

      

     ```
     Formatting.format_headers
     ```

      

     runs.

     - `HeadersFormatter` sorts the lines.
     - `ColorFormatter.format_headers` calls `pygments.highlight(HttpLexer, TerminalFormatter)`. `auto` style is the default, so this is the plain 16-colour formatter (colors.py:64).
     - The result is encoded to `bytes`, followed by `\r\n\r\n`.

   - Body: `BufferedPrettyStream.iter_body` (streams.py:238) pulls `response.iter_content(10240)`. This is the first body read from the socket. It accumulates a `bytearray` and raises `BinarySuppressedError` on a NUL byte.

   - ```
     process_body
     ```

      

     runs

      

     ```
     smart_decode
     ```

     , then

      

     ```
     Formatting.format_body(content, 'application/json')
     ```

     .

     - `JSONFormatter` runs `json.dumps(indent=4, sort_keys=True, ensure_ascii=False)`.
     - `ColorFormatter.get_lexer` resolves `JsonLexer` and swaps in `EnhancedJsonLexer`. It then highlights the body.
     - The result goes through `smart_encode`.

   - A trailing `\n\n` is yielded because stdout is a TTY (writer.py:146).

4. ```
   write_message
   ```

    

   picks the writer (

   writer.py:49

   ). This host is Windows and

    

   ```
   'colors'
   ```

    

   is in the prettify groups, so it uses

    

   ```
   write_stream_with_colors_win
   ```

   .

   - Chunks containing `\x1b[` are decoded and written as text to the colorama-wrapped stdout.
   - Other chunks go to `stdout.buffer`.
   - Each chunk is flushed because stdout is a TTY.
   - On POSIX it would use `write_stream`.

5. The third `next()` exhausts the generator, so `StopIteration` is raised. `program` returns `ExitStatus.SUCCESS`. `__main__.main` returns `.value` and the process exits with code 0.

#### Observations

- **netrc override:** `args.auth` is `None` and `--ignore-netrc` is not set. `requests.Session.prepare_request` can therefore run `get_netrc_auth(url)`. A `.netrc` entry for `httpbin.org` would overwrite the `Authorization` header with Basic auth.
- **HTTPS adapter inheritance:** `HTTPieHTTPSAdapter` extends `requests.adapters.HTTPAdapter` (re-exported via adapters.py), not `HTTPieHTTPAdapter`. So the `build_response` override (adapters.py:7) that wraps headers in `HTTPHeadersDict` only applies to `http://`, not `https://`.
- **Request not shown:** the request, including `Authorization`, is only shown with `-v` or `--print=H`.

### 2. State & Data Transformation Table

| Execution Stage             | Input Data Structure                                         | Output Data Structure                                        | Governing Class / File                                       |
| --------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| Entry / decode              | `sys.argv: List[str|bytes]`                                  | `List[str]`, plus `Environment` (stdio, `Config`, `colors`)  | `__main__.main`, `core.raw_main`, `decode_raw_args`, `context.Environment` |
| Plugin and config bootstrap | `env.config.plugins_dir`, `default_options`                  | Populated `plugin_manager` (`PluginManager(list)`), args with defaults prepended | plugins/manager.py, plugins/registry.py                      |
| Token parsing               | `['GET', url, 'Authorization:Bearer_token']`                 | `Namespace(method='GET', url, request_items=[KeyValueArg(key, value, sep=':', orig)])` | `argparse` + `KeyValueArgType.__call__/tokenize` (cli/argtypes.py) |
| Request-item classification | `List[KeyValueArg]`                                          | `RequestItems{headers: HTTPHeadersDict, data: RequestJSONDataDict({}), params, files, multipart_data}` | `RequestItems.from_args` (cli/requestitems.py), cli/dicts.py |
| Namespace normalization     | Raw `Namespace` + `Environment` TTY state                    | Mutated `Namespace`: `output_options='hb'`, `prettify=['format','colors']`, `format_options` dict, `auth=None`, `cert_key_pass=SSLCredentials(None)` | `HTTPieArgumentParser._process_*` (cli/argparser.py)         |
| Processing options          | `Namespace`                                                  | `ProcessingOptions` NamedTuple (`stream`, `style`, `prettify`, `format_options`, ...) | output/models.py                                             |
| Request kwargs              | `Namespace`, `Environment`                                   | `dict{method:'get', url, headers: HTTPHeadersDict(bytes values), data:{}, auth:None, params: iterator}` | `client.make_request_kwargs`, `make_default_headers`, `finalize_headers`, `uploads.prepare_request_body` |
| Send kwargs                 | `Namespace`                                                  | `{timeout:None, allow_redirects:False}` and `{proxies:{}, stream:True, verify:True, cert:None}` | `client.make_send_kwargs*`                                   |
| Transport assembly          | `verify, ssl_version, ciphers`                               | `requests.Session` with mounted `HTTPieHTTPAdapter`, `HTTPieHTTPSAdapter(ssl_context)` | `client.build_requests_session`, `ssl_.py`                   |
| Request preparation         | `requests.Request(**kwargs)`                                 | `requests.PreparedRequest` (headers re-merged with repeated headers) | `Session.prepare_request`, `client.transform_headers`        |
| Message emission            | `PreparedRequest`                                            | `Iterable[RequestsMessage]` item (generator `yield`)         | `client.collect_messages`                                    |
| Output gating               | `RequestsMessage`, `'hb'`                                    | `OutputOptions(kind, headers, body, meta)`                   | `models.OutputOptions.from_message`                          |
| Dispatch                    | `PreparedRequest`, `send_kwargs_merged`                      | `requests.Response` (`stream=True`, body unread, `_httpie_headers_parsed_at`) | `Session.send`, `HTTPieHTTPSAdapter`, urllib3                |
| Stream selection            | `Response`, `OutputOptions`, `ProcessingOptions`, `Environment` | `(BufferedPrettyStream, kwargs{conversion, formatting})`     | `writer.get_stream_type_and_kwargs`, output/processing.py    |
| Header rendering            | `HTTPResponse.headers: str` (CRLF status line + headers)     | `bytes` (sorted, ANSI-highlighted, `output_encoding`)        | `HTTPResponse` (`models.py`), `HeadersFormatter`, `ColorFormatter.format_headers` |
| Body rendering              | `iter_content(10240): Iterator[bytes]` → `bytearray`         | `str` → pretty JSON `str` → ANSI `str` → `bytes`             | `BufferedPrettyStream.iter_body/process_body`, `JSONFormatter`, `ColorFormatter.format_body/get_lexer` |
| Terminal write              | `Iterator[bytes]`                                            | Bytes on `env.stdout.buffer`, colored chunks as text via colorama on Windows | `writer.write_stream_with_colors_win` (`write_stream` on POSIX) |
| Exit                        | `ExitStatus`                                                 | Process exit code (`int`)                                    | `core.program`, `__main__.main`                              |



### 3. PlantUML Sequence Diagram

```
@startumltitle HTTPie: http GET https://httpbin.org/get Authorization:Bearer_tokenautonumberskinparam shadowing falseskinparam sequenceMessageAlign leftskinparam responseMessageBelowArrow true
actor "User" as User
box "CLI Ingestion & Context" #EEF3FF  boundary "CLI\n__main__.py, cli/argparser.py" as CLI  control "Core Dispatcher\ncore.py, context.py" as Coreend box
box "HTTP Client & Transport" #EEFAF0  participant "Transport / Client\nclient.py, ssl_.py, adapters.py" as Transportend box
entity "Remote Server\nhttpbin.org:443" as Server
box "Output & Stream Rendering" #FFF7E6  boundary "Terminal Output\noutput/writer.py, streams.py, formatters/" as Termend box
== Phase 1: Ingestion ==User -> CLI : $ http GET https://httpbin.org/get Authorization:Bearer_tokenactivate CLICLI -> Core : main(args: List[str]=sys.argv, env: Environment=Environment())activate CoreCore -> Core : raw_main(parser, main_program=program, args, env)Core -> Core : decode_raw_args(args, env.stdin_encoding) : List[str]Core -> Core : plugin_manager.load_installed_plugins(env.config.plugins_dir)Core -> CLI : parse_args(env: Environment, args: List[str]) : Namespaceactivate CLICLI -> CLI : parse_known_args(args) with KeyValueArgType.__call__(s: str) : KeyValueArgnote right of CLI  "Authorization:Bearer_token" becomes  KeyValueArg(key='Authorization', value='Bearer_token', sep=':')  method='GET', url='https://httpbin.org/get'end noteCLI -> CLI : _process_request_type(), _setup_standard_streams()CLI -> CLI : _process_output_options() : output_options='hb' (TTY)CLI -> CLI : _process_pretty_options() : prettify=['format','colors']CLI -> CLI : _guess_method() : method stays 'GET'CLI -> CLI : _parse_items() calls RequestItems.from_args(List[KeyValueArg], request_type) : RequestItemsCLI -> CLI : process_header_arg(arg) : str, then HTTPHeadersDict.add('Authorization','Bearer_token')CLI -> CLI : _process_url(), _process_auth() (no-op, auth=None), _process_ssl_cert()CLI --> Core : argparse.Namespace (method, url, headers, data, params, auth, verify, output_options, prettify)deactivate CLICore -> Core : check_updates(env: Environment) : NoneCore -> Core : program(args: Namespace, env: Environment) : ExitStatusCore -> Core : ProcessingOptions.from_raw_args(args) : ProcessingOptions
== Phase 2: Transport Assembly & Dispatch ==Core -> Transport : collect_messages(env, args, request_body_read_callback) : Iterable[RequestsMessage]note right of Transport : Generator: the body runs only on next(messages)Core -> Transport : next(messages)activate TransportTransport -> Transport : make_request_kwargs(env, args, base_headers, cb) : dictnote right of Transport  make_default_headers() adds User-Agent  finalize_headers() encodes values to bytes  prepare_request_body(env, {}, ...) passes the empty dict through  kwargs = {method:'get', url, headers, data:{}, auth:None, params}end noteTransport -> Transport : make_send_kwargs(args) and make_send_kwargs_mergeable_from_env(args) : dictTransport -> Transport : build_requests_session(verify=True, ssl_version=None, ciphers=None) : requests.SessionTransport -> Transport : HTTPieHTTPSAdapter._create_ssl_context(verify, ssl_version, ciphers) : SSLContextTransport -> Transport : Session.mount('http://', HTTPieHTTPAdapter) and mount('https://', HTTPieHTTPSAdapter)Transport -> Transport : Session.prepare_request(requests.Request(**kwargs)) : PreparedRequestTransport -> Transport : transform_headers(request, prepared_request) : NoneTransport -->> Core : yield PreparedRequestdeactivate Transport
Core -> Core : OutputOptions.from_message(PreparedRequest, 'hb') : OutputOptions(REQUEST, headers=False, body=False)Core -> Term : write_message(requests_message, env, output_options, processing_options)activate TermTerm --> Core : None (returns early: output_options.any() is False)deactivate Term
Core -> Transport : next(messages)activate TransportTransport -> Transport : Session.merge_environment_settings(url, proxies, stream, verify, cert) : dictTransport -> Transport : max_headers(limit=0) context managerTransport -> Transport : Session.send(request, stream=True, verify=True, cert=None, timeout=None, allow_redirects=False)Transport -> Transport : get_adapter(url) then HTTPieHTTPSAdapter.cert_verify(conn, url, verify, cert)Transport -> Server : TLS handshake (CERT_REQUIRED), then GET /get HTTP/1.1 with Authorization: Bearer_tokenactivate ServerServer --> Transport : HTTP/1.1 200 OK, headers, application/json (body unread: stream=True)deactivate ServerTransport -> Transport : HTTPAdapter.build_response(req, resp) : requests.ResponseTransport -> Transport : response._httpie_headers_parsed_at = monotonic()Transport -->> Core : yield requests.Responsedeactivate Transport
== Phase 3: Egress & Rendering ==Core -> Core : OutputOptions.from_message(Response, 'hb') : OutputOptions(RESPONSE, headers=True, body=True)Core -> Term : write_message(requests_message=Response, env, output_options, processing_options)activate TermTerm -> Term : build_output_stream_for_message(env, msg, output_options, processing_options)Term -> Term : get_stream_type_and_kwargs(env, processing_options, HTTPResponse, headers) : (BufferedPrettyStream, kwargs)Term -> Term : Formatting(groups=['format','colors'], env, color_scheme, format_options) : Formattingnote right of Term : Enabled plugins: HeadersFormatter, JSONFormatter, XMLFormatter, ColorFormatteralt env.is_windows and 'colors' in prettify (this host)  Term -> Term : write_stream_with_colors_win(stream: Iterator[bytes], outfile=env.stdout, flush=True)else POSIX or no colors  Term -> Term : write_stream(stream: Iterator[bytes], outfile, flush)endTerm -->> Term : yield bytes (BaseStream.__iter__: PrettyStream.get_headers() : bytes)note right of Term  HTTPResponse.headers : str  HeadersFormatter.format_headers() sorts the lines  ColorFormatter.format_headers() applies the Pygments HttpLexerend noteTerm -->> Term : yield b"\r\n\r\n"Term -> Server : BufferedPrettyStream.iter_body() calls response.iter_content(chunk_size=10240)activate ServerServer --> Term : body bytes (JSON)deactivate ServerTerm -> Term : process_body(body: bytearray) : bytesnote right of Term  smart_decode(bytes) : str  JSONFormatter.format_body(content, 'application/json') : indent=4, sort_keys  ColorFormatter.format_body(): EnhancedJsonLexer + TerminalFormatter  smart_encode(str, output_encoding) : bytesend noteTerm -->> Term : yield bytes (pretty JSON body)Term -->> Term : yield MESSAGE_SEPARATOR_BYTES (TTY only)Term --> User : colorized headers + pretty JSON on stdout (colorama wraps ANSI on Windows)Term --> Core : Nonedeactivate Term
Core -> Transport : next(messages)activate TransportTransport --> Core : StopIteration (no session, no redirect)deactivate TransportCore --> CLI : ExitStatus.SUCCESSdeactivate CoreCLI --> User : sys.exit(exit_status.value) = 0deactivate CLI@enduml
```