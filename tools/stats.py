"""Print the routing summary as a markdown table, straight from the boards."""
import sys, collections
sys.path.insert(0, ".")
from sexp import loads, find, first

rows = []
for name in ("Symm60HE-Left", "Symm60HE-Right", "Symm60HE-Daughterboard"):
    b = loads(open("../pcb/%s.kicad_pcb" % name).read())
    segs, vias = find(b, "segment"), find(b, "via")
    per = collections.Counter()
    for s in segs: per[first(s, "layer")[1]] += 1
    nets = set()
    for fp in find(b, "footprint"):
        for p in find(fp, "pad"):
            n = first(p, "net")
            if n: nets.add(n[1])
    rows.append((name, len(segs), per["B.Cu"], per["F.Cu"], len(vias), len(nets)))

print("| | " + " | ".join(r[0].replace("Symm60HE-", "") for r in rows) + " |")
print("|---|" + "---|" * len(rows))
for label, k in (("Segments", 1), ("… on B.Cu", 2), ("… on F.Cu", 3), ("Vias", 4), ("Nets", 5)):
    print("| %s | " % label + " | ".join(str(r[k]) for r in rows) + " |")
