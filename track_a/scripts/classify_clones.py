"""Task 2 - Clone classification & semantic audit (Track A).

Every clone found by the Track A detectors (PMD CPD, pylint symilar, the
function-level AST scanner) plus the manually identified semantic (Type 4)
candidates is listed ONCE below, with:
  * the audited clone region of every occurrence (file, first line, last line)
  * which Track A detector(s) reported it
  * the manual verdict + type + rationale (from reading the code)

The script then computes objective, deterministic metrics for every pair of
occurrences (first occurrence vs each other one) with Python's `tokenize`:

  raw tokens    : real token text, comments/layout dropped
  blind tokens  : identifiers -> ID, literals -> LIT (keywords/operators/self kept)
  raw_identical / blind_identical / raw_sim / blind_sim (difflib ratio)

and derives a *metric-suggested* type that the manual type is checked against:
  raw identical -> Type 1 ; blind identical -> Type 2 ; blind_sim >= 0.70 -> Type 3 ;
  otherwise "no syntactic similarity" (consistent only with Type 4 or a false positive).

Outputs (in track_a/task2/):
  clone_classification.csv / .md   master table (one row per clone)
  pair_metrics.csv                 metrics per occurrence pair
  ast_pairs_adjudicated.csv        every AST-scanner pair with its verdict
  detector_precision.txt           precision of each Track A detector after audit
  hotspots_confirmed.csv           per-file hotspots recomputed on confirmed clones only
"""
import csv
import io
import keyword
import tokenize
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

OUT = Path('track_a/task2')
AST_PAIRS = Path('track_a/task1/ast_scan/ast_pairs_t30_s075.csv')
CPD_INVENTORY = Path('track_a/task1/clone_inventory.csv')
LOC_FILES = Path('track_a/task1/hotspots_files.csv')

