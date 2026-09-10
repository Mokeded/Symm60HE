"""Pad-level conflict check.

Two switch positions that can never be populated together are allowed to
overlap -- that is what a multi-layout PCB is.  Everything else must clear.
"""
import sys, itertools, math
sys.path.insert(0, ".")
from sexp import loads, find, first
from shapely.geometry import Polygon, box, Point
from shapely.affinity import rotate as srot, translate as stran
from geom import KEYS, U

def pad_shapes(fp):
    at = first(fp, "at"); fx, fy = float(at[1]), float(at[2])
    frot = float(at[3]) if len(at) > 3 else 0.0
    out = []
    for p in find(fp, "pad"):
        a = first(p, "at"); sz = first(p, "size")
        x, y = float(a[1]), float(a[2])
        w, h = float(sz[1]), float(sz[2])
        shape = Point(x, y).buffer(w/2) if p[3] == "circle" else box(x-w/2, y-h/2, x+w/2, y+h/2)
        out.append(stran(srot(shape, -frot, origin=(0, 0)), fx, fy))
    return out

# positions that may legitimately overlap: any pair of switch cells whose caps
# overlap, i.e. the layout options
excl = set()
for a, b in itertools.combinations(KEYS, 2):
    ax, ay, aw = a["cx"]*U, a["cy"]*U, a["w"]*U
    bx, by, bw = b["cx"]*U, b["cy"]*U, b["w"]*U
    A = stran(srot(box(-aw/2, -9.525, aw/2, 9.525), -a["rot"], origin=(0,0)), ax, ay)
    B = stran(srot(box(-bw/2, -9.525, bw/2, 9.525), -b["rot"], origin=(0,0)), bx, by)
    if A.intersection(B).area > 1.0:
        excl.add((round(ax,1), round(ay,1), round(bx,1), round(by,1)))
        excl.add((round(bx,1), round(by,1), round(ax,1), round(ay,1)))

for name in ("Symm60HE-Left", "Symm60HE-Right", "Symm60HE-Daughterboard"):
    b = loads(open("../pcb/%s.kicad_pcb" % name).read())
    fps = find(b, "footprint")
    info = []
    for fp in fps:
        ref = next((p[2] for p in find(fp, "property") if p[1] == "Reference"), "?")
        at = first(fp, "at")
        info.append((ref, (round(float(at[1]),1), round(float(at[2]),1)), pad_shapes(fp)))
    # the USB-C receptacle is a marked keep-out, not a footprint, so add it by
    # hand -- otherwise nothing stops a part being placed under the connector
    if "Daughterboard" in name:
        from sexp import first as _f
        ub = [l for l in find(b, "gr_line") if _f(l, "layer")[1] == "Dwgs.User"]
        if ub:
            xs = [float(_f(l, "start")[1]) for l in ub] + [float(_f(l, "end")[1]) for l in ub]
            ys = [float(_f(l, "start")[2]) for l in ub] + [float(_f(l, "end")[2]) for l in ub]
            info.append(("USB-C", (0, 0), [box(min(xs), min(ys), max(xs), max(ys))]))

    hits = []
    for (r1, p1, s1), (r2, p2, s2) in itertools.combinations(info, 2):
        if (p1[0], p1[1], p2[0], p2[1]) in excl: continue
        worst = 0.0
        for a in s1:
            for c in s2:
                worst = max(worst, a.intersection(c).area)
        if worst > 0.02: hits.append((r1, r2, worst))
    hits.sort(key=lambda h: -h[2])
    print("%-22s pad conflicts: %d %s" % (name, len(hits),
          " | ".join("%s~%s %.2fmm2" % h for h in hits[:6])))
