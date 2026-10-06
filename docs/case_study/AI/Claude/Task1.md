# HTTPie Call Flow: CLI Entry Point → Environment/Config → Domain Models

Repo root: `SOEN-6431-Group-Project/` · Package: `httpie/` (v3.2.4)

## 0. Entry-point registration (`setup.cfg` → `[options.entry_points]`)

```
console_scripts
├── http    = httpie.__main__:main
├── https   = httpie.__main__:main            (same fn; scheme chosen by env.program_name == 'https')
└── httpie  = httpie.manager.__main__:main    (plugin/session manager; see §6)
```

## 1. Import-time initialization (runs BEFORE `main()` body)

```
httpie/core.py  (imported by httpie/__main__.py:main)
├── from .context import Environment                      [httpie/context.py]
│   ├── from .config import DEFAULT_CONFIG_DIR, Config, ConfigFileError   [httpie/config.py]
│   │   └── DEFAULT_CONFIG_DIR = get_default_config_dir()
│   │         1. $HTTPIE_CONFIG_DIR            (ENV_HTTPIE_CONFIG_DIR)
│   │         2. Windows → %APPDATA%/httpie    (DEFAULT_WINDOWS_CONFIG_DIR)
│   │         3. legacy ~/.httpie if it exists
│   │         4. $XDG_CONFIG_HOME/httpie or ~/.config/httpie
│   └── class Environment — CLASS BODY executes at import:
│         ├── stdin/stdout/stderr = sys.*; *_isatty computed
│         ├── non-Windows: curses.setupterm() → colors = curses.tigetnum('colors')
│         └── Windows: colorama.initialise.wrap_stream(stdout/stderr)
├── from .plugins.registry import plugin_manager          [httpie/plugins/registry.py]
│   ├── plugin_manager = PluginManager()                  [httpie/plugins/manager.py]  (a `list` subclass)
│   └── plugin_manager.register(
│         BasicAuthPlugin, DigestAuthPlugin, BearerAuthPlugin,          # httpie/plugins/builtin.py
│         HeadersFormatter, JSONFormatter, XMLFormatter, ColorFormatter # httpie/output/formatters/*.py
│       )
└── main(..., env: Environment = Environment())           ← default arg evaluated ONCE at def time
      └── Environment.__init__(devnull=None, **kwargs)    [httpie/context.py]
            ├── self._orig_stderr = self.stderr
            ├── self.stdin_encoding  ← stdin.encoding or UTF8
            ├── self.stdout_encoding ← stdout.encoding (unwrap colorama on Windows) or UTF8
            └── self.quiet = 0
```

## 2. Main call flow (`http` / `https`)

```
httpie.__main__:main()                                           [httpie/__main__.py]
├── from httpie.core import main
├── httpie.core.main(args=sys.argv, env=Environment())           [httpie/core.py]
│   ├── from .cli.definition import parser                       ← triggers §3 (parser build)
│   └── raw_main(parser, main_program=program, args, env)        [httpie/core.py]
│       ├── env.program_name = os.path.basename(argv[0])
│       ├── decode_raw_args(args, env.stdin_encoding)            # bytes → str
│       ├── is_daemon_mode(args)  ──yes──► run_daemon_task(env, args)   → §5
│       ├── plugin_manager.load_installed_plugins(env.config.plugins_dir)
│       │   ├── env.config  (property)  ──► §4 Config load
│       │   └── PluginManager.load_installed_plugins(directory)  [httpie/plugins/manager.py]
│       │       ├── iter_entry_points(directory)
│       │       │   ├── enable_plugins(directory) → _load_directories(get_site_paths(dir))
│       │       │   ├── importlib_metadata.entry_points()
│       │       │   └── find_entry_points(eps, group=...) for ENTRY_POINT_NAMES:
│       │       │         httpie.plugins.{auth,converter,formatter,transport}.v1
│       │       ├── entry_point.load()   (errors → warnings.warn, continue)
│       │       └── self.register(plugin)
│       ├── if use_default_options: args = env.config.default_options + args
│       ├── if '--debug' in args: print_debug_info(env)
│       ├── parser.parse_args(args=args, env=env)                → §3b
│       │     (except NestedJSONSyntaxError / KeyboardInterrupt / SystemExit → ExitStatus)
│       ├── check_updates(env)                                   [httpie/internal/update_warnings.py]
│       │   └── @_update_checker wrapper(env)
│       │       ├── check_updates body → env.config.version_info_file, _get_update_status(env)
│       │       └── maybe_fetch_updates(env) → fetch_updates(env)
│       │           └── spawn_daemon('fetch_updates')            [httpie/internal/daemons.py]
│       └── main_program(args=parsed_args, env=env)  == program()
│           │       (except requests.Timeout / TooManyRedirects / ConnectionError / Exception
│           │        → env.log_error(...) → ExitStatus.*)
│           └── program(args, env)                               [httpie/core.py]  → §7
└── return exit_status.value        (KeyboardInterrupt → ExitStatus.ERROR_CTRL_C)
```

