# Task 2 – generated tables

## Table 2.1 – Classification of every Track A clone

| ID | Verdict | Type | Locations | CPD tokens | Track A detector(s) | Raw sim. | Blind sim. | Metric-suggested | Agrees | Rationale |
|---|---|---|---|---|---|---|---|---|---|---|
| CL01 | true clone | Type 1 | httpie/core.py:86-96<br>httpie/core.py:104-114 | 51 | CPD | 1.0 | 1.0 | Type 1 | yes | KeyboardInterrupt / SystemExit handlers repeated verbatim in the outer and inner try of raw_main(); only indentation differs. Token-identical over 51 tokens. |
| CL02 | true clone | Type 3 | httpie/cli/argparser.py:59-69<br>httpie/cli/argparser.py:580-591 | 44 | CPD | 0.785 | 0.877 | Type 3 | yes | Same sys.exc_info() inspection of the failing argparse.Action; the second copy adds a condition (and exception.args[0].option_strings) and a different consequent (whitelist.add vs displayed_actions.insert). Gapped copy. |
| CL03 | true clone | Type 3 | httpie/cli/argparser.py:90-105<br>httpie/cli/argparser.py:151-167 | 33 + 30 | CPD | 0.831 | 0.831 | Type 3 | yes | Subclass re-implements the base parse_args instead of calling it: one statement added (self.env.args = namespace = ...), self.parse_known_args -> super().parse_known_args, getattr(...) -> direct attribute. CPD reports it as two overlapping groups. |
| CL04 | true clone | Type 3 | httpie/output/lexers/metadata.py:38-47<br>httpie/output/lexers/metadata.py:49-57 | 33 | CPD | 0.911 | 0.956 | Type 3 | yes | Two Pygments (regex, bygroups(...)) rule tuples: different regex literal, and the first has an extra group (speed_based_token). Declarative data clone. |
| CL05 | false positive | FP: signature only | httpie/core.py:146-149<br>httpie/manager/__main__.py:32-32 | 31 | CPD | 1.0 | 1.0 | Type 1 | n/a (false positive) | Match covers only the parameter list `args: List[Union[str, bytes]] = sys.argv, env: Environment = Environment()) -> ExitStatus`; the bodies are unrelated. |
| CL06 | true clone | Type 2 | httpie/output/formatters/headers.py:6-8<br>httpie/output/formatters/json.py:8-10<br>httpie/output/formatters/xml.py:55-57 | 30 | CPD, AST scan | 0.935 | 1.0 | Type 2 | yes | Three constructors identical except for the string literals selecting the --format-options switch (headers/sort, json/format, xml/format). CPD stops at the first differing literal; blind tokens are identical. |
| CL07 | false positive | FP: overriding signature | httpie/output/ui/rich_progress.py:62-65<br>httpie/output/ui/rich_progress.py:97-100 | 30 | CPD | 0.968 | 1.0 | Type 2 | n/a (false positive) | `(BaseDisplay): def start(self, *, total, at, description) -> None:` repeated because both classes override BaseDisplay.start; bodies differ completely. |
| CL08 | true clone | Type 2 | httpie/cli/argparser.py:431-434<br>httpie/cli/argparser.py:459-462 | 28 | CPD | 0.92 | 0.96 | Type 3 | no (Type 3) | Same error-handling clause `except <X> as e: if self.args.traceback: raise; self.error(e.args[0])`, only the exception class differs (argparse.ArgumentTypeError vs ParseError). The metric suggests Type 3 only because the qualified name adds two tokens (`argparse .`); a differing type name is a Type 2 variation (Roy & Cordy), so Type 2 is kept. |
| CL09 | false positive | FP: overriding signature | httpie/output/ui/rich_progress.py:14-16<br>httpie/output/ui/rich_progress.py:63-65<br>httpie/output/ui/rich_progress.py:98-100 | 26 | CPD | 1.0 | 1.0 | Type 1 | n/a (false positive) | Abstract method and its two overrides must share the signature (interface conformance). |
| CL10 | false positive | FP: overriding signature | httpie/config.py:97-99<br>httpie/sessions.py:183-185 | 25 | CPD | 1.0 | 1.0 | Type 1 | n/a (false positive) | `return data` + the post_process_data hook signature; Session overrides the hook declared by BaseConfigDict (Template Method), bodies differ. |
| CL11 | false positive | FP: parameter list | httpie/uploads.py:149-152<br>httpie/uploads.py:195-198 | 25 | CPD | 0.875 | 0.938 | Type 3 | n/a (false positive) | Shared keyword parameters (callback, chunked, content_length_header_value) because one function forwards to the other; bodies differ. |
| CL12 | true clone | Type 3 | httpie/legacy/v3_1_0_session_cookie_format.py:67-81<br>httpie/legacy/v3_2_0_session_header_format.py:49-64 | - | symilar, AST scan | 0.793 | 0.919 | Type 3 | yes | Same signature and `if issubclass(original_type, dict): return {...} else: return ...` skeleton; the dict comprehension differs. Copied between versioned migration modules. |
| CL13 | true clone | Type 3 | httpie/legacy/v3_1_0_session_cookie_format.py:36-64<br>httpie/legacy/v3_2_0_session_header_format.py:26-46 | - | AST scan | 0.655 | 0.795 | Type 3 | yes | Same normalise-then-warn structure; the warning block (format template, add suffix for named sessions, add link, warn_legacy_usage) is copied with renamed constants; the normalisation step differs. |
| CL14 | true clone | Type 3 | httpie/__main__.py:6-14<br>httpie/manager/__main__.py:51-57 | - | symilar | 0.724 | 0.759 | Type 3 | yes | Same try / except KeyboardInterrupt -> ExitStatus.ERROR_CTRL_C wrapper; the http entry point adds two lazy imports and returns .value. |
| CL15 | true clone | Type 2 | httpie/output/formatters/colors.py:81-86<br>httpie/output/formatters/colors.py:98-103 | - | AST scan | 0.895 | 1.0 | Type 2 | yes | Identical pygments.highlight(...).strip() call; only parameter and lexer names differ (headers/http_lexer vs metadata/metadata_lexer). |
| CL16 | true clone | Type 2 | httpie/ssl_.py:55-57<br>httpie/ssl_.py:59-61 | - | AST scan | 0.939 | 1.0 | Type 2 | yes | Inject ssl_context into kwargs and delegate to super(); only the method name differs. |
| CL17 | true clone | Type 3 | httpie/uploads.py:36-41<br>httpie/uploads.py:55-62 | - | AST scan | 0.731 | 0.753 | Type 3 | yes | Both iterate chunks, set the read event and yield; the second reads from an encoder in a while-loop with a break, the first calls a progress callback. |
| CL18 | true clone | Type 3 | httpie/output/ui/rich_progress.py:86-94<br>httpie/output/ui/rich_progress.py:132-141 | - | AST scan | 0.698 | 0.774 | Type 3 | yes | Stop the widget, then `if time_spent: self._print_summary(...)`; the second unpacks the task and passes different arguments, the first prints the description. |
| CL19 | true clone | Type 3 | httpie/cli/argparser.py:382-389<br>httpie/cli/argparser.py:391-397 | - | AST scan | 0.759 | 0.861 | Type 3 | yes | Both check _ensure_one_data_source(...) then assign self.args.data; argument list and conversion differ. |
| CL20 | true clone | Type 4 | httpie/uploads.py:65-69<br>httpie/models.py:163-169<br>httpie/uploads.py:257-262<br>httpie/client.py:201-203 | - | none (manual semantic audit) | 0.333 | 0.41 | no syntactic similarity | yes | The same responsibility, "coerce str to bytes (UTF-8)", is re-implemented four times with different syntax although uploads.as_bytes() exists (compress_request in the same module does not use it). |
| CL21 | true clone | Type 4 | httpie/output/formatters/colors.py:180-187<br>httpie/output/formatters/json.py:18-24 | - | none (manual semantic audit) | 0.39 | 0.512 | no syntactic similarity | yes | "Is this body JSON?" decided twice: json.loads(body) in the colour formatter, load_prefixed_json(body) in the JSON formatter; the developers flag it (`# FIXME: the body also gets parsed in json.py`). |
| CL22 | true clone | Type 4 | httpie/config.py:65-77<br>httpie/internal/update_warnings.py:31-37 | - | none (manual semantic audit) | 0.485 | 0.602 | no syntactic similarity | yes | Both "open a JSON file and json.load it, tolerating a missing/broken file"; they differ only in error policy (raise ConfigFileError vs return {}). Partial semantic clone. |

