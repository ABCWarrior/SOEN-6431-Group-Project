"""Task 1 - Clone inventory & hotspot identification (Track A, deterministic).

Inputs : PMD CPD XML reports for one source tree at several --minimum-tokens
         thresholds, plus pylint `symilar` text reports.
Outputs: clone_inventory.csv / .md   (one row per clone group)
         hotspots_files.csv, hotspots_packages.csv / hotspots.md
         loc_summary.txt

Only the Python standard library is used (xml.etree, ast, tokenize, csv).

Usage:
    python track_a/scripts/clone_inventory.py <src_dir> <cpd_dir> <prefix> <symilar_report> <out_dir>
    e.g. python track_a/scripts/clone_inventory.py httpie track_a/task1/cpd httpie \
             track_a/task1/symilar/httpie_symilar_d3.txt track_a/task1
"""
import ast
import csv
import io
import re
import sys
import tokenize
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {'c': 'https://pmd-code.org/schema/cpd-report'}
THRESHOLDS = [25, 35, 50, 75, 100]

src_dir, cpd_dir, prefix, symilar_report, out_dir = sys.argv[1:6]
ROOT = Path.cwd()
out = Path(out_dir)


def rel(p: str) -> str:
    return Path(p).resolve().relative_to(ROOT).as_posix()


# ---------------------------------------------------------------- LOC metrics
def loc_metrics(path: Path):
    """physical, blank, comment-only and code lines (docstrings count as code,
    as they are executable string statements)."""
    text = path.read_text(encoding='utf-8')
    lines = text.splitlines()
    code_lines, comment_lines = set(), set()
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type == tokenize.COMMENT:
            comment_lines.add(tok.start[0])
        elif tok.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
                              tokenize.DEDENT, tokenize.ENDMARKER):
            code_lines.update(range(tok.start[0], tok.end[0] + 1))
    blank = sum(1 for l in lines if not l.strip())
    return {
        'physical': len(lines),
        'blank': blank,
        'comment': len(comment_lines - code_lines),
        'code': len(code_lines),
    }


files = sorted(p for p in Path(src_dir).rglob('*.py'))
loc = {p.as_posix(): loc_metrics(p) for p in files}


# ------------------------------------------------- enclosing unit (via ast)
_units = {}


def units_of(path: str):
    if path not in _units:
        tree = ast.parse(Path(path).read_text(encoding='utf-8'))
        found = []

        def visit(node, qual):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    name = f'{qual}.{child.name}' if qual else child.name
                    found.append((child.lineno, child.end_lineno, name,
                                  'class' if isinstance(child, ast.ClassDef) else 'def'))
                    visit(child, name)
                else:
                    visit(child, qual)
        visit(tree, '')
        _units[path] = found
    return _units[path]


def enclosing(path: str, begin: int, end: int) -> str:
    best = None
    for lo, hi, name, kind in units_of(path):
        if lo <= begin and end <= hi and (best is None or hi - lo < best[1] - best[0]):
            best = (lo, hi, name, kind)
    if best is None:
        # range spans several units (or module level): list the units it touches
        touched = [n for lo, hi, n, k in units_of(path) if lo <= end and begin <= hi and k == 'def']
        return 'module level' if not touched else 'spans: ' + ', '.join(touched)
    return f'{best[2]}()' if best[3] == 'def' else f'class {best[2]}'


# ------------------------------------------------------------- parse CPD XML
def parse_cpd(xml_path: Path):
    root = ET.parse(xml_path).getroot()
    groups = []
    for dup in root.findall('c:duplication', NS):
        occ = []
        for f in dup.findall('c:file', NS):
            occ.append({
                'file': rel(f.get('path')),
                'begin': int(f.get('line')),
                'end': int(f.get('endline')),
            })
        frag = dup.find('c:codefragment', NS).text or ''
        groups.append({
            'lines': int(dup.get('lines')),
            'tokens': int(dup.get('tokens')),
            'occ': sorted(occ, key=lambda o: (o['file'], o['begin'])),
            'fragment': frag,
        })
    tokens_per_file = {rel(f.get('path')): int(f.get('totalNumberOfTokens'))
                       for f in root.findall('c:file', NS)}
    return groups, tokens_per_file


runs = {t: parse_cpd(Path(cpd_dir) / f'{prefix}_t{t}.xml') for t in THRESHOLDS}
base_groups, tokens_per_file = runs[THRESHOLDS[0]]
total_tokens = sum(tokens_per_file.values())


def key(g):
    return tuple((o['file'], o['begin']) for o in g['occ'])


def overlaps(a, b):
    """same files and overlapping line ranges for every occurrence"""
    if len(a['occ']) != len(b['occ']):
        return False
    return all(x['file'] == y['file'] and x['begin'] <= y['end'] and y['begin'] <= x['end']
               for x, y in zip(a['occ'], b['occ']))


inventory = []
for g in sorted(base_groups, key=lambda g: (-g['tokens'], -g['lines'])):
    detected_at = [t for t in THRESHOLDS if any(overlaps(g, h) for h in runs[t][0])]
    files_affected = sorted({o['file'] for o in g['occ']})
    inventory.append({
        'source': 'CPD',
        'tokens': g['tokens'],
        'lines': g['lines'],
        'occurrences': len(g['occ']),
        'files_affected': len(files_affected),
        'scope': 'cross-file' if len(files_affected) > 1 else 'intra-file',
        'duplicated_lines': g['lines'] * (len(g['occ']) - 1),
        'max_threshold_detected': max(detected_at),
        'locations': '; '.join(f"{o['file']}:{o['begin']}-{o['end']}" for o in g['occ']),
        'enclosing_units': '; '.join(enclosing(o['file'], o['begin'], o['end']) for o in g['occ']),
        'first_line': next((l.strip() for l in g['fragment'].splitlines() if l.strip()), ''),
        'occ': g['occ'],
    })

