## HTTPie call flow: CLI entry → Environment/Config → domain models

Everything below was read from the source on branch `group-B`. Line numbers are noted as `file:line`.

```
★ Insight ─────────────────────────────────────
```

- There are two phases. **Import time** builds the singletons: `Environment` class attributes, `DEFAULT_CONFIG_DIR`, `plugin_manager` and `parser`. **Call time** turns them into per-request objects. Most "initialization" happens when modules are imported, not when functions are called.
- `env: Environment = Environment()` in `core.main`/`raw_main` is a **default argument**. It is evaluated once, when `core.py` is imported. Tests get isolation by passing their own `Environment(**overrides)`, not by relying on a fresh default.
- `Environment.config` is a **lazy property**. `config.json` is only read the first time something touches `env.config`, which in practice is `raw_main` line 46.
  `─────────────────────────────────────────────────`

### 0. Packaging entry points

setup.cfg:75-79

```
console_scripts:
  http   → httpie.__main__:main
  https  → httpie.__main__:main      (same code path; branch is on env.program_name later)
  httpie → httpie.manager.__main__:main   (plugin/session manager, separate tree, not traced)
```

### 1. Full call tree

```
httpie/__main__.py :: main()                                        [__main__.py:6]
│   `from httpie.core import main` ── triggers IMPORT-TIME PHASE (§2) ──┐
│   exit_status = httpie.core.main()                                    │
│   except KeyboardInterrupt → httpie.status.ExitStatus.ERROR_CTRL_C    │
│   return exit_status.value  → sys.exit()                              │
│                                                                       │
└─► httpie/core.py :: main(args=sys.argv, env=Environment())         [core.py:146]
    │   from .cli.definition import parser    (lazy import → §2.4)
    │
    └─► httpie/core.py :: raw_main(parser, main_program=program, args, env)   [core.py:32]
        │
        ├─ env.program_name = os.path.basename(argv[0])        ('http' | 'https')
        ├─ decode_raw_args(args, env.stdin_encoding)           [core.py:285]
        │     bytes → str using Environment.stdin_encoding
        │
        ├─ httpie/internal/daemon_runner.py :: is_daemon_mode(args)     [daemon_runner.py:37]
        │     └─ if '--daemon' → run_daemon_task(env, args) → RETURN   [daemon_runner.py:41]
        │
        ├─ env.config  ═══► ENVIRONMENT CONFIGURATION (§3)
        │     httpie/context.py :: Environment.config (property)       [context.py:140]
        │       └─ httpie/config.py :: Config.__init__(directory=env.config_dir) [config.py:143]
        │            ├─ BaseConfigDict.__init__(path=<dir>/config.json)          [config.py:85]
        │            ├─ self.update(Config.DEFAULTS)  → {'default_options': []}
        │            └─ if not is_new(): BaseConfigDict.load()                    [config.py:103]
        │                  └─ read_raw_config('config', path) → json.load        [config.py:65]
        │                     (ConfigFileError → env.log_error(level=WARNING))
        │
        ├─ httpie/plugins/manager.py :: PluginManager.load_installed_plugins(  [manager.py:66]
        │        env.config.plugins_dir)                ← Config.plugins_dir → _configured_path()
        │     └─ iter_entry_points(directory)                                    [manager.py:59]
        │          └─ enable_plugins(dir) → _load_directories() (temp sys.path)  [manager.py:41/28]
        │          └─ importlib_metadata.entry_points() for groups:
        │               httpie.plugins.{auth,converter,formatter,transport}.v1
        │          └─ entry_point.load() → plugin.package_name = … → self.register(plugin)
        │
        ├─ if env.config.default_options: args = default_options + args
        ├─ if '--debug': print_debug_info(env)                               [core.py:270]
        │     (repr(env) → Environment.__str__ → includes env.config)
        │
        ├─► httpie/cli/argparser.py :: HTTPieArgumentParser.parse_args(args, env)  [argparser.py:151]
        │   │   self.env = env
        │   │   env.args = argparse.Namespace()        ← Environment now holds parsed args
        │   │   argparse.ArgumentParser.parse_known_args()
        │   │   has_stdin_data = env.stdin and not ignore_stdin and not env.stdin_isatty
        │   │
        │   ├─ _apply_no_options(no_options)                   [argparser.py:357]
        │   ├─ _process_request_type()  → args.json/form/multipart   [argparser.py:196]
        │   ├─ _process_download_options()
        │   ├─ _setup_standard_streams()   ═══ MUTATES Environment ═══   [argparser.py:227]
        │   │     env.stdout ← output_file | stderr (download) | devnull (--quiet)
        │   │     env.stdout_isatty, env.stderr ← devnull, env.quiet = args.quiet
        │   │     └─ Environment.apply_warnings_filter()                    [context.py:184]
        │   ├─ _process_output_options()  → args.output_options (uses env.stdout_isatty) [:492]
        │   ├─ _process_pretty_options()  → args.prettify                   [argparser.py:531]
        │   ├─ _process_format_options()
        │   ├─ _guess_method()            → args.method (GET/POST inference)  [argparser.py:409]
        │   ├─ _parse_items()                                               [argparser.py:448]
        │   │     └─► httpie/cli/requestitems.py :: RequestItems.from_args() [requestitems.py:37]
        │   │           └─ RequestItems.__init__(request_type)              [requestitems.py:26]
        │   │                ├─ headers        = HTTPHeadersDict()          [cli/dicts.py:12]
        │   │                ├─ data           = RequestJSONDataDict | RequestDataDict [dicts.py:49/85]
        │   │                ├─ files          = RequestFilesDict()         [dicts.py:93]
        │   │                ├─ params         = RequestQueryParamsDict()   [dicts.py:81]
        │   │                └─ multipart_data = MultipartRequestDataDict() [dicts.py:89]
        │   │          → args.headers / data / files / params / multipart_data
        │   ├─ _process_url()   (scheme default via env.program_name == 'https') [argparser.py:205]
        │   ├─ _process_auth()  → plugin_manager.get_auth_plugin(...) → args.auth, args.auth_plugin [:282]
        │   ├─ _process_ssl_cert()                                          [argparser.py:269]
        │   └─ _body_from_input(raw) | _body_from_file(env.stdin)           [argparser.py:391/382]
        │   return args (argparse.Namespace)
        │
        ├─ httpie/internal/update_warnings.py :: check_updates(env)      [update_warnings.py:141]
        │     (reads env.config['disable_update_warnings'], version_info_file)
        │
        └─► httpie/core.py :: program(args, env)                           [core.py:170]
            │
            ├─ httpie/output/models.py :: ProcessingOptions.from_raw_args(args)  [output/models.py:35]
            ├─ [--download] httpie/downloads.py :: Downloader(env, …).pre_request(args.headers)
            │
            ├─► httpie/client.py :: collect_messages(env, args, request_body_read_callback)  [client.py:43]
            │   │   (generator: yields PreparedRequest / Response)
            │   │
            │   ├─ [--session] httpie/sessions.py :: get_httpie_session(env, env.config.directory, …) [sessions.py:92]
            │   │     └─ Session.__init__(path, env, bound_host, session_id)   [sessions.py:128]
            │   │          ├─ BaseConfigDict.__init__(path)   (same base as Config)
            │   │          ├─ defaults: headers=[], cookies=[], auth={type,username,password}
            │   │          ├─ self._headers   = HTTPHeadersDict()
            │   │          └─ self.cookie_jar = RequestsCookieJar(policy=HTTPieCookiePolicy())
            │   │     └─ Session.load() → pre_process_data()                 [sessions.py:170]
            │   │
            │   ├─ make_request_kwargs(env, args, base_headers)              [client.py:325]
            │   │     ├─ json_dict_to_request_body(data)
            │   │     ├─ make_default_headers(args) → HTTPHeadersDict        [client.py:263]
            │   │     ├─ finalize_headers(headers)                           [client.py:192]
            │   │     ├─ httpie/uploads.py :: get_multipart_data_and_content_type()
            │   │     └─ httpie/uploads.py :: prepare_request_body(env, data, …)
            │   ├─ make_send_kwargs(args)                                    [client.py:281]
            │   ├─ make_send_kwargs_mergeable_from_env(args)                 [client.py:288]
            │   ├─ build_requests_session(verify, ssl_version, ciphers)      [client.py:156]
            │   │     ├─ requests.Session()
            │   │     ├─ mount('http://',  httpie/adapters.py :: HTTPieHTTPAdapter())
            │   │     ├─ mount('https://', httpie/ssl_.py :: HTTPieHTTPSAdapter(...))
            │   │     └─ for plugin_cls in plugin_manager.get_transport_plugins(): mount(...)
            │   ├─ [session] Session.update_headers(); requests_session.cookies = session.cookies
            │   ├─ requests.Request(**request_kwargs)
            │   ├─ requests_session.prepare_request(request) → PreparedRequest
            │   ├─ transform_headers(request, prepared_request)              [client.py:212]
            │   ├─ [--path-as-is] ensure_path_as_is(); [--compress] uploads.compress_request()
            │   ├─ LOOP: yield prepared_request
            │   │        └─ requests_session.send(...) within max_headers()  [client.py:145]
            │   │        └─ response._httpie_headers_parsed_at = monotonic()
            │   │        └─ follow redirects (args.follow / args.all / max_redirects)
            │   │        yield response
            │   └─ [session] Session.save()  → BaseConfigDict.save()          [config.py:110]
            │
            └─ for message in messages:            ═══ CORE DOMAIN MODELS ═══
                 ├─ httpie/models.py :: OutputOptions.from_message(message, args.output_options) [models.py:216]
                 │     └─ infer_requests_message_kind(message) → RequestsMessageKind.{REQUEST,RESPONSE} [models.py:180]
                 │     └─ OPTION_TO_PARAM[kind] → headers/body/meta flags   [models.py:189]
                 ├─ [response] status.http_status_to_exit_status()
                 └─ httpie/output/writer.py :: write_message(requests_message, env, output_options, processing_options)
                       └─ wraps raw message in:
                            httpie/models.py :: HTTPRequest(HTTPMessage)  [models.py:130]  ← PreparedRequest
                            httpie/models.py :: HTTPResponse(HTTPMessage) [models.py:61]   ← Response
                            (HTTPMessage.__init__(orig) → self._orig        [models.py:26])
               [--download] Downloader.start() → write_stream() → Downloader.finish()
```

