"""Track A - Dependency Structure Matrix (DSM) & coupling metrics for HTTPie.

Builds the static import graph with grimp (the engine behind import-linter),
then produces:
  * raw/dsm_components.csv        component x component import counts
  * raw/coupling_modules.csv      per-module Ca / Ce / Instability (Martin)
  * raw/import_cycles.txt         strongly-connected components (cycles)
  * figures/dsm_heatmap.png       component-level DSM heatmap
  * figures/dsm_modules_heatmap.png  module-level DSM (cycles highlighted)

Run from the repository root:  python track_a_analysis/scripts/dsm.py
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

import grimp
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW, FIG = ROOT / "raw", ROOT / "figures"
RAW.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)

sys.path.insert(0, str(ROOT.parent))
graph = grimp.build_graph("httpie", include_external_packages=False)
modules = sorted(m for m in graph.modules if m.startswith("httpie"))
edges = []  # (importer, imported, n_import_lines)
for importer in modules:
    for imported in graph.find_modules_directly_imported_by(importer):
        if imported.startswith("httpie") and imported != importer:
            details = graph.get_import_details(importer=importer, imported=imported)
            edges.append((importer, imported, max(1, len(details))))


# ---------------------------------------------------------------- components
def component(mod: str) -> str:
    parts = mod.split(".")
    if len(parts) == 1:
        return "httpie (pkg)"
    if parts[1] in {"cli", "output", "plugins", "manager", "internal", "legacy"}:
        # split the two largest subsystems one level deeper
        if parts[1] == "output" and len(parts) > 2 and parts[2] in {"ui", "formatters", "lexers"}:
            return f"output.{parts[2]}"
        if parts[1] == "cli" and len(parts) > 2 and parts[2] == "nested_json":
            return "cli.nested_json"
        return parts[1]
    return parts[1]  # top-level module, e.g. core, client, sessions


comps = sorted({component(m) for m in modules})
# order: layered-ish (entry points first) for readability
preferred = ["httpie (pkg)", "__main__", "core", "client", "sessions", "models", "context", "config",
             "cli", "cli.nested_json", "output", "output.formatters", "output.lexers", "output.ui",
             "plugins", "manager", "internal", "legacy", "uploads", "downloads", "adapters", "encoding",
             "cookies", "ssl_", "status", "compat", "utils"]
comps = [c for c in preferred if c in comps] + [c for c in comps if c not in preferred]
idx = {c: i for i, c in enumerate(comps)}
M = np.zeros((len(comps), len(comps)), dtype=int)
for a, b, n in edges:
    ca, cb = component(a), component(b)
    if ca != cb:
        M[idx[ca], idx[cb]] += n

with open(RAW / "dsm_components.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["importer \\ imported"] + comps)
    for c in comps:
        w.writerow([c] + list(M[idx[c]]))

# ---------------------------------------------------------------- coupling
ca_set, ce_set = defaultdict(set), defaultdict(set)
for a, b, _ in edges:
    ce_set[a].add(b)
    ca_set[b].add(a)
rows = []
for m in modules:
    ca, ce = len(ca_set[m]), len(ce_set[m])
    inst = ce / (ca + ce) if ca + ce else 0.0
    rows.append((m, ca, ce, round(inst, 2)))
rows.sort(key=lambda r: -(r[1] + r[2]))
with open(RAW / "coupling_modules.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["module", "afferent_Ca", "efferent_Ce", "instability_I"])
    w.writerows(rows)


# ---------------------------------------------------------------- cycles (Tarjan SCC)
adj = defaultdict(set)
for a, b, _ in edges:
    adj[a].add(b)
index, low, onstack, stack, sccs, counter = {}, {}, set(), [], [], [0]


def strongconnect(v):
    index[v] = low[v] = counter[0]
    counter[0] += 1
    stack.append(v)
    onstack.add(v)
    for w_ in adj[v]:
        if w_ not in index:
            strongconnect(w_)
            low[v] = min(low[v], low[w_])
        elif w_ in onstack:
            low[v] = min(low[v], index[w_])
    if low[v] == index[v]:
        comp_ = []
        while True:
            w_ = stack.pop()
            onstack.discard(w_)
            comp_.append(w_)
            if w_ == v:
                break
        if len(comp_) > 1:
            sccs.append(sorted(comp_))


sys.setrecursionlimit(10000)
for m in modules:
    if m not in index:
        strongconnect(m)
sccs.sort(key=len, reverse=True)

comp_cycles = [(comps[i], comps[j]) for i in range(len(comps)) for j in range(i + 1, len(comps))
               if M[i, j] and M[j, i]]
with open(RAW / "import_cycles.txt", "w") as fh:
    fh.write(f"Modules: {len(modules)}   import edges: {len(edges)}\n")
    fh.write(f"Module-level strongly connected components (cycles): {len(sccs)}\n\n")
    for k, s in enumerate(sccs, 1):
        fh.write(f"SCC #{k} ({len(s)} modules):\n  " + "\n  ".join(s) + "\n\n")
    fh.write(f"Component-level bidirectional dependencies: {len(comp_cycles)}\n")
    for a, b in comp_cycles:
        fh.write(f"  {a} <-> {b}   ({M[idx[a], idx[b]]} / {M[idx[b], idx[a]]} import lines)\n")


# ---------------------------------------------------------------- heatmap: components
def draw(matrix, labels, path, title, cyc_pairs=frozenset(), fontsize=8, annotate=True):
    n = len(labels)
    size = max(7, n * 0.38)
    fig, ax = plt.subplots(figsize=(size + 1.5, size))
    shown = np.where(matrix > 0, matrix, np.nan)
    im = ax.imshow(shown, cmap="YlOrRd", vmin=0.5)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=90, fontsize=fontsize)
    ax.set_yticklabels(labels, fontsize=fontsize)
    ax.set_xticks(np.arange(-.5, n, 1), minor=True)
    ax.set_yticks(np.arange(-.5, n, 1), minor=True)
    ax.grid(which="minor", color="#dddddd", linewidth=0.5)
    ax.tick_params(which="minor", length=0)
    for i in range(n):
        ax.add_patch(plt.Rectangle((i - .5, i - .5), 1, 1, color="#444444"))
        for j in range(n):
            if annotate and matrix[i, j]:
                ax.text(j, i, str(matrix[i, j]), ha="center", va="center", fontsize=fontsize - 1,
                        color="black")
            if (i, j) in cyc_pairs:
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False, ec="#0055ff", lw=1.8))
    ax.set_xlabel("imported (depends-on target)")
    ax.set_ylabel("importer (row depends on column)")
    ax.set_title(title, fontsize=11)
    fig.colorbar(im, ax=ax, fraction=0.035, label="# import statements")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


cyc_cells = {(i, j) for i in range(len(comps)) for j in range(len(comps)) if M[i, j] and M[j, i]}
draw(M, comps, FIG / "dsm_heatmap.png",
     "HTTPie component DSM (blue box = bidirectional / cyclic dependency)", cyc_cells)

# module-level DSM restricted to the modules that participate in coupling (degree >= 3)
keep = [m for m, ca, ce, _ in rows if ca + ce >= 3]
keep.sort()
kidx = {m: i for i, m in enumerate(keep)}
MM = np.zeros((len(keep), len(keep)), dtype=int)
for a, b, n in edges:
    if a in kidx and b in kidx:
        MM[kidx[a], kidx[b]] = n
in_scc = {m for s in sccs for m in s}
mcells = {(kidx[a], kidx[b]) for a, b, _ in edges if a in kidx and b in kidx and a in in_scc and b in in_scc
          and any(a in s and b in s for s in sccs)}
draw(MM, [k.replace("httpie.", "") for k in keep], FIG / "dsm_modules_heatmap.png",
     f"HTTPie module DSM ({len(keep)} modules, blue = edge inside an import cycle)", mcells,
     fontsize=6, annotate=False)

print(f"modules={len(modules)} edges={len(edges)} components={len(comps)} sccs={len(sccs)} "
      f"largest_scc={len(sccs[0]) if sccs else 0} component_cycles={len(comp_cycles)}")