## 3. Argument parser construction and parsing

### 3a. Build (import time of `httpie/cli/definition.py`)

```
httpie/cli/definition.py
├── options = ParserSpec('http', description=..., epilog=..., source_file=__file__)   [httpie/cli/options.py]
│   ├── options.add_group('Positional arguments' / 'Predefined content types' / ...)
│   └── group.add_argument(dest='method'|'url'|'--auth'|'--auth-type'|'--style'|...)
│       ├── Auth help   ← format_auth_help(plugin_manager.get_auth_plugin_mapping())
│       └── Style help  ← format_style_help(get_available_styles())
└── parser = to_argparse(options)                                [httpie/cli/options.py]
    ├── parser_type = HTTPieArgumentParser (default)             [httpie/cli/argparser.py]
    ├── concrete_parser.register('action', 'lazy_choices', LazyChoices)
    ├── concrete_parser.register('action', 'manual', Manual)
    └── add_argument_group(...).add_argument(*aliases, **map_qualifiers(...))
```

### 3b. Parse (`HTTPieArgumentParser.parse_args`, `httpie/cli/argparser.py:151`)

```
HTTPieArgumentParser.parse_args(env, args, namespace)
├── self.env = env;  self.env.args = namespace = argparse.Namespace()
├── argparse.ArgumentParser.parse_known_args(args, namespace)
├── has_stdin_data / has_input_data
├── _apply_no_options(no_options)
├── _process_request_type()        # → args.json / multipart / form
├── _process_download_options()
├── _setup_standard_streams()      # mutates env.stdout / env.stdout_isatty / env.quiet / env.stderr
│       └── env.apply_warnings_filter()
├── _process_output_options()
├── _process_pretty_options()
├── _process_format_options()
├── _guess_method()
├── _parse_items()                 # → httpie/cli/requestitems.py (RequestItems), httpie/cli/nested_json/*
├── _process_url()                 # default scheme / `https` program_name / `:3000` shorthand
├── _process_auth()                # plugin_manager.get_auth_plugins() / get_auth_plugin(...)
├── _process_ssl_cert()            # httpie.ssl_._is_key_file_encrypted, SSLCredentials.prompt_password
└── _body_from_input(args.raw) | _body_from_file(env.stdin)
```

## 4. Environment → Config initialization (lazy)

```
Environment.config  (property)                                   [httpie/context.py:139]
└── on first access:
    ├── self._config = Config(directory=self.config_dir)         [httpie/config.py]
    │   ├── Config.__init__ → BaseConfigDict.__init__(path=directory / 'config.json')
    │   └── self.update(Config.DEFAULTS)   # {'default_options': []}
    ├── if not config.is_new():
    │   └── config.load()                  # BaseConfigDict.load
    │       ├── read_raw_config('config', path)   # json.load; raises ConfigFileError
    │       ├── pre_process_data(data)
    │       └── self.update(data)
    └── except ConfigFileError → env.log_error(e, level=LogLevel.WARNING)

Config derived properties (consumed by core.py / update_warnings.py)
├── default_options   → self['default_options']
├── plugins_dir       → _configured_path('plugins_dir', 'plugins')
├── version_info_file → _configured_path('version_info_file', 'version_info.json')
└── developer_mode    → self.get('developer_mode')

Environment error/log helpers
├── log_error(msg, level: LogLevel)  → _make_rich_console(file, force_terminal) → rich Console + _make_rich_color_theme(style)
├── as_silent()                      → context manager swapping stdout/stderr with env.devnull
├── rich_console / rich_error_console (cached_property)
└── devnull (lazy open(os.devnull))
```