### 2. Import-time phase (runs before `core.main` executes)

Triggered by `from httpie.core import main` in `__main__.py`, in roughly this order:

| #    | Module                                                 | What gets initialized                                        |
| ---- | ------------------------------------------------------ | ------------------------------------------------------------ |
| 2.1  | httpie/config.py:58                                    | `DEFAULT_CONFIG_DIR = get_default_config_dir()`. Resolution order: `$HTTPIE_CONFIG_DIR`, then `%APPDATA%\httpie` (Windows), then legacy `~/.httpie`, then `$XDG_CONFIG_HOME/httpie` or `~/.config/httpie` |
| 2.2  | httpie/context.py:46                                   | `class Environment` **body** runs: binds `sys.stdin/stdout/stderr`, `*_isatty`. `curses.setupterm()` sets `colors` (POSIX); Windows wraps stdout/stderr with `colorama.initialise.wrap_stream` |
| 2.3  | httpie/plugins/registry.py:9                           | `plugin_manager = PluginManager()` (a `list` subclass). Registers the built-ins `BasicAuthPlugin`, `DigestAuthPlugin`, `BearerAuthPlugin`, `HeadersFormatter`, `JSONFormatter`, `XMLFormatter`, `ColorFormatter` |
| 2.4  | httpie/core.py:148                                     | Default arg `env = Environment()` → `Environment.__init__` (context.py:93): applies kwargs, saves `_orig_stderr`, resolves `stdin_encoding`/`stdout_encoding` (unwrapping `AnsiToWin32` on Windows), sets `quiet=0` |
| 2.5  | httpie/cli/definition.py:32 (lazy, inside `core.main`) | `options = ParserSpec(...)` declares every CLI group and argument. Then `options.finalize()` and `parser = to_argparse(options)` (cli/options.py:193), which builds an `HTTPieArgumentParser` and registers the `LazyChoices`/`Manual` actions |

