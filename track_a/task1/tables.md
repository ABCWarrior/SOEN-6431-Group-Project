# Task 1 – generated tables

## Table 1.1 – Raw Track A detector inventory (CPD `--minimum-tokens 25` + symilar `-d 3`)

| Group | Tool | Tokens | Lines | Occ. | Files | Scope | Max MTS | Locations (file:begin-end) | Enclosing unit(s) | Audited as |
|---|---|---|---|---|---|---|---|---|---|---|
| CG01 | CPD | 51 | 11 | 2 | 1 | intra-file | 50 | httpie/core.py:86-96<br>httpie/core.py:104-114 | raw_main()<br>raw_main() | CL01 (true clone) |
| CG02 | CPD | 44 | 5 | 2 | 1 | intra-file | 35 | httpie/cli/argparser.py:59-63<br>httpie/cli/argparser.py:580-584 | HTTPieHelpFormatter.add_usage()<br>HTTPieArgumentParser.print_usage() | CL02 (true clone) |
| CG03 | CPD | 33 | 6 | 2 | 1 | intra-file | 25 | httpie/cli/argparser.py:97-102<br>httpie/cli/argparser.py:159-164 | BaseHTTPieArgumentParser.parse_args()<br>HTTPieArgumentParser.parse_args() | CL03 (true clone) |
| CG04 | CPD | 33 | 5 | 2 | 1 | intra-file | 25 | httpie/output/lexers/metadata.py:39-43<br>httpie/output/lexers/metadata.py:50-54 | class MetadataLexer<br>class MetadataLexer | CL04 (true clone) |
| CG05 | CPD | 31 | 4 | 2 | 2 | cross-file | 25 | httpie/core.py:146-149<br>httpie/manager/__main__.py:32-32 | main()<br>main() | CL05 (false positive) |
| CG06 | CPD | 30 | 8 | 2 | 1 | intra-file | 25 | httpie/cli/argparser.py:90-97<br>httpie/cli/argparser.py:151-158 | BaseHTTPieArgumentParser.parse_args()<br>HTTPieArgumentParser.parse_args() | CL03 (true clone) |
| CG07 | CPD | 30 | 5 | 3 | 3 | cross-file | 25 | httpie/output/formatters/headers.py:4-8<br>httpie/output/formatters/json.py:6-10<br>httpie/output/formatters/xml.py:53-57 | class HeadersFormatter<br>class JSONFormatter<br>class XMLFormatter | CL06 (true clone) |
| CG08 | CPD | 30 | 4 | 2 | 1 | intra-file | 25 | httpie/output/ui/rich_progress.py:62-65<br>httpie/output/ui/rich_progress.py:97-100 | class StatusDisplay<br>class ProgressDisplay | CL07 (false positive) |
| CG09 | CPD | 28 | 8 | 2 | 1 | intra-file | 25 | httpie/cli/argparser.py:431-438<br>httpie/cli/argparser.py:459-464 | HTTPieArgumentParser._guess_method()<br>HTTPieArgumentParser._parse_items() | CL08 (true clone) |
| CG10 | CPD | 26 | 3 | 3 | 1 | intra-file | 25 | httpie/output/ui/rich_progress.py:14-16<br>httpie/output/ui/rich_progress.py:63-65<br>httpie/output/ui/rich_progress.py:98-100 | BaseDisplay.start()<br>StatusDisplay.start()<br>ProgressDisplay.start() | CL09 (false positive) |
| CG11 | CPD | 25 | 4 | 2 | 1 | intra-file | 25 | httpie/uploads.py:149-152<br>httpie/uploads.py:195-198 | _prepare_file_for_upload()<br>prepare_request_body() | CL11 (false positive) |
| CG12 | CPD | 25 | 3 | 2 | 2 | cross-file | 25 | httpie/config.py:97-99<br>httpie/sessions.py:183-185 | class BaseConfigDict<br>class Session | CL10 (false positive) |
| SG13 | symilar | – | 5 | 2 | 2 | cross-file | – | httpie/legacy/v3_1_0_session_cookie_format.py [68:76]<br>httpie/legacy/v3_2_0_session_header_format.py [50:59] | – | CL12 (true clone) |
| SG14 | symilar | – | 4 | 2 | 2 | cross-file | – | httpie/__main__.py [6:13]<br>httpie/manager/__main__.py [51:56] | – | CL14 (true clone) |