# ---------------------------------------------------- symilar (line-based)
sym_text = Path(symilar_report).read_text(encoding='utf-8', errors='replace')
for m in re.finditer(r'(\d+) similar lines in (\d+) files\n((?:==.*\n)+)', sym_text):
    n_lines = int(m.group(1))
    occ = []
    for loc_m in re.finditer(r'==(.+?):\[(\d+):(\d+)\]', m.group(3)):
        # symilar reports 0-based [start:end) indices of *stripped* lines;
        # we keep its notation and resolve the real line span by matching text.
        occ.append({'file': loc_m.group(1), 'sym_range': f'[{loc_m.group(2)}:{loc_m.group(3)}]'})
    inventory.append({
        'source': 'symilar',
        'tokens': '',
        'lines': n_lines,
        'occurrences': len(occ),
        'files_affected': len({o['file'] for o in occ}),
        'scope': 'cross-file',
        'duplicated_lines': n_lines * (len(occ) - 1),
        'max_threshold_detected': '',
        'locations': '; '.join(f"{o['file']} {o['sym_range']}" for o in occ),
        'enclosing_units': '',
        'first_line': '',
        'occ': [],
    })

for i, row in enumerate(inventory, 1):
    row['id'] = f'{"CG" if row["source"] == "CPD" else "SG"}{i:02d}'

fields = ['id', 'source', 'tokens', 'lines', 'occurrences', 'files_affected', 'scope',
          'duplicated_lines', 'max_threshold_detected', 'locations', 'enclosing_units', 'first_line']
with open(out / 'clone_inventory.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=fields, extrasaction='ignore')
    w.writeheader()
    w.writerows(inventory)

# --------------------------------------------------------------- hotspots
covered = defaultdict(set)          # file -> set of line numbers inside a clone
groups_in_file = defaultdict(set)   # file -> clone ids
for row in inventory:
    for o in row['occ']:
        covered[o['file']].update(range(o['begin'], o['end'] + 1))
        groups_in_file[o['file']].add(row['id'])

file_rows = []
for f, m in loc.items():
    cov = len(covered.get(f, ()))
    file_rows.append({
        'file': f, 'code_loc': m['code'], 'physical_loc': m['physical'],
        'cpd_tokens': tokens_per_file.get(f, 0),
        'clone_groups': len(groups_in_file.get(f, ())),
        'cloned_lines': cov,
        'clone_density_pct': round(100 * cov / m['code'], 2) if m['code'] else 0.0,
    })
file_rows.sort(key=lambda r: (-r['cloned_lines'], -r['clone_density_pct']))
with open(out / 'hotspots_files.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(file_rows[0]))
    w.writeheader()
    w.writerows(file_rows)


def package_of(f):
    parts = Path(f).parts
    return '/'.join(parts[:2]) if len(parts) > 2 else parts[0] + ' (top-level modules)'


pkg = defaultdict(lambda: {'files': 0, 'code_loc': 0, 'cloned_lines': 0, 'clone_groups': set()})
for r in file_rows:
    p = pkg[package_of(r['file'])]
    p['files'] += 1
    p['code_loc'] += r['code_loc']
    p['cloned_lines'] += r['cloned_lines']
    p['clone_groups'] |= groups_in_file.get(r['file'], set())
pkg_rows = sorted(({
    'package': k, 'files': v['files'], 'code_loc': v['code_loc'],
    'clone_groups': len(v['clone_groups']), 'cloned_lines': v['cloned_lines'],
    'clone_density_pct': round(100 * v['cloned_lines'] / v['code_loc'], 2) if v['code_loc'] else 0.0,
} for k, v in pkg.items()), key=lambda r: (-r['cloned_lines'], r['package']))
with open(out / 'hotspots_packages.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(pkg_rows[0]))
    w.writeheader()
    w.writerows(pkg_rows)

# ------------------------------------------------------------ text summary
tot = {k: sum(m[k] for m in loc.values()) for k in ('physical', 'blank', 'comment', 'code')}
all_cov = sum(len(v) for v in covered.values())
with open(out / 'loc_summary.txt', 'w', encoding='utf-8') as fh:
    fh.write(f'Source tree: {src_dir}/  ({len(loc)} .py files)\n')
    for k, v in tot.items():
        fh.write(f'{k:>9} lines: {v}\n')
    fh.write(f'CPD tokens (all files): {total_tokens}\n')
    for t in THRESHOLDS:
        g = runs[t][0]
        fh.write(f'CPD --minimum-tokens {t:>3}: {len(g):>2} clone groups, '
                 f'{sum(x["lines"] * (len(x["occ"]) - 1) for x in g)} duplicated lines\n')
    fh.write(f'Lines covered by CPD(t=25) clone occurrences: {all_cov} '
             f'({100 * all_cov / tot["code"]:.2f} % of code lines)\n')
print((out / 'loc_summary.txt').read_text(encoding='utf-8'))
print(f'{len(inventory)} inventory rows -> {out / "clone_inventory.csv"}')