## 5. Daemon path (`--daemon`)

```
raw_main → is_daemon_mode(args) → run_daemon_task(env, args)     [httpie/internal/daemon_runner.py]
├── _parse_options(args)             # task_id, --daemon
├── redirect_stdout/stderr → env.devnull
├── _get_suppress_context(env)       # suppress(BaseException) unless env.config.developer_mode
└── DAEMONIZED_TASKS[task_id](env)
    ├── 'fetch_updates' → _fetch_updates(env)     [httpie/internal/update_warnings.py]
    │       └── requests.get(PACKAGE_INDEX_LINK) → writes env.config.version_info_file (open_with_lockfile)
    └── 'check_status'  → _check_status(env)      # test-only
```

## 6. `httpie` manager command (plugins / sessions / cli)

```
httpie.manager.__main__:main(args, env)                          [httpie/manager/__main__.py]
├── from httpie.core import raw_main
├── raw_main(parser=httpie.manager.cli.parser,                   # HTTPieManagerArgumentParser
│            main_program=httpie.manager.core.program,
│            args, env, use_default_options=False)
│   └── httpie.manager.core.program(args, env)                   [httpie/manager/core.py]
│       ├── args.action is None → parser.error(MSG_NAKED_INVOCATION)
│       ├── 'plugins' → dispatch_cli_task(env, 'plugins', args)
│       └── 'cli'     → dispatch_cli_task(env, args.cli_action, args)
│           └── CLI_TASKS[action](env, args)                     [httpie/manager/tasks/__init__.py]
│               ├── 'plugins'      → cli_plugins      (tasks/plugins.py → PluginInstaller.run → install/upgrade/uninstall/list)
│               ├── 'sessions'     → cli_sessions     (tasks/sessions.py → cli_upgrade_session / cli_upgrade_all_sessions)
│               ├── 'export-args'  → cli_export_args  (tasks/export_args.py)
│               └── 'check-updates'→ cli_check_updates(tasks/check_updates.py)
└── except argparse.ArgumentError → is_http_command(...) → prints MSG_COMMAND_CONFUSION; ExitStatus.ERROR
```

## 7. Core domain model initialization (`httpie.core.program`)