## Table 1.2 – Consolidated clone list (all Track A detectors + manual audit), largest first

| Rank | ID | Locations | Lines / occ. | Py tokens / occ. | Shared tokens | CPD tokens | Occ. | Files | Found by | Type |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | CL13 | httpie/legacy/v3_1_0_session_cookie_format.py:36-64<br>httpie/legacy/v3_2_0_session_header_format.py:26-46 | 29/21 | 123/106 | 91 | - | 2 | 2 | AST scan | Type 3 |
| 2 | CL03 | httpie/cli/argparser.py:90-105<br>httpie/cli/argparser.py:151-167 | 16/17 | 106/113 | 91 | 33 + 30 | 2 | 1 | CPD | Type 3 |
| 3 | CL06 | httpie/output/formatters/headers.py:6-8<br>httpie/output/formatters/json.py:8-10<br>httpie/output/formatters/xml.py:55-57 | 3/3/3 | 31/31/31 | 62 | 30 | 3 | 3 | CPD, AST scan | Type 2 |
| 4 | CL02 | httpie/cli/argparser.py:59-69<br>httpie/cli/argparser.py:580-591 | 11/12 | 59/71 | 57 | 44 | 2 | 1 | CPD | Type 3 |
| 5 | CL20 | httpie/uploads.py:65-69<br>httpie/models.py:163-169<br>httpie/uploads.py:257-262<br>httpie/client.py:201-203 | 5/7/6/3 | 33/34/45/15 | 51 | - | 4 | 3 | none (manual semantic audit) | Type 4 |
| 6 | CL12 | httpie/legacy/v3_1_0_session_cookie_format.py:67-81<br>httpie/legacy/v3_2_0_session_header_format.py:49-64 | 15/16 | 55/56 | 51 | - | 2 | 2 | symilar, AST scan | Type 3 |
| 7 | CL01 | httpie/core.py:86-96<br>httpie/core.py:104-114 | 11/11 | 51/51 | 51 | 51 | 2 | 1 | CPD | Type 1 |
| 8 | CL04 | httpie/output/lexers/metadata.py:38-47<br>httpie/output/lexers/metadata.py:49-57 | 10/9 | 47/43 | 43 | 33 | 2 | 1 | CPD | Type 3 |
| 9 | CL18 | httpie/output/ui/rich_progress.py:86-94<br>httpie/output/ui/rich_progress.py:132-141 | 9/10 | 51/55 | 41 | - | 2 | 1 | AST scan | Type 3 |
| 10 | CL15 | httpie/output/formatters/colors.py:81-86<br>httpie/output/formatters/colors.py:98-103 | 6/6 | 38/38 | 38 | - | 2 | 1 | AST scan | Type 2 |
| 11 | CL17 | httpie/uploads.py:36-41<br>httpie/uploads.py:55-62 | 6/8 | 43/50 | 35 | - | 2 | 1 | AST scan | Type 3 |
| 12 | CL19 | httpie/cli/argparser.py:382-389<br>httpie/cli/argparser.py:391-397 | 8/7 | 39/40 | 34 | - | 2 | 1 | AST scan | Type 3 |
| 13 | CL16 | httpie/ssl_.py:55-57<br>httpie/ssl_.py:59-61 | 3/3 | 33/33 | 33 | - | 2 | 1 | AST scan | Type 2 |
| 14 | CL22 | httpie/config.py:65-77<br>httpie/internal/update_warnings.py:31-37 | 13/7 | 66/37 | 31 | - | 2 | 2 | none (manual semantic audit) | Type 4 |
| 15 | CL08 | httpie/cli/argparser.py:431-434<br>httpie/cli/argparser.py:459-462 | 4/4 | 26/24 | 24 | 28 | 2 | 1 | CPD | Type 2 |
| 16 | CL14 | httpie/__main__.py:6-14<br>httpie/manager/__main__.py:51-57 | 9/7 | 36/22 | 22 | - | 2 | 2 | symilar | Type 3 |
| 17 | CL21 | httpie/output/formatters/colors.py:180-187<br>httpie/output/formatters/json.py:18-24 | 8/7 | 41/41 | 21 | - | 2 | 2 | none (manual semantic audit) | Type 4 |

