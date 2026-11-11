"""Cross-reference AI-reported clone fragments against token-scan results."""
import json, re, sys
from pathlib import Path
root = Path(sys.argv[1])
frags = {f['id']: f for f in json.loads((root / 'fragments.json').read_text())}
pairs = sorted({k[:3] for k in frags})
runs = ['exact_mts25', 'exact_mts50', 'exact_mts100', 'ignoreids_mts25', 'ignoreids_mts50', 'ignoreids_mts100']
pat = re.compile(r'^\s*(\d+) tokens\s+\d+ lines\s+(\S+):(\d+)-(\d+)\s+<->\s+(\S+):(\d+)-(\d+)')
def overlaps(f, file, s, e):
    return f['file'] == file and not (e < f['start'] or s > f['end'])
print('pair  ' + '  '.join(f'{r:>16}' for r in runs))
for p in pairs:
    members = [frags[k] for k in frags if k.startswith(p)]
    row = []
    for r in runs:
        best = 0
        for line in (root / f'{r}.txt').read_text().splitlines():
            m = pat.match(line)
            if not m: continue
            n, fa, sa, ea, fb, sb, eb = m.groups()
            hit_a = [x for x in members if overlaps(x, fa, int(sa), int(ea))]
            hit_b = [x for x in members if overlaps(x, fb, int(sb), int(eb))]
            if hit_a and hit_b and set(map(id, hit_a + hit_b)).__len__() >= 2:
                best = max(best, int(n))
        row.append(f'{("YES (" + str(best) + ")") if best else "no":>16}')
    print(f'{p:<5} ' + '  '.join(row))
