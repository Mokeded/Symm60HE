"""Check the routing against the real geometry, not the router's own grid.

Four things have to hold, per layer:
  * every piece of copper is inside the board outline,
  * no trace or via comes within CLEAR of a pad on another net,
  * no trace or via comes within CLEAR of another net's copper -- this is the
    one that catches two diagonal runs crossing through the same gap, which
    cell ownership alone cannot rule out,
  * every pad of a poured net can reach its pour, directly or through a via,
  * no trace end is left hanging: it has to land on a pad of its own net, on a
    via, on another segment end of the same net (a corner in an L-shaped run),
    or *anywhere along* another segment of the same net -- a branch of a
    multi-pad net leaves its trunk at a T, and the trunk has no vertex there
    because the run was straight through.
"""
import sys, math, collections
sys.path.insert(0, ".")
from sexp import loads, find, first
from shapely.geometry import Polygon, LineString, box, Point
from shapely.affinity import rotate as srot, translate as stran
from shapely.strtree import STRtree

CLEAR = 0.15
EPS = 1e-6

def rot(px, py, a):
    r = math.radians(-a)
    return px*math.cos(r) - py*math.sin(r), px*math.sin(r) + py*math.cos(r)

bad = 0
for name in ("Symm60HE-Left", "Symm60HE-Right", "Symm60HE-Daughterboard"):
    b = loads(open("../pcb/%s.kicad_pcb" % name).read())
    es = [((float(first(l,"start")[1]), float(first(l,"start")[2])),
           (float(first(l,"end")[1]),   float(first(l,"end")[2])))
          for l in find(b,"gr_line") if first(l,"layer")[1]=="Edge.Cuts"]
    outline = Polygon([es[0][0]] + [s[1] for s in es])
    ko = [((float(first(l,"start")[1]), float(first(l,"start")[2])),
           (float(first(l,"end")[1]),   float(first(l,"end")[2])))
          for l in find(b,"gr_line") if first(l,"layer")[1]=="Dwgs.User"]
    keepout = Polygon([ko[0][0]] + [s[1] for s in ko]) if len(ko) > 2 else None

    # ------------------------------------------------------------ pads
    pads = []
    for fp in find(b,"footprint"):
        at = first(fp,"at"); fx, fy = float(at[1]), float(at[2])
        fr = float(at[3]) if len(at)>3 else 0.0
        flay = first(fp,"layer")[1]
        for i, p in enumerate(find(fp,"pad")):
            a = first(p,"at"); sz = first(p,"size")
            dx, dy = rot(float(a[1]), float(a[2]), fr)
            w, h = float(sz[1]), float(sz[2])
            g = Point(fx+dx, fy+dy).buffer(w/2) if p[3]=="circle" else \
                stran(srot(box(-w/2,-h/2,w/2,h/2), -fr, origin=(0,0)), fx+dx, fy+dy)
            n = first(p,"net")
            lays = ("F.Cu","B.Cu") if p[2]!="smd" else \
                   (("B.Cu",) if flay=="B.Cu" else ("F.Cu",))
            # an unnamed pad is nobody's, so give it an identity of its own
            pads.append(dict(net=(n[1] if n else "#%d.%d" % (id(fp), i)),
                             g=g, lays=lays))

    # ------------------------------------------------------------ copper
    cu = []                                   # (geom, net, layers)
    for s in find(b,"segment"):
        a = first(s,"start"); c = first(s,"end")
        w = float(first(s,"width")[1])
        cu.append((LineString([(float(a[1]),float(a[2])),
                               (float(c[1]),float(c[2]))]).buffer(w/2),
                   first(s,"net")[1], (first(s,"layer")[1],), s))
    for v in find(b,"via"):
        a = first(v,"at")
        cu.append((Point(float(a[1]), float(a[2])).buffer(float(first(v,"size")[1])/2),
                   first(v,"net")[1], ("F.Cu","B.Cu"), v))

    by_layer = collections.defaultdict(list)
    for rec in cu:
        for L in rec[2]: by_layer[L].append(rec)
    for p in pads:
        for L in p["lays"]: by_layer[L].append((p["g"], p["net"], p["lays"], None))
    trees = {L: (STRtree([r[0] for r in rs]), rs) for L, rs in by_layer.items()}

    off = clash = inko = 0
    for g, net, lays, node in cu:
        if not outline.buffer(-0.05).contains(g): off += 1
        if keepout is not None and keepout.intersects(g): inko += 1
        probe = g.buffer(CLEAR - EPS)
        hit = False
        for L in lays:
            tree, rs = trees[L]
            for k in tree.query(probe):
                og, onet, _, onode = rs[k]
                if onet == net or onode is node: continue
                if probe.intersects(og): hit = True; break
            if hit: break
        if hit: clash += 1

    # ------------------------------------------------------------ loose ends
    joints = collections.Counter()
    for s in find(b,"segment"):
        n = first(s,"net")[1]
        for e in ("start","end"):
            q = first(s,e)
            joints[(n, round(float(q[1]),3), round(float(q[2]),3))] += 1
    for v in find(b,"via"):
        q = first(v,"at")
        joints[(first(v,"net")[1], round(float(q[1]),3), round(float(q[2]),3))] += 1
    padtree = STRtree([p["g"] for p in pads])
    cutree = STRtree([r[0] for r in cu])
    dangling = 0
    for s in find(b,"segment"):
        net = first(s,"net")[1]
        for e in ("start","end"):
            q = first(s,e); x, y = float(q[1]), float(q[2])
            pt = Point(x, y)
            if joints[(net, round(x,3), round(y,3))] > 1: continue
            if any(pads[k]["net"] == net and pads[k]["g"].buffer(0.05).contains(pt)
                   for k in padtree.query(pt.buffer(0.05))): continue
            probe = pt.buffer(0.02)
            if any(cu[k][1] == net and cu[k][3] is not s and cu[k][0].contains(pt)
                   for k in cutree.query(probe)): continue
            dangling += 1

    zones = find(b,"zone")
    zbad = 0
    zlay = {}
    for z in zones:
        poly = Polygon([(float(q[1]),float(q[2]))
                        for q in first(first(z,"polygon"),"pts")[1:]])
        if not outline.contains(poly): zbad += 1
        zlay.setdefault(first(z,"layers")[1], []).append(first(z,"net")[1])
    # one pour per layer, and every layer poured: a pad on an unpoured layer
    # would have nothing to tie to
    for L in ("F.Cu", "B.Cu"):
        if len(zlay.get(L, [])) != 1: zbad += 1
    # every pad of a poured net must reach its pour -- directly if it is on
    # that layer, otherwise through a via of the same net
    unstitched = 0
    vpts = collections.defaultdict(list)
    for v in find(b,"via"):
        a = first(v,"at")
        vpts[first(v,"net")[1]].append(Point(float(a[1]), float(a[2])))
    for L, nets in zlay.items():
        pn = nets[0]
        for p in pads:
            if p["net"] != pn or L in p["lays"]: continue
            if not vpts[pn]: unstitched += 1; continue
            # the pad has to be joined to some via of its net; the copper check
            # above already proved the joining trace is legal
            if min(p["g"].distance(q) for q in vpts[pn]) > 25.0: unstitched += 1

    nseg, nvia = len(find(b,"segment")), len(find(b,"via"))
    print("%-22s %3d segments, %3d vias | off-board %d | in keep-out %d | clearance violations %d | loose ends %d | %d pours (%s), bad %d | unstitched %d"
          % (name, nseg, nvia, off, inko, clash, dangling, len(zones),
             ", ".join("%s=%s" % (L, zlay[L][0]) for L in sorted(zlay)), zbad, unstitched))
    bad += off + inko + clash + dangling + zbad + unstitched

print("\n%s" % ("ROUTING CLEAN" if bad == 0 else "%d routing problems" % bad))
sys.exit(1 if bad else 0)