## Table 2.2 – Pair metrics (first occurrence vs each other occurrence)

| Clone | Occurrence A | Occurrence B | Tokens A/B | Raw ident. | Blind ident. | Raw sim. | Blind sim. | Suggested |
|---|---|---|---|---|---|---|---|---|
| CL01 | httpie/core.py:86-96 | httpie/core.py:104-114 | 51/51 | True | True | 1.0 | 1.0 | Type 1 |
| CL02 | httpie/cli/argparser.py:59-69 | httpie/cli/argparser.py:580-591 | 59/71 | False | False | 0.785 | 0.877 | Type 3 |
| CL03 | httpie/cli/argparser.py:90-105 | httpie/cli/argparser.py:151-167 | 106/113 | False | False | 0.831 | 0.831 | Type 3 |
| CL04 | httpie/output/lexers/metadata.py:38-47 | httpie/output/lexers/metadata.py:49-57 | 47/43 | False | False | 0.911 | 0.956 | Type 3 |
| CL05 | httpie/core.py:146-149 | httpie/manager/__main__.py:32-32 | 30/30 | True | True | 1.0 | 1.0 | Type 1 |
| CL06 | httpie/output/formatters/headers.py:6-8 | httpie/output/formatters/json.py:8-10 | 31/31 | False | True | 0.935 | 1.0 | Type 2 |
| CL06 | httpie/output/formatters/headers.py:6-8 | httpie/output/formatters/xml.py:55-57 | 31/31 | False | True | 0.935 | 1.0 | Type 2 |
| CL07 | httpie/output/ui/rich_progress.py:62-65 | httpie/output/ui/rich_progress.py:97-100 | 31/31 | False | True | 0.968 | 1.0 | Type 2 |
| CL08 | httpie/cli/argparser.py:431-434 | httpie/cli/argparser.py:459-462 | 26/24 | False | False | 0.92 | 0.96 | Type 3 |
| CL09 | httpie/output/ui/rich_progress.py:14-16 | httpie/output/ui/rich_progress.py:63-65 | 25/25 | True | True | 1.0 | 1.0 | Type 1 |
| CL09 | httpie/output/ui/rich_progress.py:14-16 | httpie/output/ui/rich_progress.py:98-100 | 25/25 | True | True | 1.0 | 1.0 | Type 1 |
| CL10 | httpie/config.py:97-99 | httpie/sessions.py:183-185 | 24/24 | True | True | 1.0 | 1.0 | Type 1 |
| CL11 | httpie/uploads.py:149-152 | httpie/uploads.py:195-198 | 30/34 | False | False | 0.875 | 0.938 | Type 3 |
| CL12 | httpie/legacy/v3_1_0_session_cookie_format.py:67-81 | httpie/legacy/v3_2_0_session_header_format.py:49-64 | 55/56 | False | False | 0.793 | 0.919 | Type 3 |
| CL13 | httpie/legacy/v3_1_0_session_cookie_format.py:36-64 | httpie/legacy/v3_2_0_session_header_format.py:26-46 | 123/106 | False | False | 0.655 | 0.795 | Type 3 |
| CL14 | httpie/__main__.py:6-14 | httpie/manager/__main__.py:51-57 | 36/22 | False | False | 0.724 | 0.759 | Type 3 |
| CL15 | httpie/output/formatters/colors.py:81-86 | httpie/output/formatters/colors.py:98-103 | 38/38 | False | True | 0.895 | 1.0 | Type 2 |
| CL16 | httpie/ssl_.py:55-57 | httpie/ssl_.py:59-61 | 33/33 | False | True | 0.939 | 1.0 | Type 2 |
| CL17 | httpie/uploads.py:36-41 | httpie/uploads.py:55-62 | 43/50 | False | False | 0.731 | 0.753 | Type 3 |
| CL18 | httpie/output/ui/rich_progress.py:86-94 | httpie/output/ui/rich_progress.py:132-141 | 51/55 | False | False | 0.698 | 0.774 | Type 3 |
| CL19 | httpie/cli/argparser.py:382-389 | httpie/cli/argparser.py:391-397 | 39/40 | False | False | 0.759 | 0.861 | Type 3 |
| CL20 | httpie/uploads.py:65-69 | httpie/models.py:163-169 | 33/34 | False | False | 0.448 | 0.657 | no syntactic similarity |
| CL20 | httpie/uploads.py:65-69 | httpie/uploads.py:257-262 | 33/45 | False | False | 0.333 | 0.41 | no syntactic similarity |
| CL20 | httpie/uploads.py:65-69 | httpie/client.py:201-203 | 33/15 | False | False | 0.458 | 0.542 | no syntactic similarity |
| CL21 | httpie/output/formatters/colors.py:180-187 | httpie/output/formatters/json.py:18-24 | 41/41 | False | False | 0.39 | 0.512 | no syntactic similarity |
| CL22 | httpie/config.py:65-77 | httpie/internal/update_warnings.py:31-37 | 66/37 | False | False | 0.485 | 0.602 | no syntactic similarity |