# ---------------------------------------------------------------------------
# Master clone list.  regions: (file, first_line, last_line, unit)
# cpd: CPD group ids from track_a/task1/clone_inventory.csv (CGxx), symilar: bool,
# ast: True if the AST scanner reported the pair(s).
# verdict: 'true clone' or 'false positive'
# ---------------------------------------------------------------------------
CLONES = [
    dict(id='CL01', cpd=['CG01'], symilar=False, ast=False,
         regions=[('httpie/core.py', 86, 96, 'raw_main() - outer try (argument parsing)'),
                  ('httpie/core.py', 104, 114, 'raw_main() - inner try (main_program call)')],
         verdict='true clone', type='Type 1',
         rationale='KeyboardInterrupt / SystemExit handlers repeated verbatim in the outer and inner try '
                   'of raw_main(); only indentation differs. Token-identical over 51 tokens.'),
    dict(id='CL02', cpd=['CG02'], symilar=False, ast=False,
         regions=[('httpie/cli/argparser.py', 59, 69, 'HTTPieHelpFormatter.add_usage()'),
                  ('httpie/cli/argparser.py', 580, 591, 'HTTPieArgumentParser.print_usage()')],
         verdict='true clone', type='Type 3',
         rationale='Same sys.exc_info() inspection of the failing argparse.Action; the second copy adds a '
                   'condition (and exception.args[0].option_strings) and a different consequent '
                   '(whitelist.add vs displayed_actions.insert). Gapped copy.'),
    dict(id='CL03', cpd=['CG03', 'CG06'], symilar=False, ast=False,
         regions=[('httpie/cli/argparser.py', 90, 105, 'BaseHTTPieArgumentParser.parse_args()'),
                  ('httpie/cli/argparser.py', 151, 167, 'HTTPieArgumentParser.parse_args()')],
         verdict='true clone', type='Type 3',
         rationale='Subclass re-implements the base parse_args instead of calling it: one statement added '
                   '(self.env.args = namespace = ...), self.parse_known_args -> super().parse_known_args, '
                   'getattr(...) -> direct attribute. CPD reports it as two overlapping groups.'),
    dict(id='CL04', cpd=['CG04'], symilar=False, ast=False,
         regions=[('httpie/output/lexers/metadata.py', 38, 47, 'MetadataLexer.tokens (elapsed-time rule)'),
                  ('httpie/output/lexers/metadata.py', 49, 57, 'MetadataLexer.tokens (generic rule)')],
         verdict='true clone', type='Type 3',
         rationale='Two Pygments (regex, bygroups(...)) rule tuples: different regex literal, and the first '
                   'has an extra group (speed_based_token). Declarative data clone.'),
    dict(id='CL05', cpd=['CG05'], symilar=False, ast=False,
         regions=[('httpie/core.py', 146, 149, 'main() signature'),
                  ('httpie/manager/__main__.py', 32, 32, 'main() signature')],
         verdict='false positive', type='-', fp_kind='signature only',
         rationale='Match covers only the parameter list `args: List[Union[str, bytes]] = sys.argv, '
                   'env: Environment = Environment()) -> ExitStatus`; the bodies are unrelated.'),
    dict(id='CL06', cpd=['CG07'], symilar=False, ast=True,
         regions=[('httpie/output/formatters/headers.py', 6, 8, 'HeadersFormatter.__init__()'),
                  ('httpie/output/formatters/json.py', 8, 10, 'JSONFormatter.__init__()'),
                  ('httpie/output/formatters/xml.py', 55, 57, 'XMLFormatter.__init__()')],
         verdict='true clone', type='Type 2',
         rationale='Three constructors identical except for the string literals selecting the '
                   '--format-options switch (headers/sort, json/format, xml/format). CPD stops at the '
                   'first differing literal; blind tokens are identical.'),
    dict(id='CL07', cpd=['CG08'], symilar=False, ast=False,
         regions=[('httpie/output/ui/rich_progress.py', 62, 65, 'StatusDisplay.start() signature'),
                  ('httpie/output/ui/rich_progress.py', 97, 100, 'ProgressDisplay.start() signature')],
         verdict='false positive', type='-', fp_kind='overriding signature',
         rationale='`(BaseDisplay): def start(self, *, total, at, description) -> None:` repeated because '
                   'both classes override BaseDisplay.start; bodies differ completely.'),
    dict(id='CL08', cpd=['CG09'], symilar=False, ast=False,
         regions=[('httpie/cli/argparser.py', 431, 434, 'HTTPieArgumentParser._guess_method()'),
                  ('httpie/cli/argparser.py', 459, 462, 'HTTPieArgumentParser._parse_items()')],
         verdict='true clone', type='Type 2',
         rationale='Same error-handling clause `except <X> as e: if self.args.traceback: raise; '
                   'self.error(e.args[0])`, only the exception class differs '
                   '(argparse.ArgumentTypeError vs ParseError). The metric suggests Type 3 only because the '
                   'qualified name adds two tokens (`argparse .`); a differing type name is a Type 2 '
                   'variation (Roy & Cordy), so Type 2 is kept.'),
    dict(id='CL09', cpd=['CG10'], symilar=False, ast=False,
         regions=[('httpie/output/ui/rich_progress.py', 14, 16, 'BaseDisplay.start() signature'),
                  ('httpie/output/ui/rich_progress.py', 63, 65, 'StatusDisplay.start() signature'),
                  ('httpie/output/ui/rich_progress.py', 98, 100, 'ProgressDisplay.start() signature')],
         verdict='false positive', type='-', fp_kind='overriding signature',
         rationale='Abstract method and its two overrides must share the signature (interface conformance).'),
    dict(id='CL10', cpd=['CG12'], symilar=False, ast=False,
         regions=[('httpie/config.py', 97, 99, 'BaseConfigDict.pre/post_process_data() hooks'),
                  ('httpie/sessions.py', 183, 185, 'Session.pre/post_process_data() overrides')],
         verdict='false positive', type='-', fp_kind='overriding signature',
         rationale='`return data` + the post_process_data hook signature; Session overrides the hook '
                   'declared by BaseConfigDict (Template Method), bodies differ.'),
    dict(id='CL11', cpd=['CG11'], symilar=False, ast=False,
         regions=[('httpie/uploads.py', 149, 152, '_prepare_file_for_upload() parameters'),
                  ('httpie/uploads.py', 195, 198, 'prepare_request_body() parameters')],
         verdict='false positive', type='-', fp_kind='parameter list',
         rationale='Shared keyword parameters (callback, chunked, content_length_header_value) because one '
                   'function forwards to the other; bodies differ.'),
    dict(id='CL12', cpd=[], symilar=True, ast=True,
         regions=[('httpie/legacy/v3_1_0_session_cookie_format.py', 67, 81, 'post_process()'),
                  ('httpie/legacy/v3_2_0_session_header_format.py', 49, 64, 'post_process()')],
         verdict='true clone', type='Type 3',
         rationale='Same signature and `if issubclass(original_type, dict): return {...} else: return ...` '
                   'skeleton; the dict comprehension differs. Copied between versioned migration modules.'),
    dict(id='CL13', cpd=[], symilar=False, ast=True,
         regions=[('httpie/legacy/v3_1_0_session_cookie_format.py', 36, 64, 'pre_process()'),
                  ('httpie/legacy/v3_2_0_session_header_format.py', 26, 46, 'pre_process()')],
         verdict='true clone', type='Type 3',
         rationale='Same normalise-then-warn structure; the warning block (format template, add suffix for '
                   'named sessions, add link, warn_legacy_usage) is copied with renamed constants; the '
                   'normalisation step differs.'),
    dict(id='CL14', cpd=[], symilar=True, ast=False,
         regions=[('httpie/__main__.py', 6, 14, 'main() (http/https entry point)'),
                  ('httpie/manager/__main__.py', 51, 57, 'program() (httpie manager)')],
         verdict='true clone', type='Type 3',
         rationale='Same try / except KeyboardInterrupt -> ExitStatus.ERROR_CTRL_C wrapper; the http entry '
                   'point adds two lazy imports and returns .value.'),
    dict(id='CL15', cpd=[], symilar=False, ast=True,
         regions=[('httpie/output/formatters/colors.py', 81, 86, 'ColorFormatter.format_headers()'),
                  ('httpie/output/formatters/colors.py', 98, 103, 'ColorFormatter.format_metadata()')],
         verdict='true clone', type='Type 2',
         rationale='Identical pygments.highlight(...).strip() call; only parameter and lexer names differ '
                   '(headers/http_lexer vs metadata/metadata_lexer).'),
    dict(id='CL16', cpd=[], symilar=False, ast=True,
         regions=[('httpie/ssl_.py', 55, 57, 'HTTPieHTTPSAdapter.init_poolmanager()'),
                  ('httpie/ssl_.py', 59, 61, 'HTTPieHTTPSAdapter.proxy_manager_for()')],
         verdict='true clone', type='Type 2',
         rationale='Inject ssl_context into kwargs and delegate to super(); only the method name differs.'),
    dict(id='CL17', cpd=[], symilar=False, ast=True,
         regions=[('httpie/uploads.py', 36, 41, 'ChunkedUploadStream.__iter__()'),
                  ('httpie/uploads.py', 55, 62, 'ChunkedMultipartUploadStream.__iter__()')],
         verdict='true clone', type='Type 3',
         rationale='Both iterate chunks, set the read event and yield; the second reads from an encoder in a '
                   'while-loop with a break, the first calls a progress callback.'),
    dict(id='CL18', cpd=[], symilar=False, ast=True,
         regions=[('httpie/output/ui/rich_progress.py', 86, 94, 'StatusDisplay.stop()'),
                  ('httpie/output/ui/rich_progress.py', 132, 141, 'ProgressDisplay.stop()')],
         verdict='true clone', type='Type 3',
         rationale='Stop the widget, then `if time_spent: self._print_summary(...)`; the second unpacks the '
                   'task and passes different arguments, the first prints the description.'),
    dict(id='CL19', cpd=[], symilar=False, ast=True,
         regions=[('httpie/cli/argparser.py', 382, 389, 'HTTPieArgumentParser._body_from_file()'),
                  ('httpie/cli/argparser.py', 391, 397, 'HTTPieArgumentParser._body_from_input()')],
         verdict='true clone', type='Type 3',
         rationale='Both check _ensure_one_data_source(...) then assign self.args.data; argument list and '
                   'conversion differ.'),
    # ----- Type 4: found only by the manual semantic audit (no Track A tool reports them)
    dict(id='CL20', cpd=[], symilar=False, ast=False,
         regions=[('httpie/uploads.py', 65, 69, 'as_bytes()'),
                  ('httpie/models.py', 163, 169, 'HTTPRequest.body'),
                  ('httpie/uploads.py', 257, 262, 'compress_request() - body to bytes'),
                  ('httpie/client.py', 201, 203, 'finalize_headers() - header value to bytes')],
         verdict='true clone', type='Type 4',
         rationale='The same responsibility, "coerce str to bytes (UTF-8)", is re-implemented four times with '
                   'different syntax although uploads.as_bytes() exists (compress_request in the same module '
                   'does not use it).'),
    dict(id='CL21', cpd=[], symilar=False, ast=False,
         regions=[('httpie/output/formatters/colors.py', 180, 187, 'get_lexer() - JSON sniffing'),
                  ('httpie/output/formatters/json.py', 18, 24, 'JSONFormatter.format_body() - JSON parsing')],
         verdict='true clone', type='Type 4',
         rationale='"Is this body JSON?" decided twice: json.loads(body) in the colour formatter, '
                   'load_prefixed_json(body) in the JSON formatter; the developers flag it '
                   '(`# FIXME: the body also gets parsed in json.py`).'),
    dict(id='CL22', cpd=[], symilar=False, ast=False,
         regions=[('httpie/config.py', 65, 77, 'read_raw_config()'),
                  ('httpie/internal/update_warnings.py', 31, 37, '_read_data_error_free()')],
         verdict='true clone', type='Type 4',
         rationale='Both "open a JSON file and json.load it, tolerating a missing/broken file"; they differ '
                   'only in error policy (raise ConfigFileError vs return {}). Partial semantic clone.'),
]

