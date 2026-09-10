"""Structural + geometric checks on the generated boards."""
import sys, math, itertools
sys.path.insert(0, ".")
from sexp import loads, find, first
from shapely.geometry import Polygon, box, LineString
from shapely.affinity import rotate as srot, translate as stran
from shapely.ops import unary_union

def courtyard(fp):
    """Approximate a footprint's extent from its pads and courtyard lines."""
    pts = []
    for p in find(fp, "pad"):
        at = first(p, "at"); sz = first(p, "size")
        x, y = float(at[1]), float(at[2])
        w, h = float(sz[1]), float(sz[2])
        pts += [(x-w/2, y-h/2), (x+w/2, y+h/2)]
    for l in find(fp, "fp_line"):
        if first(l, "layer")[1].endswith("CrtYd"):
            s, e = first(l, "start"), first(l, "end")
            pts += [(float(s[1]), float(s[2])), (float(e[1]), float(e[2]))]
    if not pts: return None
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return box(min(xs), min(ys), max(xs), max(ys))

for name in ("Symm60HE-Left", "Symm60HE-Right", "Symm60HE-Daughterboard"):
    txt = open("../pcb/%s.kicad_pcb" % name).read()
    b = loads(txt)
    assert b[0] == "kicad_pcb", name
    fps = find(b, "footprint")
    edges = [l for l in find(b, "gr_line") if first(l, "layer")[1] == "Edge.Cuts"]
    segs = [((float(first(l,"start")[1]), float(first(l,"start")[2])),
             (float(first(l,"end")[1]),  float(first(l,"end")[2]))) for l in edges]
    ring = [segs[0][0]] + [s[1] for s in segs]
    outline = Polygon(ring)
    closed = abs(segs[-1][1][0]-segs[0][0][0]) < 1e-6 and abs(segs[-1][1][1]-segs[0][0][1]) < 1e-6

    shapes, refs, outside = [], [], []
    for fp in fps:
        at = first(fp, "at")
        x, y = float(at[1]), float(at[2])
        rot = float(at[3]) if len(at) > 3 else 0.0
        cy = courtyard(fp)
        ref = next((p[2] for p in find(fp, "property") if p[1] == "Reference"), "?")
        if cy is None: continue
        g = stran(srot(cy, -rot, origin=(0, 0)), x, y)
        shapes.append(g); refs.append(ref)
        if not outline.buffer(0.01).contains(g): outside.append(ref)

    coll = []
    for i, j in itertools.combinations(range(len(shapes)), 2):
        if shapes[i].intersection(shapes[j]).area > 0.10:
            coll.append((refs[i], refs[j], shapes[i].intersection(shapes[j]).area))
    nets = set()
    for fp in fps:
        for p in find(fp, "pad"):
            n = first(p, "net")
            if n: nets.add(n[1])
    print("%-22s parses ok | %3d footprints | outline %s (%.1f x %.1f mm) | %d nets"
          % (name, len(fps), "closed" if closed else "OPEN!",
             outline.bounds[2]-outline.bounds[0], outline.bounds[3]-outline.bounds[1], len(nets)))
    print("      outside outline: %d %s" % (len(outside), outside[:6] if outside else ""))
    print("      courtyard collisions: %d %s" % (len(coll),
          ", ".join("%s/%s %.2fmm2" % c for c in sorted(coll, key=lambda c: -c[2])[:5])))
