"""Switch plates -- one per layout option, plus a universal multi-layout plate.

Mutually exclusive switch positions overlap, so a plate has to either pick one
layout or merge the overlapping openings into a slot.  Both are produced.
"""
import math, ezdxf
from shapely.geometry import box
from shapely.ops import unary_union
from shapely.affinity import rotate, translate
from geom import KEYS, U, BUILDS
from outline import CASE_IN

SW_CUT, PLATE_GAP = 14.0, 0.5
STAB_X, STAB_CUT = 11.90625, (7.0, 15.6, 0.635)
PLATE = CASE_IN.buffer(-PLATE_GAP)

def placed(k, shape):
    return translate(rotate(shape, k["rot"], origin=(0, 0)), k["cx"] * U, k["cy"] * U)

def cutouts(keys):
    cuts, stabs = [], []
    for k in keys:
        cuts.append(placed(k, box(-SW_CUT/2, -SW_CUT/2, SW_CUT/2, SW_CUT/2)))
        if k["w"] >= 2.0:
            w, h, dy = STAB_CUT
            for sx in (-STAB_X, STAB_X):
                stabs.append(placed(k, box(sx-w/2, dy-h/2, sx+w/2, dy+h/2)))
    return cuts, stabs

def write(name, cuts, stabs, merge=False):
    doc = ezdxf.new("R2010"); doc.units = ezdxf.units.MM
    msp = doc.modelspace()
    for ln, col in (("PLATE_OUTLINE", 7), ("SWITCH_CUTOUTS", 3), ("STAB_CLEARANCE", 1)):
        doc.layers.add(ln, color=col)
    def put(poly, layer):
        msp.add_lwpolyline(list(poly.exterior.coords), close=True, dxfattribs={"layer": layer})
        for r in poly.interiors:
            msp.add_lwpolyline(list(r.coords), close=True, dxfattribs={"layer": layer})
    put(PLATE, "PLATE_OUTLINE")
    if merge:
        # Merge openings that leave a web thinner than the plate is thick; a
        # 0.3 mm sliver of 1.5 mm steel will not survive laser cutting.
        u = unary_union(cuts).buffer(0.6).buffer(-0.6)
        shapes = list(u.geoms) if hasattr(u, "geoms") else [u]
    else:
        shapes = cuts
    for c in shapes: put(c, "SWITCH_CUTOUTS")
    for s in unary_union(stabs).geoms if stabs else []: put(s, "STAB_CLEARANCE")
    doc.saveas("../plate/%s.dxf" % name)
    return shapes

def check(name, cuts):
    bad = sum(1 for c in cuts if not PLATE.contains(c))
    ov = 0
    for i in range(len(cuts)):
        for j in range(i+1, len(cuts)):
            if cuts[i].intersection(cuts[j]).area > 0.01: ov += 1
    web = min(PLATE.exterior.distance(c) for c in cuts)
    bridge = 1e9
    for i in range(len(cuts)):
        for j in range(i+1, len(cuts)):
            if cuts[i].intersection(cuts[j]).area <= 0.01:
                bridge = min(bridge, cuts[i].distance(cuts[j]))
    print("%-26s %3d openings | outside %d | overlaps %d | edge web %.2f mm | min bridge %.2f mm"
          % (name, len(cuts), bad, ov, web, bridge))

for b in BUILDS:
    ks = [k for k in KEYS if b in k["builds"]]
    cuts, stabs = cutouts(ks)
    write("DOE60-plate-" + b.replace("doe-", ""), cuts, stabs)
    check(b.replace("doe-", ""), cuts)

cuts, stabs = cutouts(KEYS)
merged = write("DOE60-plate-universal", cuts, stabs, merge=True)
check("universal (merged)", merged)