# Verdicts for AST-scanner pairs that are NOT true clones (by function-name pair).
AST_FP_REASON = {
    ('KeyValueArg.__init__', 'NestedJSONSyntaxError.__init__'): 'attribute-assignment constructor idiom',
    ('ParserSpec.serialize', 'Group.serialize'): 'to-dict serialisation idiom (different fields)',
    ('HTTPieHelpFormatter.__init__', 'HTTPieHTTPSAdapter.init_poolmanager'): 'kwargs injection + super() idiom',
    ('HTTPieHelpFormatter.__init__', 'HTTPieHTTPSAdapter.proxy_manager_for'): 'kwargs injection + super() idiom',
    ('_GenericColorCaster._translate', 'as_bytes'): 'isinstance-then-convert idiom',
    ('ChunkedUploadStream.__init__', 'ChunkedMultipartUploadStream.__init__'): 'attribute-assignment constructor idiom',
    ('ParserSpec.add_group', 'EncodedStream.decode_chunk'): 'create/append/return idiom',
    ('HTTPMessage.content_type', 'HTTPRequest.body'): 'opposite conversions (decode vs encode)',
    ('NestedJSONSyntaxError.__init__', 'ChunkedUploadStream.__init__'): 'attribute-assignment constructor idiom',
    ('parser_to_parser_spec', 'cli_upgrade_session'): 'single keyword-argument call wrapper',
    ('NestedJSONSyntaxError.__init__', 'Path.__init__'): 'attribute-assignment constructor idiom',
    ('json_dict_to_request_body', 'as_bytes'): 'if/else value-conversion idiom',
    ('KeyValueArg.__init__', 'ChunkedUploadStream.__init__'): 'attribute-assignment constructor idiom',
    ('cli_upgrade_session', 'display_for'): 'single keyword-argument call wrapper',
    ('DigestAuthPlugin.get_auth', 'session_hostname_to_dirname'): 'single-call wrapper',
    ('KeyValueArg.__init__', 'BaseStream.__init__'): 'attribute-assignment constructor idiom',
    ('EncodedStream.decode_chunk', '_GenericColorCaster._translate'): 'short helper, coincidental shape',
    ('Session.pre_process_data', 'Session.post_process_data'): 'inverse operations (import vs export loop)',
    ('response_charset_type', 'load_json'): 'try / except -> raise validation idiom',
    ('Formatting.format_body', 'DigestAuthPlugin.get_auth'): 'short helper, coincidental shape',
    ('BaseStream.__init__', 'ChunkedUploadStream.__init__'): 'attribute-assignment constructor idiom',
    ('_GenericColorCaster._translate', 'unwrap_context'): 'isinstance if/else idiom',
    ('NestedJSONSyntaxError.__init__', 'BaseStream.__init__'): 'attribute-assignment constructor idiom',
    ('Path.__init__', 'BaseStream.__init__'): 'attribute-assignment constructor idiom',
    ('ColorFormatter.format_headers', 'ColorFormatter.get_lexer_for_body'): 'single keyword-argument call wrapper',
    ('ColorFormatter.format_metadata', 'ColorFormatter.get_lexer_for_body'): 'single keyword-argument call wrapper',
    ('KeyValueArgType.__init__', 'HTTPHeadersDict.remove_item'): 'short loop, coincidental shape',
    ('as_bytes', 'unwrap_context'): 'isinstance if/else idiom',
    ('ParserSpec.add_group', 'Group.add_argument'): 'create/append/return idiom',
    ('cli_check_updates', 'cli_upgrade_session'): 'short command handler, coincidental shape',
    ('PluginInstaller.__init__', 'ChunkedUploadStream.__init__'): 'attribute-assignment constructor idiom',
    ('NestedJSONSyntaxError.__init__', 'PluginInstaller.__init__'): 'attribute-assignment constructor idiom',
    ('ParserSpec.add_group', '_GenericColorCaster._translate'): 'short helper, coincidental shape',
    ('cached_property.__set_name__', 'DownloadStatus.started'): 'attribute-assignment sequence, coincidental',
    ('NestedJSONSyntaxError.__init__', 'StatusDisplay.start'): 'attribute-assignment sequence, coincidental',
    ('LazyChoices.load', 'LazyChoices.help'): 'lazy-cache property idiom',
    ('get_filename_max_length', 'Formatting.format_body'): 'short helper, coincidental shape',
}
AST_TRUE = {  # function-name pair -> clone id
    ('ColorFormatter.format_headers', 'ColorFormatter.format_metadata'): 'CL15',
    ('HTTPieHTTPSAdapter.init_poolmanager', 'HTTPieHTTPSAdapter.proxy_manager_for'): 'CL16',
    ('HeadersFormatter.__init__', 'JSONFormatter.__init__'): 'CL06',
    ('HeadersFormatter.__init__', 'XMLFormatter.__init__'): 'CL06',
    ('JSONFormatter.__init__', 'XMLFormatter.__init__'): 'CL06',
    ('post_process', 'post_process'): 'CL12',
    ('pre_process', 'pre_process'): 'CL13',
    ('HTTPieArgumentParser._body_from_file', 'HTTPieArgumentParser._body_from_input'): 'CL19',
    ('ChunkedUploadStream.__iter__', 'ChunkedMultipartUploadStream.__iter__'): 'CL17',
    ('StatusDisplay.stop', 'ProgressDisplay.stop'): 'CL18',
}

