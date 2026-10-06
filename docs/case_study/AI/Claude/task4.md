### 1. Plugin Discovery & Registration

**Discovery mechanism: entry-point groups, one per plugin type** (manager.py:18-24):

| Entry-point group             | Base class        |
| ----------------------------- | ----------------- |
| `httpie.plugins.auth.v1`      | `AuthPlugin`      |
| `httpie.plugins.converter.v1` | `ConverterPlugin` |
| `httpie.plugins.formatter.v1` | `FormatterPlugin` |
| `httpie.plugins.transport.v1` | `TransportPlugin` |

**Governing class:** `PluginManager`, a `list` subclass (manager.py:48). One global instance, `plugin_manager`, is created in registry.py:9. It is pre-populated with the built-ins at registry.py:13-21:

- `BasicAuthPlugin`
- `DigestAuthPlugin`
- `BearerAuthPlugin`
- `HeadersFormatter`
- `JSONFormatter`
- `XMLFormatter`
- `ColorFormatter`

**Load path:**

1. `iter_entry_points()` (manager.py:59-64) calls `importlib_metadata.entry_points()` and yields matches for each of the four groups. The `find_entry_points` helper in compat.py:79 handles the API differences across Python versions.
2. `load_installed_plugins()` (manager.py:66-80) does `entry_point.load()`, which is the dynamic import. It then sets `plugin.package_name` and calls `register()`.
3. A plugin that fails to load only produces a `warnings.warn` with uninstall instructions. It does not abort HTTPie (manager.py:71-78).

**Isolated plugin directory (runtime override):**

- `enable_plugins()` (manager.py:41-45) is a context manager that temporarily extends `sys.path` with the site-packages paths under `config.plugins_dir`.
- `plugins_dir` is defined at config.py:158 and defaults to `<config_dir>/plugins`.
- The `httpie plugins install` command installs into that directory with `pip --prefix={self.dir}` (manager/tasks/plugins.py:66).

**Lifecycle hook:** core.py:46 calls `plugin_manager.load_installed_plugins(env.config.plugins_dir)` inside `raw_main()`.

- It runs after the daemon-mode early return and before `default_options` are merged and arguments are parsed.
- That ordering is what lets `--auth-type` choices include plugin auth types.
- The `--auth-type` argument uses `lazy_choices` with `getter=plugin_manager.get_auth_plugin_mapping` (definition.py:684-694).

`setup.cfg:75-79` only declares HTTPie's own `console_scripts`. It does not declare any plugin entry points.

### 2. Plugin Types & Lifecycle Interception

All four types are in base.py, under `BasePlugin` (base.py:4-13), which defines `name`, `description` and `package_name`.

| Type                            | Responsibility                                       | Where it runs                                                |
| ------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------ |
| `AuthPlugin` (base.py:16)       | Builds a `requests` `AuthBase` from `-a` credentials | **Argument post-processing:** `_process_auth()` (argparser.py:282-337) looks up the plugin by `auth_type`, applies `netrc_parse`/`auth_require`/`auth_parse`/`prompt_password`, then calls `get_auth()`. It also runs when a stored session is loaded (sessions.py:278). |
| `TransportPlugin` (base.py:72)  | Mounts a custom `requests` adapter on a URL prefix   | **Client/session construction:** in client.py:176-182, each plugin is instantiated and `session.mount(prefix, get_adapter())` is called. This is before any request is sent. |
| `ConverterPlugin` (base.py:96)  | Turns a binary body into text for terminal display   | **Output stage:** `Conversion.get_converter(mime)` (processing.py:19-23) picks the first plugin whose `supports(mime)` is true. `convert()` is called from streams.py:211 and streams.py:252, only when a `\0` byte is found in the body. |
| `FormatterPlugin` (base.py:124) | Pretty-prints headers, body and metadata             | **Output stage:** `Formatting` (processing.py:26-58) instantiates plugins by `group_name` and chains `format_headers`, `format_body` and `format_metadata` (streams.py:191-224). |

`PluginManager` has typed accessors for each type. They filter the list with `issubclass` (manager.py:56-57, 82-110). `__init__.py` warns that the plugin API is a work in progress and may be reworked.

### 3. Extension Contracts

**Contract A: `AuthPlugin`** (base.py:16-69)

```
# my_pkg/plugin.py
from httpie.plugins import AuthPlugin
import requests.auth

class TokenAuth(requests.auth.AuthBase):
    def __init__(self, token): self.token = token
    def __call__(self, r):
        r.headers['X-Token'] = self.token
        return r

class MyAuthPlugin(AuthPlugin):
    # BasePlugin metadata
    name = 'My token auth'
    description = 'Shown under --auth-type help'
    # Required: value passed to --auth-type
    auth_type = 'my-token'
    # Optional flags (defaults shown in base.py:34-51)
    auth_require = True      # require -a
    auth_parse = False       # False -> skip user:pass parsing
    netrc_parse = False
    prompt_password = False

    def get_auth(self, username: str = None, password: str = None):
        # self.raw_auth holds the raw -a value (set at argparser.py:322)
        return TokenAuth(self.raw_auth)
# setup.py
entry_points={'httpie.plugins.auth.v1': ['my_token = my_pkg.plugin:MyAuthPlugin']}
```

- `auth_type` and `get_auth()` are the only required members. The base `get_auth` raises `NotImplementedError` (base.py:69).
- Built-in example: `BasicAuthPlugin` in builtin.py:47-54.

**Contract B: `FormatterPlugin`** (base.py:124-165)

```
from httpie.plugins import FormatterPlugin

class UpperFormatter(FormatterPlugin):
    name = 'Upper'
    group_name = 'format'        # base.py:129; groups are selected in Formatting(groups=...)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)   # REQUIRED: reads kwargs['format_options'] (base.py:140)
        self.enabled = self.format_options['json']['format']  # opt-out flag (base.py:138)

    def format_headers(self, headers: str) -> str:
        return headers

    def format_body(self, content: str, mime: str) -> str:
        return content.upper() if mime.endswith('json') else content

    def format_metadata(self, metadata: str) -> str:
        return metadata
entry_points={'httpie.plugins.formatter.v1': ['upper = my_pkg.fmt:UpperFormatter']}
```

- All three `format_*` methods have pass-through defaults, so a subclass overrides only the ones it needs.
- Constructor kwargs come from `Formatting.__init__` (processing.py:40): `cls(env=env, **kwargs)`. The `format_options` key is mandatory, because `FormatterPlugin.__init__` does `kwargs['format_options']`.
- Plugins with `enabled = False` are skipped (processing.py:41).
- Order matters: plugins run in registry order, built-ins first.

**Not run:** I read the code but did not execute any of the examples above.

**Reference:** every base class is in httpie/plugins/base.py. Re-exports are in httpie/plugins/__init__.py:6. The test fixture tests/utils/plugins_cli.py builds real entry-point packages if you want a working reference.