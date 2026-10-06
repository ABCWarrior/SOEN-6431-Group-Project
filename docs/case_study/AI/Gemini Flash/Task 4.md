# Task 4: Extension & Plugin Hook Identification

## 1. Plugin Discovery & Registration Architecture

### Discovery Mechanism
HTTPie discovers third-party and installed plugins dynamically using Python Packaging Entry Points via `importlib_metadata` (with compatibility fallbacks defined in `httpie/compat.py`).

Plugin packages declare entry points under four reserved namespace groups:
* `httpie.plugins.auth.v1`
* `httpie.plugins.converter.v1`
* `httpie.plugins.formatter.v1`
* `httpie.plugins.transport.v1`

When scanning for plugins, the system dynamically prepends plugin `site-packages` directories (located under `~/.config/httpie/plugins` or platform equivalent) to `sys.path` within a managed context (`enable_plugins()` / `_load_directories()` in `httpie/plugins/manager.py`). It then queries `importlib_metadata.entry_points()` for each of the group names above and loads them safely.

### Governing Registry & Lifecycle Hook
* **Governing Registry:** `PluginManager` (a specialized subclass of `list`), instantiated as a module-level singleton `plugin_manager` in `httpie/plugins/registry.py`.
* **Application Lifecycle Hook:** Discovery hooks in during the initial bootstrap phase in `httpie/core.py:raw_main()` before CLI arguments are parsed:
  ```python
  # httpie/core.py: line 49
  plugin_manager.load_installed_plugins(env.config.plugins_dir)
  ```
  This guarantees that all custom plugins (and their respective options/auth types) are registered in the `PluginManager` before `parser.parse_args()` processes CLI arguments and choices.

---

## 2. Core Plugin Base Classes & Extension Types

The architecture defines four concrete plugin extension points (all inheriting from `httpie.plugins.base.BasePlugin` in `httpie/plugins/base.py`):

1. **`AuthPlugin` (`httpie.plugins.base.AuthPlugin`)**
   * **Responsibility:** Implements custom authentication schemes (e.g., AWS SigV4, digest, OAuth, HMAC, Bearer tokens).
   * **Lifecycle Interception:** Intercepts during CLI parsing (`HTTPieArgumentParser._process_auth()` in `httpie/cli/argparser.py`) where credentials and flags are gathered, and during request preparation (`httpie/client.py:make_request_kwargs()`) where its auth handler is assigned to the outgoing `requests.Request(auth=...)`.

2. **`TransportPlugin` (`httpie.plugins.base.TransportPlugin`)**
   * **Responsibility:** Provides custom network transports and protocols by supplying custom `requests.adapters.BaseAdapter` implementations (e.g., Unix domain sockets via `http+unix://`, custom proxy tunnels).
   * **Lifecycle Interception:** Intercepts during session construction in `httpie/client.py:build_requests_session()`. The session mounts the adapter for the plugin's URL prefix via `requests_session.mount(prefix=plugin.prefix, adapter=plugin.get_adapter())`.

3. **`FormatterPlugin` (`httpie.plugins.base.FormatterPlugin`)**
   * **Responsibility:** Formats, colors, and transforms request and response headers and body payloads before output rendering (e.g., Pygments syntax highlighting, JSON/XML formatting).
   * **Lifecycle Interception:** Intercepts during output processing in `httpie/output/writer.py:write_message()`, where formatters wrap stream processors and sequentially transform token/text streams written to stdout.

4. **`ConverterPlugin` (`httpie.plugins.base.ConverterPlugin`)**
   * **Responsibility:** Converts non-HTTP or binary data formats (or custom media types) into valid representations for display or transmission.
   * **Lifecycle Interception:** Intercepts during stream ingestion in the output pipeline when content types match the converter's declared MIME types.

---

## 3. Hook Method Signatures & Extension Contracts

### Contract A: Custom Authentication Plugin (`AuthPlugin`)
* **Base Class Definition Reference:** `httpie/plugins/base.py` (lines 14–37)

```python
from httpie.plugins import AuthPlugin
import requests

class CustomTokenAuth(requests.auth.AuthBase):
    def __init__(self, token: str):
        self.token = token

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        r.headers['X-Custom-Token'] = self.token
        return r

class CustomAuthPlugin(AuthPlugin):
    # Required metadata attributes
    name = 'Custom Token Auth'
    description = 'Authenticate using a custom token header'
    auth_type = 'custom-token'  # Used via --auth-type=custom-token

    # Configuration flags
    auth_require = True         # Set to True if --auth is mandatory
    auth_parse = True           # Whether to split raw_auth into username/password
    prompt_password = False     # Whether to prompt if password part is absent
    netrc_parse = False         # Whether to fallback to ~/.netrc

    def get_auth(self, username: str = None, password: str = None) -> CustomTokenAuth:
        """
        Return an auth handler (compatible with requests.auth.AuthBase
        or an (identity, secret) tuple).
        """
        # When auth_parse=True, username carries the extracted key/token
        return CustomTokenAuth(token=username or self.raw_auth)
```

---

### Contract B: Custom Transport Adapter Plugin (`TransportPlugin`)
* **Base Class Definition Reference:** `httpie/plugins/base.py` (lines 40–51)

```python
from httpie.plugins import TransportPlugin
from requests.adapters import HTTPAdapter

class CustomUnixSocketAdapter(HTTPAdapter):
    # Standard requests.adapters.BaseAdapter implementation
    pass

class CustomTransportPlugin(TransportPlugin):
    # Required metadata attributes
    name = 'Unix Socket Transport'
    description = 'Transport adapter enabling unix socket URLs'

    # URL prefix to match and mount onto requests.Session
    prefix = 'http+unix://'

    def get_adapter(self) -> CustomUnixSocketAdapter:
        """
        Return an initialized requests.adapters.BaseAdapter instance.
        """
        return CustomUnixSocketAdapter()
```