SKIP = {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
        tokenize.DEDENT, tokenize.ENDMARKER, tokenize.ENCODING}
FSTART = getattr(tokenize, 'FSTRING_START', None)
FEND = getattr(tokenize, 'FSTRING_END', None)
FPARTS = {t for t in (FSTART, FEND, getattr(tokenize, 'FSTRING_MIDDLE', None)) if t is not None}
_tok_cache = {}


def tokens_of(path):
    if path not in _tok_cache:
        text = Path(path).read_text(encoding='utf-8')
        out, depth = [], 0
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type in SKIP:
                continue
            if tok.type in FPARTS or depth:
                if tok.type == FSTART:
                    if depth == 0:
                        out.append((tok.start[0], '<fstring>', 'LIT'))
                    depth += 1
                elif tok.type == FEND:
                    depth -= 1
                continue
            if tok.type == tokenize.NAME:
                blind = tok.string if (keyword.iskeyword(tok.string) or tok.string in ('self', 'cls')) else 'ID'
            elif tok.type in (tokenize.NUMBER, tokenize.STRING):
                blind = 'LIT'
            else:
                blind = tok.string
            out.append((tok.start[0], tok.string, blind))
        _tok_cache[path] = out
    return _tok_cache[path]


def region(path, lo, hi):
    seg = [t for t in tokens_of(path) if lo <= t[0] <= hi]
    return [t[1] for t in seg], [t[2] for t in seg]


