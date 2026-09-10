"""Check the routing: on-board, endpoints on their pads, no foreign-pad crossings."""
import sys, math
sys.path.insert(0, ".")
from sexp import loads, find, first
from shapely.geometry import Polygon, LineString, box, Point
from shapely.affinity import rotate as srot, translate as stran

CLEAR = 0.20

def rot(px, py, a):
    r = math.radians(-a)
    return px*math.cos(r) - py*math.sin(r), px*math.sin(r) + py*math.cos(r)

bad = 0
for name in ("DOE60-Left", "DOE60-Right", "DOE60-Daughterboard"):
    b = loads(open("../pcb/%s.kicad_pcb" % name).read())
    es = [((float(first(l,"start")[1]), float(first(l,"start")[2])),
           (float(first(l,"end")[1]),   float(first(l,"end")[2])))
          for l in find(b,"gr_line") if first(l,"layer")[1]=="Edge.Cuts"]
    outline = Polygon([es[0][0]] + [s[1] for s in es])

    pads = []
    for fp in find(b,"footprint"):
        at = first(fp,"at"); fx, fy = float(at[1]), float(at[2])
        fr = float(at[3]) if len(at)>3 else 0.0
        flay = first(fp,"layer")[1]
        for p in find(fp,"pad"):
            a = first(p,"at"); sz = first(p,"size")
            dx, dy = rot(float(a[1]), float(a[2]), fr)
            w, h = float(sz[1]), float(sz[2])
            g = Point(fx+dx, fy+dy).buffer(w/2) if p[3]=="circle" else \
                stran(srot(box(-w/2,-h/2,w/2,h/2), -fr, origin=(0,0)), fx+dx, fy+dy)
            n = first(p,"net")
            pads.append(dict(net=n[1] if n else None, g=g,
                             layer=("B.Cu" if flay=="B.Cu" else "F.Cu"),
                             thru=(p[2]!="smd")))

    segs = find(b,"segment")
    # an endpoint may land on a pad, on a via, or on another segment of the same
    # net -- the last is a corner in an L-shaped route, not a loose end
    joints = {}
    for s2 in segs:
        n2 = first(s2,"net")[1]
        for e in ("start","end"):
            q = first(s2,e)
            joints.setdefault((n2, round(float(q[1]),3), round(float(q[2]),3)), 0)
            joints[(n2, round(float(q[1]),3), round(float(q[2]),3))] += 1
    for v2 in find(b,"via"):
        q = first(v2,"at"); n2 = first(v2,"net")[1]
        joints[(n2, round(float(q[1]),3), round(float(q[2]),3))] = \
            joints.get((n2, round(float(q[1]),3), round(float(q[2]),3)), 0) + 1
    off, foreign, dangling = 0, 0, 0
    for s in segs:
        a = first(s,"start"); c = first(s,"end")
        net = first(s,"net")[1]; lay = first(s,"layer")[1]
        w = float(first(s,"width")[1])
        line = LineString([(float(a[1]),float(a[2])), (float(c[1]),float(c[2]))])
        if not outline.buffer(-0.05).contains(line): off += 1
        body = line.buffer(w/2)
        for p in pads:
            if p["net"] == net: continue
            if not (p["thru"] or p["layer"] == lay): continue
            if body.buffer(CLEAR).intersects(p["g"]): foreign += 1; break
        ends = 0
        for q in (a, c):
            pt = Point(float(q[1]), float(q[2]))
            on_pad = any(p["net"]==net and p["g"].buffer(0.05).contains(pt) for p in pads)
            joined = joints.get((net, round(float(q[1]),3), round(float(q[2]),3)), 0) > 1
            if on_pad or joined: ends += 1
        if ends < 2: dangling += 1

    # vias: must be on-board and clear of foreign pads
    vias = find(b,"via")
    voff, vclash = 0, 0
    for v in vias:
        a = first(v,"at"); net = first(v,"net")[1]
        g = Point(float(a[1]), float(a[2])).buffer(float(first(v,"size")[1])/2)
        if not outline.buffer(-0.05).contains(g): voff += 1
        for p in pads:
            if p["net"] == net: continue
            if g.buffer(CLEAR).intersects(p["g"]): vclash += 1; break

    zones = find(b,"zone")
    zbad = 0
    for z in zones:
        pts = first(first(z,"polygon"),"pts")
        poly = Polygon([(float(q[1]),float(q[2])) for q in pts[1:]])
        if not outline.contains(poly): zbad += 1

    print("%-22s %3d segments, %3d vias | off-board %d/%d | foreign-pad clashes %d/%d | dangling ends %d | %d pours, outside %d"
          % (name, len(segs), len(vias), off, voff, foreign, vclash, dangling, len(zones), zbad))
    bad += off + foreign + dangling + zbad + voff + vclash

print("\n%s" % ("ROUTING CLEAN" if bad == 0 else "%d routing problems" % bad))
sys.exit(1 if bad else 0)
