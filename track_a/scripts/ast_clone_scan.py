"""Function-level AST/token clone metric calculator (Track A, deterministic).

For every function/method in <src_dir> it builds two token sequences with the
standard-library `tokenize` module, using `ast` to find the function boundaries
and the docstring:

  raw   : the real token text           (comments, layout and docstrings dropped)
  blind : identifiers -> ID, literals -> LIT, keywords/operators kept

Every pair of functions is then compared with difflib.SequenceMatcher:

  similarity = 2*M / (len(a)+len(b))   on the *blind* sequences

and reported if similarity >= --min-sim. Indicative type (verified by hand in Task 2):
  raw sequences identical               -> Type 1
  blind identical, raw different        -> Type 2 (renamed identifiers / literals)
  blind similarity < 1                  -> Type 3 (gapped / modified statements)

Usage:
    python track_a/scripts/ast_clone_scan.py <src_dir> <out_csv> [--min-tokens N] [--min-sim S]
"""
import argparse
import ast
import csv
import io
import keyword
import tokenize
from difflib import SequenceMatcher
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('src_dir')
ap.add_argument('out_csv')
ap.add_argument('--min-tokens', type=int, default=30)
ap.add_argument('--min-sim', type=float, default=0.75)
args = ap.parse_args()

SKIP = {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
        tokenize.DEDENT, tokenize.ENDMARKER, tokenize.ENCODING}
FSTRING_PARTS = {getattr(tokenize, n) for n in
                 ('FSTRING_START', 'FSTRING_MIDDLE', 'FSTRING_END') if hasattr(tokenize, n)}


def file_tokens(text):
    """List of (line, raw, blind) tokens; an f-string collapses to one LIT."""
    out, fdepth = [], 0
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type in SKIP:
            continue
        if tok.type in FSTRING_PARTS or fdepth:
            if tok.type == getattr(tokenize, 'FSTRING_START', None):
                if fdepth == 0:
                    out.append((tok.start[0], '<fstring>', 'LIT'))
                fdepth += 1
            elif tok.type == getattr(tokenize, 'FSTRING_END', None):
                fdepth -= 1
            continue
        if tok.type == tokenize.NAME:
            blind = tok.string if (keyword.iskeyword(tok.string) or tok.string in ('self', 'cls')) else 'ID'
        elif tok.type in (tokenize.NUMBER, tokenize.STRING):
            blind = 'LIT'
        else:
            blind = tok.string
        out.append((tok.start[0], tok.string, blind))
    return out


functions = []
for path in sorted(Path(args.src_dir).rglob('*.py')):
    text = path.read_text(encoding='utf-8')
    toks = file_tokens(text)
    tree = ast.parse(text)

    def visit(node, qual):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = f'{qual}.{ch.name}' if qual else ch.name
                lo = min([d.lineno for d in ch.decorator_list] + [ch.lineno])
                hi = ch.end_lineno
                doc = None
                if (ch.body and isinstance(ch.body[0], ast.Expr)
                        and isinstance(ch.body[0].value, ast.Constant)
                        and isinstance(ch.body[0].value.value, str)):
                    doc = (ch.body[0].lineno, ch.body[0].end_lineno)
                seg = [t for t in toks if lo <= t[0] <= hi
                       and not (doc and doc[0] <= t[0] <= doc[1])]
                functions.append({
                    'file': path.as_posix(), 'name': name, 'lo': lo, 'hi': hi,
                    'raw': [t[1] for t in seg], 'blind': [t[2] for t in seg],
                })
                visit(ch, name)
            elif isinstance(ch, ast.ClassDef):
                visit(ch, f'{qual}.{ch.name}' if qual else ch.name)
            else:
                visit(ch, qual)
    visit(tree, '')

cands = [f for f in functions if len(f['blind']) >= args.min_tokens]
print(f'{len(functions)} functions parsed, {len(cands)} with >= {args.min_tokens} tokens; '
      f'{len(cands) * (len(cands) - 1) // 2} pairs compared')

pairs = []
for i, a in enumerate(cands):
    for b in cands[i + 1:]:
        la, lb = len(a['blind']), len(b['blind'])
        if min(la, lb) / max(la, lb) < args.min_sim:      # cannot reach min-sim
            continue
        if a['file'] == b['file'] and (a['lo'] <= b['lo'] <= a['hi'] or b['lo'] <= a['lo'] <= b['hi']):
            continue                                       # nested functions
        sm = SequenceMatcher(None, a['blind'], b['blind'], autojunk=False)
        if sm.real_quick_ratio() < args.min_sim or sm.quick_ratio() < args.min_sim:
            continue
        sim = sm.ratio()
        if sim < args.min_sim:
            continue
        raw_sim = SequenceMatcher(None, a['raw'], b['raw'], autojunk=False).ratio()
        if a['raw'] == b['raw']:
            hint = 'Type 1'
        elif a['blind'] == b['blind']:
            hint = 'Type 2'
        else:
            hint = 'Type 3'
        pairs.append({
            'blind_similarity': round(sim, 3), 'raw_similarity': round(raw_sim, 3),
            'type_hint': hint,
            'tokens_a': la, 'tokens_b': lb,
            'unit_a': f"{a['file']}:{a['lo']}-{a['hi']} {a['name']}()",
            'unit_b': f"{b['file']}:{b['lo']}-{b['hi']} {b['name']}()",
        })

pairs.sort(key=lambda p: (-p['blind_similarity'], -(p['tokens_a'] + p['tokens_b'])))
with open(args.out_csv, 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=['blind_similarity', 'raw_similarity', 'type_hint',
                                       'tokens_a', 'tokens_b', 'unit_a', 'unit_b'])
    w.writeheader()
    w.writerows(pairs)
print(f'{len(pairs)} function pairs with blind similarity >= {args.min_sim} -> {args.out_csv}')
for p in pairs:
    print(f"{p['blind_similarity']:.3f} {p['raw_similarity']:.3f} {p['type_hint']}  "
          f"{p['unit_a']}  <->  {p['unit_b']}")