def suggested(raw_id, blind_id, blind_sim):
    if raw_id:
        return 'Type 1'
    if blind_id:
        return 'Type 2'
    if blind_sim >= 0.70:
        return 'Type 3'
    return 'no syntactic similarity'


# --------------------------------------------------------------- pair metrics
pair_rows, master_rows = [], []
for c in CLONES:
    regs = c['regions']
    base_raw, base_blind = region(*regs[0][:3])
    sims = []
    for r in regs[1:]:
        raw, blind = region(*r[:3])
        rs = SequenceMatcher(None, base_raw, raw, autojunk=False).ratio()
        bsm = SequenceMatcher(None, base_blind, blind, autojunk=False)
        bs = bsm.ratio()
        matched = sum(b.size for b in bsm.get_matching_blocks())
        sug = suggested(base_raw == raw, base_blind == blind, bs)
        sims.append((rs, bs, sug, matched))
        pair_rows.append({
            'clone_id': c['id'],
            'occurrence_a': f'{regs[0][0]}:{regs[0][1]}-{regs[0][2]}',
            'occurrence_b': f'{r[0]}:{r[1]}-{r[2]}',
            'tokens_a': len(base_raw), 'tokens_b': len(raw),
            'raw_identical': base_raw == raw, 'blind_identical': base_blind == blind,
            'raw_similarity': round(rs, 3), 'blind_similarity': round(bs, 3),
            'matched_blind_tokens': matched,
            'metric_suggested_type': sug,
        })
    sug_types = sorted({s[2] for s in sims})
    manual = c['type']
    if c['verdict'] == 'false positive':
        agree = 'n/a (false positive)'
    elif manual == 'Type 4':
        agree = 'yes' if sug_types == ['no syntactic similarity'] else f'partial ({", ".join(sug_types)})'
    else:
        agree = 'yes' if sug_types == [manual] else f'no ({", ".join(sug_types)})'
    detectors = []
    if c['cpd']:
        detectors.append('CPD')
    if c['symilar']:
        detectors.append('symilar')
    if c['ast']:
        detectors.append('AST scan')
    master_rows.append({
        'id': c['id'],
        'locations': '; '.join(f'{r[0]}:{r[1]}-{r[2]}' for r in regs),
        'units': '; '.join(r[3] for r in regs),
        'occurrences': len(regs),
        'files': len({r[0] for r in regs}),
        'lines_per_occurrence': '/'.join(str(r[2] - r[1] + 1) for r in regs),
        'py_tokens_per_occurrence': '/'.join(str(len(region(*r[:3])[0])) for r in regs),
        # tokens the copies really share (normalised matching blocks), summed over pairs
        'duplicated_tokens': sum(s[3] for s in sims),
        'cpd_groups': ' + '.join(c['cpd']) or '-',
        'track_a_detectors': ', '.join(detectors) or 'none (manual semantic audit)',
        'verdict': c['verdict'],
        'type': manual,
        'fp_kind': c.get('fp_kind', ''),
        'min_raw_similarity': round(min(s[0] for s in sims), 3),
        'min_blind_similarity': round(min(s[1] for s in sims), 3),
        'metric_suggested_type': ', '.join(sug_types),
        'manual_vs_metric_agree': agree,
        'rationale': c['rationale'],
    })