## Table 2.3 – AST scanner pairs (blind similarity >= 0.75) with audit verdict

| Blind sim. | Raw sim. | Unit A | Unit B | Verdict | Clone / reason |
|---|---|---|---|---|---|
| 1.0 | 0.895 | httpie/output/formatters/colors.py:81-86 ColorFormatter.format_headers() | httpie/output/formatters/colors.py:98-103 ColorFormatter.format_metadata() | true clone | CL15 |
| 1.0 | 0.939 | httpie/ssl_.py:55-57 HTTPieHTTPSAdapter.init_poolmanager() | httpie/ssl_.py:59-61 HTTPieHTTPSAdapter.proxy_manager_for() | true clone | CL16 |
| 1.0 | 0.935 | httpie/output/formatters/headers.py:6-8 HeadersFormatter.__init__() | httpie/output/formatters/json.py:8-10 JSONFormatter.__init__() | true clone | CL06 |
| 1.0 | 0.935 | httpie/output/formatters/headers.py:6-8 HeadersFormatter.__init__() | httpie/output/formatters/xml.py:55-57 XMLFormatter.__init__() | true clone | CL06 |
| 1.0 | 0.968 | httpie/output/formatters/json.py:8-10 JSONFormatter.__init__() | httpie/output/formatters/xml.py:55-57 XMLFormatter.__init__() | true clone | CL06 |
| 0.947 | 0.674 | httpie/cli/argtypes.py:15-19 KeyValueArg.__init__() | httpie/cli/nested_json/errors.py:7-17 NestedJSONSyntaxError.__init__() | false positive | attribute-assignment constructor idiom |
| 0.917 | 0.807 | httpie/legacy/v3_1_0_session_cookie_format.py:67-81 post_process() | httpie/legacy/v3_2_0_session_header_format.py:49-64 post_process() | true clone | CL12 |
| 0.917 | 0.812 | httpie/cli/options.py:64-69 ParserSpec.serialize() | httpie/cli/options.py:89-95 Group.serialize() | false positive | to-dict serialisation idiom (different fields) |
| 0.896 | 0.776 | httpie/cli/argparser.py:42-45 HTTPieHelpFormatter.__init__() | httpie/ssl_.py:55-57 HTTPieHTTPSAdapter.init_poolmanager() | false positive | kwargs injection + super() idiom |
| 0.896 | 0.776 | httpie/cli/argparser.py:42-45 HTTPieHelpFormatter.__init__() | httpie/ssl_.py:59-61 HTTPieHTTPSAdapter.proxy_manager_for() | false positive | kwargs injection + super() idiom |
| 0.862 | 0.585 | httpie/output/ui/rich_palette.py:32-36 _GenericColorCaster._translate() | httpie/uploads.py:65-69 as_bytes() | false positive | isinstance-then-convert idiom |
| 0.857 | 0.779 | httpie/cli/argparser.py:382-389 HTTPieArgumentParser._body_from_file() | httpie/cli/argparser.py:391-397 HTTPieArgumentParser._body_from_input() | true clone | CL19 |
| 0.853 | 0.773 | httpie/uploads.py:26-34 ChunkedUploadStream.__init__() | httpie/uploads.py:47-53 ChunkedMultipartUploadStream.__init__() | false positive | attribute-assignment constructor idiom |
| 0.853 | 0.588 | httpie/cli/options.py:59-62 ParserSpec.add_group() | httpie/output/streams.py:145-148 EncodedStream.decode_chunk() | false positive | create/append/return idiom |
| 0.842 | 0.632 | httpie/models.py:52-58 HTTPMessage.content_type() | httpie/models.py:163-169 HTTPRequest.body() | false positive | opposite conversions (decode vs encode) |
| 0.826 | 0.543 | httpie/cli/nested_json/errors.py:7-17 NestedJSONSyntaxError.__init__() | httpie/uploads.py:26-34 ChunkedUploadStream.__init__() | false positive | attribute-assignment constructor idiom |
| 0.816 | 0.421 | httpie/cli/options.py:242-249 parser_to_parser_spec() | httpie/manager/tasks/sessions.py:63-69 cli_upgrade_session() | false positive | single keyword-argument call wrapper |
| 0.81 | 0.517 | httpie/cli/nested_json/errors.py:7-17 NestedJSONSyntaxError.__init__() | httpie/cli/nested_json/tokens.py:56-66 Path.__init__() | false positive | attribute-assignment constructor idiom |
| 0.806 | 0.611 | httpie/client.py:314-322 json_dict_to_request_body() | httpie/uploads.py:65-69 as_bytes() | false positive | if/else value-conversion idiom |
| 0.805 | 0.506 | httpie/cli/argtypes.py:15-19 KeyValueArg.__init__() | httpie/uploads.py:26-34 ChunkedUploadStream.__init__() | false positive | attribute-assignment constructor idiom |
| 0.8 | 0.427 | httpie/manager/tasks/sessions.py:63-69 cli_upgrade_session() | httpie/output/ui/man_pages.py:39-48 display_for() | false positive | single keyword-argument call wrapper |
| 0.794 | 0.441 | httpie/plugins/builtin.py:63-68 DigestAuthPlugin.get_auth() | httpie/sessions.py:46-53 session_hostname_to_dirname() | false positive | single-call wrapper |
| 0.793 | 0.661 | httpie/legacy/v3_1_0_session_cookie_format.py:36-64 pre_process() | httpie/legacy/v3_2_0_session_header_format.py:26-46 pre_process() | true clone | CL13 |
| 0.792 | 0.515 | httpie/cli/argtypes.py:15-19 KeyValueArg.__init__() | httpie/output/streams.py:33-49 BaseStream.__init__() | false positive | attribute-assignment constructor idiom |
| 0.788 | 0.364 | httpie/output/streams.py:145-148 EncodedStream.decode_chunk() | httpie/output/ui/rich_palette.py:32-36 _GenericColorCaster._translate() | false positive | short helper, coincidental shape |
| 0.787 | 0.656 | httpie/sessions.py:170-183 Session.pre_process_data() | httpie/sessions.py:185-198 Session.post_process_data() | false positive | inverse operations (import vs export loop) |
| 0.787 | 0.557 | httpie/cli/argtypes.py:262-268 response_charset_type() | httpie/cli/requestitems.py:226-230 load_json() | false positive | try / except -> raise validation idiom |
| 0.778 | 0.389 | httpie/output/processing.py:49-53 Formatting.format_body() | httpie/plugins/builtin.py:63-68 DigestAuthPlugin.get_auth() | false positive | short helper, coincidental shape |
| 0.776 | 0.49 | httpie/output/streams.py:33-49 BaseStream.__init__() | httpie/uploads.py:26-34 ChunkedUploadStream.__init__() | false positive | attribute-assignment constructor idiom |
| 0.776 | 0.537 | httpie/output/ui/rich_palette.py:32-36 _GenericColorCaster._translate() | httpie/utils.py:258-263 unwrap_context() | false positive | isinstance if/else idiom |
| 0.774 | 0.472 | httpie/cli/nested_json/errors.py:7-17 NestedJSONSyntaxError.__init__() | httpie/output/streams.py:33-49 BaseStream.__init__() | false positive | attribute-assignment constructor idiom |
| 0.774 | 0.698 | httpie/output/ui/rich_progress.py:86-94 StatusDisplay.stop() | httpie/output/ui/rich_progress.py:132-141 ProgressDisplay.stop() | true clone | CL18 |
| 0.77 | 0.475 | httpie/cli/nested_json/tokens.py:56-66 Path.__init__() | httpie/output/streams.py:33-49 BaseStream.__init__() | false positive | attribute-assignment constructor idiom |
| 0.769 | 0.513 | httpie/output/formatters/colors.py:81-86 ColorFormatter.format_headers() | httpie/output/formatters/colors.py:105-113 ColorFormatter.get_lexer_for_body() | false positive | single keyword-argument call wrapper |
| 0.769 | 0.513 | httpie/output/formatters/colors.py:98-103 ColorFormatter.format_metadata() | httpie/output/formatters/colors.py:105-113 ColorFormatter.get_lexer_for_body() | false positive | single keyword-argument call wrapper |
| 0.767 | 0.301 | httpie/cli/argtypes.py:58-62 KeyValueArgType.__init__() | httpie/cli/dicts.py:38-46 HTTPHeadersDict.remove_item() | false positive | short loop, coincidental shape |
| 0.765 | 0.529 | httpie/uploads.py:65-69 as_bytes() | httpie/utils.py:258-263 unwrap_context() | false positive | isinstance if/else idiom |
| 0.763 | 0.553 | httpie/cli/options.py:59-62 ParserSpec.add_group() | httpie/cli/options.py:83-87 Group.add_argument() | false positive | create/append/return idiom |
| 0.763 | 0.526 | httpie/manager/tasks/check_updates.py:7-10 cli_check_updates() | httpie/manager/tasks/sessions.py:63-69 cli_upgrade_session() | false positive | short command handler, coincidental shape |
| 0.762 | 0.524 | httpie/manager/tasks/plugins.py:23-28 PluginInstaller.__init__() | httpie/uploads.py:26-34 ChunkedUploadStream.__init__() | false positive | attribute-assignment constructor idiom |
| 0.761 | 0.522 | httpie/cli/nested_json/errors.py:7-17 NestedJSONSyntaxError.__init__() | httpie/manager/tasks/plugins.py:23-28 PluginInstaller.__init__() | false positive | attribute-assignment constructor idiom |
| 0.758 | 0.364 | httpie/cli/options.py:59-62 ParserSpec.add_group() | httpie/output/ui/rich_palette.py:32-36 _GenericColorCaster._translate() | false positive | short helper, coincidental shape |
| 0.753 | 0.731 | httpie/uploads.py:36-41 ChunkedUploadStream.__iter__() | httpie/uploads.py:55-62 ChunkedMultipartUploadStream.__iter__() | true clone | CL17 |
| 0.752 | 0.495 | httpie/compat.py:48-56 cached_property.__set_name__() | httpie/downloads.py:318-323 DownloadStatus.started() | false positive | attribute-assignment sequence, coincidental |
| 0.75 | 0.5 | httpie/cli/nested_json/errors.py:7-17 NestedJSONSyntaxError.__init__() | httpie/output/ui/rich_progress.py:63-72 StatusDisplay.start() | false positive | attribute-assignment sequence, coincidental |
| 0.75 | 0.591 | httpie/cli/utils.py:49-54 LazyChoices.load() | httpie/cli/utils.py:56-63 LazyChoices.help() | false positive | lazy-cache property idiom |
| 0.75 | 0.3 | httpie/downloads.py:137-141 get_filename_max_length() | httpie/output/processing.py:49-53 Formatting.format_body() | false positive | short helper, coincidental shape |