```
program(args: Namespace, env: Environment)                       [httpie/core.py:170]
├── processing_options = ProcessingOptions.from_raw_args(args)   [httpie/output/models.py]
│     └── NamedTuple: debug, traceback, stream, style, prettify, response_mime,
│                     response_charset, json, format_options
│         └── get_prettify(env) / show_traceback
├── (--download) Downloader(env, output_file, resume).pre_request(args.headers)   [httpie/downloads.py]
├── messages = collect_messages(env, args, request_body_read_callback)            [httpie/client.py:43]
│   ├── (--session) get_httpie_session(env, env.config.directory, name, host, url) [httpie/sessions.py]
│   │   ├── Session(path, env, session_id, bound_host)           # subclass of BaseConfigDict
│   │   │     └── headers: HTTPHeadersDict · cookie_jar: RequestsCookieJar(policy=HTTPieCookiePolicy())
│   │   └── session.load() → pre_process_data(legacy_cookies/legacy_headers)
│   ├── make_request_kwargs(env, args, base_headers, callback)
│   │   ├── make_default_headers(args)         → HTTPHeadersDict  [httpie/cli/dicts.py]
│   │   ├── finalize_headers(headers)
│   │   ├── get_multipart_data_and_content_type(...)   [httpie/uploads.py]
│   │   └── prepare_request_body(env, data, ...)       [httpie/uploads.py]
│   ├── make_send_kwargs(args) · make_send_kwargs_mergeable_from_env(args)  (→ HTTPieCertificate)
│   ├── build_requests_session(verify, ssl_version, ciphers)
│   │   ├── requests.Session()
│   │   ├── mount('http://',  HTTPieHTTPAdapter())          [httpie/adapters.py]
│   │   ├── mount('https://', HTTPieHTTPSAdapter(...))      [httpie/ssl_.py]
│   │   └── plugin_manager.get_transport_plugins() → mount(prefix, plugin().get_adapter())
│   ├── requests.Request(**kwargs) → requests_session.prepare_request() → transform_headers()
│   └── loop: yield PreparedRequest → requests_session.send() (max_headers) → yield Response
│             (follow redirects via response.next; save session at the end)
└── for message in messages:                                     # RequestsMessage = PreparedRequest | Response
    ├── OutputOptions.from_message(message, args.output_options) [httpie/models.py]
    │     ├── infer_requests_message_kind(message) → RequestsMessageKind.{REQUEST,RESPONSE}
    │     └── NamedTuple(kind, headers, body, meta); .any()
    ├── http_status_to_exit_status(...)                          [httpie/status.py]  (ExitStatus enum)
    └── write_message(requests_message, env, output_options, processing_options)  [httpie/output/writer.py]
        ├── build_output_stream_for_message(...)
        │   ├── message_type = HTTPRequest | HTTPResponse        [httpie/models.py] (extend HTTPMessage)
        │   ├── get_stream_type_and_kwargs(env, processing_options, message_type, headers)
        │   │     → RawStream | EncodedStream | PrettyStream | BufferedPrettyStream   [httpie/output/streams.py]
        │   │       + Conversion() / Formatting(env, groups, color_scheme, ...)       [httpie/output/processing.py]
        │   │           └── Formatting uses plugin_manager.get_formatters_grouped()
        │   └── yield from stream_class(msg=message_type(requests_message), output_options, **kwargs)
        └── write_stream(stream, outfile=env.stdout, flush)  (or write_stream_with_colors_win on Windows)
    finally: downloader.start/finish/failed; args.output_file.close()
```

## Key class / object map

| Layer | File | Symbol |
|---|---|---|
| Entry | `httpie/__main__.py` | `main()` |
| Orchestrator | `httpie/core.py` | `main()`, `raw_main()`, `program()`, `decode_raw_args()`, `print_debug_info()` |
| Environment | `httpie/context.py` | `Environment`, `LogLevel`, `LOG_LEVEL_COLORS` |
| Config | `httpie/config.py` | `Config`, `BaseConfigDict`, `ConfigFileError`, `get_default_config_dir()`, `DEFAULT_CONFIG_DIR` |
| Parser | `httpie/cli/argparser.py` | `BaseHTTPieArgumentParser`, `HTTPieArgumentParser`, `HTTPieManagerArgumentParser` |
| Parser spec | `httpie/cli/options.py`, `httpie/cli/definition.py` | `ParserSpec`, `Argument`, `to_argparse()`, `options`, `parser` |
| Plugins | `httpie/plugins/{manager,registry,base,builtin}.py` | `PluginManager`, `plugin_manager`, `BasePlugin`, `AuthPlugin`, `FormatterPlugin`, `TransportPlugin`, `ConverterPlugin` |
| HTTP client | `httpie/client.py` | `collect_messages()`, `build_requests_session()`, `make_request_kwargs()` |
| Domain models | `httpie/models.py` | `HTTPMessage`, `HTTPRequest`, `HTTPResponse`, `RequestsMessageKind`, `OutputOptions` |
| Output models | `httpie/output/models.py` | `ProcessingOptions` |
| Sessions | `httpie/sessions.py` | `Session`, `get_httpie_session()` |
| Output | `httpie/output/{writer,streams,processing}.py` | `write_message()`, `BaseStream` subclasses, `Conversion`, `Formatting` |
| Status | `httpie/status.py` | `ExitStatus`, `http_status_to_exit_status()` |
| Background | `httpie/internal/{update_warnings,daemon_runner,daemons}.py` | `check_updates()`, `run_daemon_task()`, `spawn_daemon()` |
| Manager | `httpie/manager/{__main__,core,cli}.py`, `httpie/manager/tasks/*` | `main()`, `program()`, `dispatch_cli_task()`, `CLI_TASKS` |