### 3. Environment and configuration object graph

```
Environment                       (httpie/context.py)
├── class attrs: stdin/stdout/stderr, *_isatty, colors, program_name, config_dir=DEFAULT_CONFIG_DIR
├── instance:    stdin_encoding, stdout_encoding, quiet, _orig_stderr, _devnull
├── args         ← set by HTTPieArgumentParser.parse_args (argparse.Namespace)
├── config  ──►  Config(BaseConfigDict(dict))          (httpie/config.py)
│                ├── path = <config_dir>/config.json
│                ├── default_options  (prepended to argv in raw_main)
│                ├── plugins_dir      (→ PluginManager.load_installed_plugins)
│                ├── version_info_file(→ check_updates)
│                └── developer_mode
├── devnull, as_silent()
├── log_error() → _make_rich_console() → rich.Console + rich_palette theme
└── rich_console / rich_error_console (cached_property)

BaseConfigDict(dict) ─┬─ Config          (global config.json)
                      └─ Session         (per-host session JSON, httpie/sessions.py)
```

### 4. Domain model layer (httpie/models.py)

| Class / function            | Role                                                         | Created by                                       |
| --------------------------- | ------------------------------------------------------------ | ------------------------------------------------ |
| `HTTPMessage` (abstract)    | Wraps `_orig`; provides `content_type` and `encoding`        | —                                                |
| `HTTPRequest(HTTPMessage)`  | Builds the request line, `Host` header and body bytes from `requests.PreparedRequest` | output writer                                    |
| `HTTPResponse(HTTPMessage)` | Status line, `Set-Cookie` splitting, `version` mapping, `metadata` (elapsed time via `_httpie_headers_parsed_at`) | output writer                                    |
| `RequestsMessage`           | `Union[PreparedRequest, Response]`, the type yielded by `collect_messages` | `client.py`                                      |
| `RequestsMessageKind`       | Enum `REQUEST` / `RESPONSE`                                  | `infer_requests_message_kind()`                  |
| `OutputOptions(NamedTuple)` | Per-message `headers`/`body`/`meta` flags                    | `OutputOptions.from_message()` in `core.program` |

Supporting models built during parsing: `RequestItems` plus the cli/dicts.py multi-dicts (`HTTPHeadersDict`, `RequestJSONDataDict`, …), and `ProcessingOptions` (httpie/output/models.py:10).

```
★ Insight ─────────────────────────────────────
```

- `Environment` is shared mutable state. `HTTPieArgumentParser._setup_standard_streams()` reassigns `env.stdout`/`env.stderr` (to the output file, stderr or devnull), so all later output silently follows those redirects. That is why `log_error` keeps `_orig_stderr` around.
- `Config` and `Session` share `BaseConfigDict`, a `dict` with `load()`/`save()` and pre/post-process hooks. Global config and per-host sessions use the same JSON persistence path.
- `collect_messages` is a **generator**. `program()` renders each request before it is sent, which is what makes `--offline` and `--all` (intermediate redirects) work without a separate code path.
  `─────────────────────────────────────────────────`