## Table 1.3 – File hotspots, raw CPD view (t=25, before false-positive removal)

| File | Code LOC | CPD groups | Cloned lines | Clone density % |
|---|---|---|---|---|
| httpie/cli/argparser.py | 487 | 4 | 51 | 10.47 |
| httpie/core.py | 257 | 2 | 26 | 10.12 |
| httpie/output/ui/rich_progress.py | 113 | 2 | 11 | 9.73 |
| httpie/output/lexers/metadata.py | 49 | 1 | 10 | 20.41 |
| httpie/uploads.py | 204 | 1 | 8 | 3.92 |
| httpie/output/formatters/headers.py | 14 | 1 | 5 | 35.71 |
| httpie/output/formatters/json.py | 27 | 1 | 5 | 18.52 |
| httpie/output/formatters/xml.py | 55 | 1 | 5 | 9.09 |
| httpie/config.py | 131 | 1 | 3 | 2.29 |
| httpie/sessions.py | 240 | 1 | 3 | 1.25 |
| httpie/manager/__main__.py | 43 | 1 | 1 | 2.33 |

## Table 1.4 – File hotspots, confirmed clones only (after Task 2 audit, Types 1–4)

| File | Code LOC | True clones | Clone IDs | Cloned lines | Clone density % |
|---|---|---|---|---|---|
| httpie/cli/argparser.py | 487 | 4 | CL02 CL03 CL08 CL19 | 79 | 16.22 |
| httpie/legacy/v3_1_0_session_cookie_format.py | 82 | 2 | CL12 CL13 | 44 | 53.66 |
| httpie/legacy/v3_2_0_session_header_format.py | 55 | 2 | CL12 CL13 | 37 | 67.27 |
| httpie/uploads.py | 204 | 2 | CL17 CL20 | 25 | 12.25 |
| httpie/output/formatters/colors.py | 325 | 2 | CL15 CL21 | 20 | 6.15 |
| httpie/output/formatters/json.py | 27 | 2 | CL06 CL21 | 10 | 37.04 |
| httpie/core.py | 257 | 1 | CL01 | 22 | 8.56 |
| httpie/output/lexers/metadata.py | 49 | 1 | CL04 | 19 | 38.78 |
| httpie/output/ui/rich_progress.py | 113 | 1 | CL18 | 19 | 16.81 |
| httpie/config.py | 131 | 1 | CL22 | 13 | 9.92 |
| httpie/__main__.py | 14 | 1 | CL14 | 9 | 64.29 |
| httpie/manager/__main__.py | 43 | 1 | CL14 | 7 | 16.28 |
| httpie/models.py | 185 | 1 | CL20 | 7 | 3.78 |
| httpie/internal/update_warnings.py | 120 | 1 | CL22 | 7 | 5.83 |
| httpie/ssl_.py | 80 | 1 | CL16 | 6 | 7.5 |
| httpie/output/formatters/headers.py | 14 | 1 | CL06 | 3 | 21.43 |
| httpie/output/formatters/xml.py | 55 | 1 | CL06 | 3 | 5.45 |
| httpie/client.py | 311 | 1 | CL20 | 3 | 0.96 |

## Table 1.5 – Package hotspots, raw CPD view (t=25)

| Package | Files | Code LOC | CPD groups | Cloned lines | Density % |
|---|---|---|---|---|---|
| httpie/cli | 15 | 2549 | 4 | 51 | 2.0 |
| httpie (top-level modules) | 17 | 2314 | 4 | 40 | 1.73 |
| httpie/output | 23 | 1708 | 4 | 36 | 2.11 |
| httpie/manager | 10 | 579 | 1 | 1 | 0.17 |
| httpie/internal | 5 | 240 | 0 | 0 | 0.0 |
| httpie/legacy | 3 | 137 | 0 | 0 | 0.0 |
| httpie/plugins | 5 | 286 | 0 | 0 | 0.0 |
