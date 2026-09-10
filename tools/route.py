"""A first pass of routing on the generated boards.

Two planes.  Every component sits on the back, so the front copper is empty and
becomes the +3V3A plane; the back gets the GND pour, which fills around the
signal traces.  Both pours use connect_pads, so GND pads tie in with no trace
at all and each analog-rail pad needs only a via.

Chaining the rail from sensor to sensor instead was the obvious first attempt
and it was wrong: a straight line between two sensors' VCC pads runs through
the MX leg holes between them.

Sensor signal to mux input is deliberately left open -- that is the part worth
doing by hand with a real router.
"""
import sys, math, uuid, re
sys.path.insert(0, ".")
from sexp import loads, dumps, find, first, Sym

TRACE_W, VIA_D, VIA_DRILL = 0.25, 0.6, 0.3
POUR_INSET, CLEAR = 0.3, 0.22

def rot(px, py, a):
    r = math.radians(-a)
    return px*math.cos(r) - py*math.sin(r), px*math.sin(r) + py*math.cos(r)

def read(path):
    b = loads(open(path).read())
    pads, outline = [], None
    for fp in find(b, "footprint"):
        ref = next((q[2] for q in find(fp, "property") if q[1] == "Reference"), "")
        at = first(fp, "at"); fx, fy = float(at[1]), float(at[2])
        fr = float(at[3]) if len(at) > 3 else 0.0
        layer = first(fp, "layer")[1]
        for p in find(fp, "pad"):
            n = first(p, "net")
            a = first(p, "at"); sz = first(p, "size")
            dx, dy = rot(float(a[1]), float(a[2]), fr)
            pads.append(dict(ref=ref, num=p[1], net=(n[1] if n else None),
                             x=fx+dx, y=fy+dy,
                             w=float(sz[1]), h=float(sz[2]), circle=(p[3] == "circle"),
                             layer="B.Cu" if layer == "B.Cu" else "F.Cu",
                             thru=(p[2] != "smd")))
    segs = [((float(first(l,"start")[1]), float(first(l,"start")[2])),
             (float(first(l,"end")[1]),   float(first(l,"end")[2])))
            for l in find(b, "gr_line") if first(l,"layer")[1] == "Edge.Cuts"]
    ring = [segs[0][0]] + [s[1] for s in segs]
    return b, pads, ring

def seg(a, b_, net, layer="B.Cu"):
    return [Sym("segment"), [Sym("start"), round(a[0],4), round(a[1],4)],
            [Sym("end"), round(b_[0],4), round(b_[1],4)],
            [Sym("width"), TRACE_W], [Sym("layer"), layer], [Sym("net"), net],
            [Sym("uuid"), str(uuid.uuid4())]]

def via(pt, net):
    return [Sym("via"), [Sym("at"), round(pt[0],4), round(pt[1],4)],
            [Sym("size"), VIA_D], [Sym("drill"), VIA_DRILL],
            [Sym("layers"), "F.Cu", "B.Cu"], [Sym("net"), net],
            [Sym("uuid"), str(uuid.uuid4())]]

def zone(ring, net, layers):
    from shapely.geometry import Polygon
    p = Polygon(ring).buffer(-POUR_INSET)
    if hasattr(p, "geoms"): p = max(p.geoms, key=lambda g: g.area)
    pts = [[Sym("xy"), round(x,4), round(y,4)] for x, y in list(p.exterior.coords)[:-1]]
    return [Sym("zone"), [Sym("net"), net], [Sym("layers")] + list(layers),
            [Sym("uuid"), str(uuid.uuid4())], [Sym("hatch"), Sym("edge"), 0.5],
            [Sym("connect_pads"), Sym("yes"), [Sym("clearance"), 0.3]],
            [Sym("min_thickness"), 0.2],
            [Sym("fill"), Sym("yes"), [Sym("thermal_gap"), 0.5],
             [Sym("thermal_bridge_width"), 0.5], [Sym("island_removal_mode"), 0]],
            [Sym("polygon"), [Sym("pts")] + pts]]