# attach CPD token / line size and max threshold from the Task 1 inventory
inv = {r['id']: r for r in csv.DictReader(open(CPD_INVENTORY, encoding='utf-8'))}

# consistency guard: every CPD group is used exactly once, and every occurrence
# of a cited CPD group overlaps one of the clone's audited regions
cited = [g for c in CLONES for g in c['cpd']]
cpd_ids = sorted(k for k, v in inv.items() if v['source'] == 'CPD')
assert sorted(cited) == cpd_ids, f'CPD groups cited {sorted(cited)} != inventory {cpd_ids}'
for c in CLONES:
    for g in c['cpd']:
        for loc_ in inv[g]['locations'].split('; '):
            f, span = loc_.rsplit(':', 1)
            lo, hi = map(int, span.split('-'))
            assert any(f == rf and lo <= rhi and rlo <= hi for rf, rlo, rhi, _ in c['regions']), \
                f'{c["id"]} cites {g} but {loc_} is outside its regions'
print('consistency check passed: all 12 CPD groups mapped to clone regions')
for row, c in zip(master_rows, CLONES):
    if c['cpd']:
        row['cpd_tokens'] = ' + '.join(inv[g]['tokens'] for g in c['cpd'])
        row['cpd_max_threshold'] = max(int(inv[g]['max_threshold_detected']) for g in c['cpd'])
    else:
        row['cpd_tokens'] = '-'
        row['cpd_max_threshold'] = 'not detected'

