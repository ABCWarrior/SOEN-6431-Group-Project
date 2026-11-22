"""Render the Task 1 / Task 2 CSV results as Markdown tables (no manual copying).

Usage: python track_a/scripts/render_tables.py
Writes track_a/task1/tables.md and track_a/task2/tables.md
"""
import csv
import re
from pathlib import Path

T1, T2 = Path('track_a/task1'), Path('track_a/task2')


def rows(p):
    return list(csv.DictReader(open(p, encoding='utf-8')))


def table(headers, data):
    out = ['| ' + ' | '.join(headers) + ' |', '|' + '|'.join('---' for _ in headers) + '|']
    out += ['| ' + ' | '.join(str(c).replace('|', '\\|') for c in r) + ' |' for r in data]
    return '\n'.join(out)


inv = rows(T1 / 'clone_inventory.csv')
cls = rows(T2 / 'clone_classification.csv')
cg_to_cl = {g.strip(): c['id'] for c in cls for g in c['cpd_groups'].split('+') if g.strip() != '-'}
# symilar rows -> clone id by file pair
for r in inv:
    if r['source'] == 'symilar':
        files = sorted(re.findall(r'(httpie/\S+\.py)', r['locations']))
        for c in cls:
            if 'symilar' in c['track_a_detectors'] and sorted(
                    {l.rsplit(':', 1)[0] for l in c['locations'].split('; ')}) == files:
                cg_to_cl[r['id']] = c['id']
verdict = {c['id']: c for c in cls}

# ------------------------------------------------------------------ Task 1
t1 = ['# Task 1 – generated tables', '',
      '## Table 1.1 – Raw Track A detector inventory (CPD `--minimum-tokens 25` + symilar `-d 3`)', '']
data = []
for r in inv:
    cl = cg_to_cl.get(r['id'], '?')
    data.append([r['id'], r['source'], r['tokens'] or '–', r['lines'], r['occurrences'],
                 r['files_affected'], r['scope'], r['max_threshold_detected'] or '–',
                 r['locations'].replace('; ', '<br>'), r['enclosing_units'].replace('; ', '<br>') or '–',
                 f"{cl} ({verdict[cl]['verdict']})" if cl in verdict else cl])
t1.append(table(['Group', 'Tool', 'Tokens', 'Lines', 'Occ.', 'Files', 'Scope', 'Max MTS',
                 'Locations (file:begin-end)', 'Enclosing unit(s)', 'Audited as'], data))

t1 += ['', '## Table 1.2 – Consolidated clone list (all Track A detectors + manual audit), largest first', '']


def total_tokens(c):
    return sum(int(x) for x in c['py_tokens_per_occurrence'].split('/'))


true = sorted([c for c in cls if c['verdict'] == 'true clone'], key=lambda c: (-int(c['duplicated_tokens']), -total_tokens(c)))
data = [[i, c['id'], c['locations'].replace('; ', '<br>'), c['lines_per_occurrence'],
         c['py_tokens_per_occurrence'], c['duplicated_tokens'], c['cpd_tokens'], c['occurrences'], c['files'],
         c['track_a_detectors'], c['type']] for i, c in enumerate(true, 1)]
t1.append(table(['Rank', 'ID', 'Locations', 'Lines / occ.', 'Py tokens / occ.', 'Shared tokens', 'CPD tokens',
                 'Occ.', 'Files', 'Found by', 'Type'], data))

t1 += ['', '## Table 1.3 – File hotspots, raw CPD view (t=25, before false-positive removal)', '']
hf = [r for r in rows(T1 / 'hotspots_files.csv') if int(r['clone_groups']) > 0]
t1.append(table(['File', 'Code LOC', 'CPD groups', 'Cloned lines', 'Clone density %'],
                [[r['file'], r['code_loc'], r['clone_groups'], r['cloned_lines'], r['clone_density_pct']] for r in hf]))

t1 += ['', '## Table 1.4 – File hotspots, confirmed clones only (after Task 2 audit, Types 1–4)', '']
hc = rows(T2 / 'hotspots_confirmed.csv')
t1.append(table(['File', 'Code LOC', 'True clones', 'Clone IDs', 'Cloned lines', 'Clone density %'],
                [[r['file'], r['code_loc'], r['true_clones'], r['clone_ids'], r['cloned_lines'],
                  r['clone_density_pct']] for r in hc]))

t1 += ['', '## Table 1.5 – Package hotspots, raw CPD view (t=25)', '']
hp = rows(T1 / 'hotspots_packages.csv')
t1.append(table(['Package', 'Files', 'Code LOC', 'CPD groups', 'Cloned lines', 'Density %'],
                [[r['package'], r['files'], r['code_loc'], r['clone_groups'], r['cloned_lines'],
                  r['clone_density_pct']] for r in hp]))
(T1 / 'tables.md').write_text('\n'.join(t1) + '\n', encoding='utf-8')

# ------------------------------------------------------------------ Task 2
t2 = ['# Task 2 – generated tables', '', '## Table 2.1 – Classification of every Track A clone', '']
data = [[c['id'], c['verdict'], c['type'] if c['verdict'] == 'true clone' else f"FP: {c['fp_kind']}",
         c['locations'].replace('; ', '<br>'), c['cpd_tokens'], c['track_a_detectors'],
         c['min_raw_similarity'], c['min_blind_similarity'], c['metric_suggested_type'],
         c['manual_vs_metric_agree'], c['rationale']] for c in cls]
t2.append(table(['ID', 'Verdict', 'Type', 'Locations', 'CPD tokens', 'Track A detector(s)',
                 'Raw sim.', 'Blind sim.', 'Metric-suggested', 'Agrees', 'Rationale'], data))
t2 += ['', '## Table 2.2 – Pair metrics (first occurrence vs each other occurrence)', '']
pm = rows(T2 / 'pair_metrics.csv')
t2.append(table(['Clone', 'Occurrence A', 'Occurrence B', 'Tokens A/B', 'Raw ident.', 'Blind ident.',
                 'Raw sim.', 'Blind sim.', 'Suggested'],
                [[r['clone_id'], r['occurrence_a'], r['occurrence_b'], f"{r['tokens_a']}/{r['tokens_b']}",
                  r['raw_identical'], r['blind_identical'], r['raw_similarity'], r['blind_similarity'],
                  r['metric_suggested_type']] for r in pm]))
t2 += ['', '## Table 2.3 – AST scanner pairs (blind similarity >= 0.75) with audit verdict', '']
ap = rows(T2 / 'ast_pairs_adjudicated.csv')
t2.append(table(['Blind sim.', 'Raw sim.', 'Unit A', 'Unit B', 'Verdict', 'Clone / reason'],
                [[r['blind_similarity'], r['raw_similarity'], r['unit_a'], r['unit_b'], r['verdict'],
                  r['clone_id'] or r['reason']] for r in ap]))
(T2 / 'tables.md').write_text('\n'.join(t2) + '\n', encoding='utf-8')
print('wrote', T1 / 'tables.md', 'and', T2 / 'tables.md')