def obstacles(pads, net, layer):
    """Everything a trace on `net` must keep away from.  Drilled holes count
    even when they belong to a switch position the layout does not populate --
    the hole is there either way."""
    from shapely.geometry import box as sbox, Point as spt
    from shapely.affinity import rotate as srot, translate as stran
    out = []
    for p in pads:
        if p["net"] == net: continue
        if not (p["thru"] or p["layer"] == layer): continue
        g = spt(p["x"], p["y"]).buffer(p["w"]/2) if p["circle"] else \
            sbox(p["x"]-p["w"]/2, p["y"]-p["h"]/2, p["x"]+p["w"]/2, p["y"]+p["h"]/2)
        out.append(g)
    return out

def clear_path(pts, obs, w=TRACE_W):
    from shapely.geometry import LineString
    body = LineString(pts).buffer(w/2 + CLEAR)
    return not any(body.intersects(o) for o in obs)

def try_route(a, c, net, obs):
    """Straight if it is clear, else an L in either order.  None if neither."""
    for pts in ([a, c],
                [a, (c[0], a[1]), c],
                [a, (a[0], c[1]), c]):
        if clear_path(pts, obs):
            return [seg(pts[i], pts[i+1], net) for i in range(len(pts)-1)]
    return None

def route(path):
    b, pads, ring = read(path)
    by = {}
    for p in pads:
        if p["net"] is not None: by.setdefault((p["ref"], p["num"]), p)
    added, skipped = [], 0
    obs_cache = {}

    # 1. sensor -> its own decouplers, routed around whatever is in the way
    routed_pairs = []
    for (ref, num), p in sorted(by.items()):
        m = re.match(r"HE([LR])(\d+)$", ref)
        if not m or num not in ("1", "3"): continue
        h, i = m.group(1), m.group(2)
        cap = by.get(("C%s%sA" % (h, i), "1")) if num == "1" else by.get(("C%s%sB" % (h, i), "1"))
        if not cap or cap["net"] != p["net"]: continue
        if p["net"] not in obs_cache:
            obs_cache[p["net"]] = obstacles(pads, p["net"], "B.Cu")
        r = try_route((p["x"], p["y"]), (cap["x"], cap["y"]), p["net"], obs_cache[p["net"]])
        if r is None:
            skipped += 1
            continue
        added += r
        if num == "1": routed_pairs.append((p, cap, r))

    # 2. analog rail: one via per +3V3A pad, dropped on the short trace that
    # already joins the sensor to its 100n, so the pad reaches the front plane
    from shapely.geometry import Point as _pt
    vias, no_via = 0, 0
    vobs = obstacles(pads, "+3V3A", "B.Cu")
    for p, cap, r in routed_pairs:
        placed = False
        for t in (0.5, 0.35, 0.65, 0.25, 0.75):
            s0 = r[len(r)//2]
            a0 = (float(first(s0,"start")[1]), float(first(s0,"start")[2]))
            c0 = (float(first(s0,"end")[1]),   float(first(s0,"end")[2]))
            pt = (a0[0] + (c0[0]-a0[0])*t, a0[1] + (c0[1]-a0[1])*t)
            g = _pt(*pt).buffer(VIA_D/2 + CLEAR)
            if not any(g.intersects(o) for o in vobs):
                added.append(via(pt, "+3V3A")); vias += 1; placed = True; break
        if not placed: no_via += 1

    # 3. planes: +3V3A on the empty front, GND on the back around the signals
    added.append(zone(ring, "+3V3A", ["F.Cu"]))
    added.append(zone(ring, "GND", ["B.Cu"]))

    body = [c for c in b[1:]]
    out = [Sym("kicad_pcb")] + body[:-1] + added + [body[-1]]
    open(path, "w").write(dumps(out) + "\n")
    return (len([a for a in added if a[0] == "segment"]),
            len([a for a in added if a[0] == "via"]), skipped, no_via)

for name in ("DOE60-Left", "DOE60-Right", "DOE60-Daughterboard"):
    n, v, sk, nv = route("../pcb/%s.kicad_pcb" % name)
    print("%-22s %3d segments, %3d vias | left for manual: %d traces, %d vias"
          % (name, n, v, sk, nv))