fields = ['id', 'verdict', 'type', 'fp_kind', 'locations', 'units', 'occurrences', 'files',
          'lines_per_occurrence', 'py_tokens_per_occurrence', 'duplicated_tokens', 'cpd_groups', 'cpd_tokens',
          'cpd_max_threshold', 'track_a_detectors', 'min_raw_similarity', 'min_blind_similarity',
          'metric_suggested_type', 'manual_vs_metric_agree', 'rationale']
with open(OUT / 'clone_classification.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    w.writerows(master_rows)
with open(OUT / 'pair_metrics.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(pair_rows[0]))
    w.writeheader()
    w.writerows(pair_rows)

# ------------------------------------------------- adjudicate AST scanner pairs
def short(unit):
    return unit.split(' ', 1)[1].rstrip('()')


ast_rows, unmatched = [], []
for p in csv.DictReader(open(AST_PAIRS, encoding='utf-8')):
    key = (short(p['unit_a']), short(p['unit_b']))
    if key in AST_TRUE:
        p['verdict'], p['clone_id'], p['reason'] = 'true clone', AST_TRUE[key], ''
    elif key in AST_FP_REASON:
        p['verdict'], p['clone_id'], p['reason'] = 'false positive', '', AST_FP_REASON[key]
    else:
        p['verdict'], p['clone_id'], p['reason'] = 'UNREVIEWED', '', ''
        unmatched.append(key)
    ast_rows.append(p)
with open(OUT / 'ast_pairs_adjudicated.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(ast_rows[0]))
    w.writeheader()
    w.writerows(ast_rows)
assert not unmatched, f'unreviewed AST pairs: {unmatched}'

# ------------------------------------------------------- detector precision
lines = []
cpd_true = sum(len(c['cpd']) for c in CLONES if c['cpd'] and c['verdict'] == 'true clone')
cpd_all = sum(len(c['cpd']) for c in CLONES if c['cpd'])
lines.append(f'CPD --minimum-tokens 25 : {cpd_true}/{cpd_all} groups are true clones '
             f'-> precision {100 * cpd_true / cpd_all:.0f} %')
for thr in (35, 50):
    g = [r for r in master_rows if r['cpd_max_threshold'] != 'not detected' and int(r['cpd_max_threshold']) >= thr]
    t = [r for r in g if r['verdict'] == 'true clone']
    lines.append(f'CPD --minimum-tokens {thr} : {len(t)}/{len(g)} clones true '
                 f'(clone ids: {", ".join(r["id"] for r in g)})')
sym = [c for c in CLONES if c['symilar']]
lines.append(f'symilar -d 3            : {sum(c["verdict"] == "true clone" for c in sym)}/{len(sym)} pairs true')


def prec(rows, cond):
    sel = [r for r in rows if cond(r)]
    tp = sum(r['verdict'] == 'true clone' for r in sel)
    return tp, len(sel)


for label, cond in [
    ('AST scan blind>=0.75            ', lambda r: True),
    ('AST scan blind>=0.75 & raw>=0.60', lambda r: float(r['raw_similarity']) >= 0.60),
    ('AST scan blind>=0.90            ', lambda r: float(r['blind_similarity']) >= 0.90),
]:
    tp, n = prec(ast_rows, cond)
    lines.append(f'{label}: {tp}/{n} pairs true -> precision {100 * tp / n:.0f} %')
true_ast_ids = {r['clone_id'] for r in ast_rows if r['verdict'] == 'true clone'}
lost = {r['clone_id'] for r in ast_rows if r['verdict'] == 'true clone' and float(r['raw_similarity']) < 0.60}
lines.append(f'AST scan true clone ids: {", ".join(sorted(true_ast_ids))}; '
             f'lost by raw>=0.60 filter: {", ".join(sorted(lost)) or "none"}')

true_clones = [c for c in CLONES if c['verdict'] == 'true clone']
by_type = defaultdict(list)
for c in true_clones:
    by_type[c['type']].append(c['id'])
lines.append('')
lines.append(f'Confirmed true clones: {len(true_clones)}  |  false positives: {len(CLONES) - len(true_clones)}')
for t in sorted(by_type):
    lines.append(f'  {t}: {len(by_type[t])}  ({", ".join(by_type[t])})')
lines.append('')
lines.append('Recall of each Track A tool over the confirmed true clones (union = reference set):')
for tool, test in [('CPD (t=25)', lambda c: bool(c['cpd'])), ('symilar (d=3)', lambda c: c['symilar']),
                   ('AST scan', lambda c: c['ast']),
                   ('any Track A tool', lambda c: bool(c['cpd']) or c['symilar'] or c['ast'])]:
    hit = [c['id'] for c in true_clones if test(c)]
    lines.append(f'  {tool:<17}: {len(hit)}/{len(true_clones)}')
for t in ('Type 1', 'Type 2', 'Type 3', 'Type 4'):
    ids = [c for c in true_clones if c['type'] == t]
    cpd_hit = sum(bool(c['cpd']) for c in ids)
    any_hit = sum(bool(c['cpd']) or c['symilar'] or c['ast'] for c in ids)
    lines.append(f'  {t}: CPD {cpd_hit}/{len(ids)}, any Track A tool {any_hit}/{len(ids)}')
(OUT / 'detector_precision.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('\n'.join(lines))

# ----------------------------------------- hotspots recomputed on true clones
loc = {r['file']: int(r['code_loc']) for r in csv.DictReader(open(LOC_FILES, encoding='utf-8'))}
covered, ids_in_file = defaultdict(set), defaultdict(set)
for c in true_clones:
    for f, lo, hi, _ in c['regions']:
        covered[f].update(range(lo, hi + 1))
        ids_in_file[f].add(c['id'])
hot = sorted(({'file': f, 'code_loc': loc[f], 'true_clones': len(ids_in_file[f]),
               'clone_ids': ' '.join(sorted(ids_in_file[f])), 'cloned_lines': len(covered[f]),
               'clone_density_pct': round(100 * len(covered[f]) / loc[f], 2)}
              for f in covered), key=lambda r: (-r['true_clones'], -r['cloned_lines']))
with open(OUT / 'hotspots_confirmed.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(hot[0]))
    w.writeheader()
    w.writerows(hot)
print('\nConfirmed-clone hotspots:')
for r in hot[:10]:
    print(f"  {r['file']:<52} {r['true_clones']} clones ({r['clone_ids']}), "
          f"{r['cloned_lines']} lines, {r['clone_density_pct']} %")
print(f'\ncovered lines total: {sum(len(v) for v in covered.values())} '
      f'of {sum(loc.values())} code lines '
      f'({100 * sum(len(v) for v in covered.values()) / sum(loc.values()):.2f} %)')
