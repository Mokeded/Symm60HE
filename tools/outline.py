"""Board and plate outlines, in millimetres, KiCad orientation (y down)."""
import math, json
from shapely.geometry import Polygon, box, MultiPolygon
from shapely.ops import unary_union
from geom import KEYS, U, AXIS

WALL      = 3.0     # case wall thickness
BEZEL     = 0.46 * U   # key field -> case inner edge, as the renders use
PCB_GAP   = 2.0     # clearance between the two half PCBs
PCB_INSET = 1.2     # PCB edge inside the case inner wall

def cap(k, grow=0.0):
    a = math.radians(k["rot"]); c, s = math.cos(a), math.sin(a)
    hw, hh = k["w"] / 2.0 + grow, 0.5 + grow
    return Polygon([(k["cx"] + dx*c - dy*s, k["cy"] + dx*s + dy*c)
                    for dx, dy in ((-hw,-hh),(hw,-hh),(hw,hh),(-hw,hh))])

field = unary_union([cap(k) for k in KEYS])          # in u
hull  = field.convex_hull

# Square off the top and sides the way the case drawing does, leaving the swept
# front to follow the hull.
b = hull.bounds
xs = list(hull.exterior.coords)
yl = max(y for x, y in xs if x < b[0] + 0.08)
yr = max(y for x, y in xs if x > b[2] - 0.08)
case_in = hull.union(box(b[0], b[1], b[2], min(yl, yr))).buffer(0.06).buffer(-0.06)
case_in = case_in.buffer(BEZEL / U)                   # case inner face
case_out = case_in.buffer(WALL / U)                   # case outer face

def to_mm(poly):
    return Polygon([(x * U, y * U) for x, y in poly.exterior.coords])

CASE_IN  = to_mm(case_in)
CASE_OUT = to_mm(case_out)
axis_mm  = AXIS * U

pcb_area = CASE_IN.buffer(-PCB_INSET)
big = box(*[v * 2 for v in (-1e3, -1e3, 1e3, 1e3)])
LEFT_PCB  = pcb_area.intersection(box(-1e4, -1e4, axis_mm - PCB_GAP / 2, 1e4))
RIGHT_PCB = pcb_area.intersection(box(axis_mm + PCB_GAP / 2, -1e4, 1e4, 1e4))

def big_poly(g):
    if isinstance(g, MultiPolygon): return max(g.geoms, key=lambda p: p.area)
    return g
LEFT_PCB, RIGHT_PCB = big_poly(LEFT_PCB), big_poly(RIGHT_PCB)

# Daughterboard: the top-centre wedge where the two halves pull apart.
DB_W, DB_H = 56.0, 26.0   # LQFP-64 + USB-C between two end-on FFC links
top = CASE_IN.bounds[1]
DB = box(axis_mm - DB_W / 2, top + 1.0, axis_mm + DB_W / 2, top + 1.0 + DB_H)

if __name__ == "__main__":
    for nm, p in (("case outer", CASE_OUT), ("case inner", CASE_IN),
                  ("left PCB", LEFT_PCB), ("right PCB", RIGHT_PCB),
                  ("daughterboard", DB)):
        bb = p.bounds
        print("%-14s %7.1f x %6.1f mm   area %7.1f cm2   x %.1f..%.1f  y %.1f..%.1f"
              % (nm, bb[2]-bb[0], bb[3]-bb[1], p.area/100, bb[0], bb[2], bb[1], bb[3]))
    print("centre axis x = %.2f mm" % axis_mm)
    print("left/right PCBs overlap DB area:",
          LEFT_PCB.intersects(DB) or RIGHT_PCB.intersects(DB))
