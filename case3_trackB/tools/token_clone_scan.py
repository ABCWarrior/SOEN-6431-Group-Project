"""
CPD-style token clone scanner used by Track B (Claude Code) as a
deterministic cross-check of AI-reported clones.

It mimics PMD CPD's core algorithm (Rabin-Karp style window hashing over a
token stream, then maximal forward extension) using Python's `tokenize`.
It is NOT PMD/CPD: Track A's official CPD numbers take precedence.

Usage:
    python token_clone_scan.py <src_dir> [--min-tokens 50] [--ignore-ids]
    python token_clone_scan.py <src_dir> --fragments fragments.json

Token rules (close to CPD's Python lexer):
  * comments, NL/NEWLINE, INDENT/DEDENT, ENCODING, ENDMARKER are dropped
  * --ignore-ids replaces non-keyword NAMEs with ID, strings with STR,
    numbers with NUM (equivalent to CPD --ignore-identifiers --ignore-literals)
"""
import argparse
import io
import json
import keyword
import sys
import tokenize
from collections import defaultdict
from pathlib import Path

SKIP = {
    tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
    tokenize.DEDENT, tokenize.ENCODING, tokenize.ENDMARKER,
}


def lex(path: Path, ignore_ids: bool):
    """Return a list of (normalised_text, line) tokens for one file."""
    out = []
    src = path.read_bytes()
    for tok in tokenize.tokenize(io.BytesIO(src).readline):
        if tok.type in SKIP:
            continue
        text = tok.string
        if ignore_ids:
            if tok.type == tokenize.NAME and not keyword.iskeyword(text):
                text = 'ID'
            elif tok.type == tokenize.STRING:
                text = 'STR'
            elif tok.type == tokenize.NUMBER:
                text = 'NUM'
        out.append((text, tok.start[0]))
    return out


def scan(src_dir: Path, min_tokens: int, ignore_ids: bool):
    files = sorted(p for p in src_dir.rglob('*.py'))
    streams = {f: lex(f, ignore_ids) for f in files}

    # Global token array with per-file sentinels so matches never cross files.
    toks, where = [], []
    for f, stream in streams.items():
        for i, (t, line) in enumerate(stream):
            toks.append(t)
            where.append((f, line))
        toks.append(f'<EOF:{f}>')
        where.append((f, -1))

    buckets = defaultdict(list)
    for i in range(len(toks) - min_tokens + 1):
        window = tuple(toks[i:i + min_tokens])
        if any(t.startswith('<EOF:') for t in window):
            continue
        buckets[hash(window)].append(i)

    matches = []
    seen = set()
    for positions in buckets.values():
        if len(positions) < 2:
            continue
        for a_idx, p in enumerate(positions):
            for q in positions[a_idx + 1:]:
                if q < p + min_tokens:  # overlapping self-match
                    continue
                # only start at maximal left edge
                if p > 0 and toks[p - 1] == toks[q - 1] and not toks[p - 1].startswith('<EOF'):
                    continue
                n = 0
                while (q + n < len(toks) and p + n < q
                       and toks[p + n] == toks[q + n]
                       and not toks[p + n].startswith('<EOF')):
                    n += 1
                if n < min_tokens:
                    continue
                key = (p, q)
                if key in seen:
                    continue
                seen.add(key)
                fa, la1 = where[p]
                _, la2 = where[p + n - 1]
                fb, lb1 = where[q]
                _, lb2 = where[q + n - 1]
                matches.append({
                    'tokens': n,
                    'a': f'{fa.relative_to(src_dir.parent)}:{la1}-{la2}',
                    'b': f'{fb.relative_to(src_dir.parent)}:{lb1}-{lb2}',
                    'lines': max(la2 - la1, lb2 - lb1) + 1,
                })
    matches.sort(key=lambda m: -m['tokens'])
    total_tokens = sum(len(s) for s in streams.values())
    return matches, len(files), total_tokens


def count_fragment_tokens(path: Path, start: int, end: int) -> int:
    return sum(1 for _, line in lex(path, False) if start <= line <= end)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src_dir', type=Path)
    ap.add_argument('--min-tokens', type=int, default=50)
    ap.add_argument('--ignore-ids', action='store_true')
    ap.add_argument('--fragments', type=Path,
                    help='JSON list of {"id","file","start","end"} to measure')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()

    if a.fragments:
        frags = json.loads(a.fragments.read_text())
        root = a.src_dir.parent
        for fr in frags:
            fr['tokens'] = count_fragment_tokens(root / fr['file'], fr['start'], fr['end'])
            fr['loc'] = fr['end'] - fr['start'] + 1
            print(f"{fr['id']:<6} {fr['file']}:{fr['start']}-{fr['end']:<6}"
                  f" tokens={fr['tokens']:<5} lines={fr['loc']}")
        return

    matches, n_files, n_tokens = scan(a.src_dir, a.min_tokens, a.ignore_ids)
    mode = 'ignore-ids+literals' if a.ignore_ids else 'exact'
    if a.json:
        json.dump({'min_tokens': a.min_tokens, 'mode': mode, 'files': n_files,
                   'total_tokens': n_tokens, 'matches': matches}, sys.stdout, indent=2)
        return
    print(f'# token_clone_scan  min_tokens={a.min_tokens}  mode={mode}  '
          f'files={n_files}  tokens={n_tokens}  duplications={len(matches)}')
    for m in matches:
        print(f"{m['tokens']:>5} tokens  {m['lines']:>3} lines  {m['a']}  <->  {m['b']}")


if __name__ == '__main__':
    main()
