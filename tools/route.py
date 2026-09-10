"""Routing pass for the Symm60HE boards.

Layer plan, the usual one for a two-layer analog design:

  B.Cu   components, and the great majority of the signals and the +3V3A rail.
  F.Cu   GND plane.  Nothing is mounted on the front, so it stays essentially
         unbroken, which is what the sensor returns want.
  GND    is never routed at all: both pours carry it, and the sensors' and
         muxes' ground pins sit straight on the B.Cu pour.

Two things make this harder than a plain maze:

  * A 0.65 mm TSSOP has 0.25 mm between adjacent pads, so a trace cannot get
    in from the side; a pin has to be met head-on, along its own axis.  Every
    pad therefore gets an *escape stub* -- a short straight run out along the
    pad's long axis to a fan-out ring, staggered near/far by pin parity so
    that neighbouring escape points end up 0.92 mm apart instead of 0.65 mm.
    The maze router starts from there, in open board space.
  * A 0.5 mm grid cannot represent the exact pad geometry, so everything the
    router produces is re-checked against the real shapes before it is kept.
    A connection whose copper would violate clearance is dropped and counted
    unrouted rather than written out.  The board on disk is therefore always
    clean; the honest number is the routed/unrouted split printed at the end.

Chaining the +3V3A rail straight from sensor to sensor was the first attempt
and it was wrong -- the line between two sensors' VCC pads runs through the MX
leg holes between them.  The router goes round them.
"""
import sys, math, uuid, random
sys.path.insert(0, ".")
from sexp import loads, dumps, find, first, Sym
from router import Grid, simplify, GRID, TRACE, CLEAR, PAD_MARGIN
from shapely.geometry import Polygon, Point, box as sbox, LineString
from shapely.affinity import rotate as srot, translate as stran

VIA_D, VIA_DRILL, POUR_INSET = 0.45, 0.25, 0.3
LAYERS = ("B.Cu", "F.Cu")
ESCAPE = (0.45, 1.05)          # near/far fan-out ring, past the pad tip
LANE = 1.30                    # length of a pad's private escape lane
CAND = 6                       # grid cells tried per entry point
HOOKS = 20                     # ways of meeting one pad, before giving up

def rot(px, py, a):
    r = math.radians(-a)
    return px*math.cos(r) - py*math.sin(r), px*math.sin(r) + py*math.cos(r)

def read(path):
    b = loads(open(path).read())
    pads = []
    for fp in find(b, "footprint"):
        ref = next((q[2] for q in find(fp, "property") if q[1] == "Reference"), "")
        at = first(fp, "at"); fx, fy = float(at[1]), float(at[2])
        fr = float(at[3]) if len(at) > 3 else 0.0
        layer = first(fp, "layer")[1]
        for p in find(fp, "pad"):
            n = first(p, "net")
            a = first(p, "at"); sz = first(p, "size")
            lx, ly = float(a[1]), float(a[2])
            dx, dy = rot(lx, ly, fr)
            w, h = float(sz[1]), float(sz[2])
            g = (Point(fx+dx, fy+dy).buffer(w/2) if p[3] == "circle"
                 else stran(srot(sbox(-w/2, -h/2, w/2, h/2), -fr, origin=(0,0)), fx+dx, fy+dy))
            # long axis of the pad, in board coords, pointing away from the body
            if p[3] == "circle" or abs(w - h) < 1e-9:
                ax, ay, half, wid = 0.0, 0.0, max(w, h)/2, min(w, h)
            elif w > h:
                s = 1.0 if lx >= 0 else -1.0
                ax, ay = rot(s, 0.0, fr); half, wid = w/2, h
            else:
                s = 1.0 if ly >= 0 else -1.0
                ax, ay = rot(0.0, s, fr); half, wid = h/2, w
            pads.append(dict(ref=ref, num=p[1], net=(n[1] if n else None),
                             x=fx+dx, y=fy+dy, geom=g, ax=ax, ay=ay,
                             half=half, wid=wid,
                             idx=(int(p[1]) if str(p[1]).isdigit() else 0),
                             layer=("B.Cu" if layer == "B.Cu" else "F.Cu"),
                             thru=(p[2] != "smd")))
    def poly_on(layer):
        ls = [((float(first(l,"start")[1]), float(first(l,"start")[2])),
               (float(first(l,"end")[1]),   float(first(l,"end")[2])))
              for l in find(b, "gr_line") if first(l,"layer")[1] == layer]
        return Polygon([ls[0][0]] + [q[1] for q in ls]) if len(ls) > 2 else None
    # anything drawn on Dwgs.User is a keep-out -- at the moment that is the
    # USB-C receptacle, whose body and shield tabs are not a footprint yet
    return b, pads, poly_on("Edge.Cuts"), poly_on("Dwgs.User")

def pad_layers(p):
    if p["thru"]: return (0, 1)
    return (0,) if p["layer"] == "B.Cu" else (1,)

def lane(p):
    """The strip of board a pad owns along its own axis, both ways.

    Without it a fine-pitch pin has no way out: the keep-out margins of its two
    neighbours meet in front of its tip, and whichever of them was blocked
    first ends up owning the only cells the pin could have escaped through.
    The lane is only as wide as the pad, so it stays clear of those neighbours
    by the same margin their own copper does.  It runs both ways because the
    useful direction is not always outwards: an edge connector's contacts face
    off-board, and a package's inward side is open once past the pad row."""
    if not (p["ax"] or p["ay"]): return None
    d = p["half"] + LANE
    return LineString([(p["x"] - p["ax"]*d, p["y"] - p["ay"]*d),
                       (p["x"] + p["ax"]*d, p["y"] + p["ay"]*d)]).buffer(p["wid"]*0.45)

def entries(p):
    """Points at which a trace may meet this pad, best first.

    A gullwing pad can only be met along its own axis, so the escape ring is
    staggered by pin parity: odd pins stop just past the tip, even pins carry
    on to the far ring.  Adjacent escape points are then a diagonal apart.
    """
    out = [(p["x"], p["y"])]
    if p["ax"] or p["ay"]:
        # forwards first, then backwards: a connector at the board edge has its
        # contacts facing off-board, because that is the way the cable goes in,
        # so its only way out is inwards under its own body
        for sgn in (1.0, -1.0):
            for k in (ESCAPE[p["idx"] % 2], ESCAPE[(p["idx"] + 1) % 2]):
                out.append((p["x"] + sgn*p["ax"]*(p["half"] + k),
                            p["y"] + sgn*p["ay"]*(p["half"] + k)))
    return out

# ---------------------------------------------------------------- clearance

class Space:
    """Everything already on the board, bucketed so clearance tests stay cheap."""
    CELL = 4.0
    def __init__(self):
        self.b = ({}, {})
    def _keys(self, g):
        x0, y0, x1, y1 = g.bounds
        for i in range(int(math.floor(x0/self.CELL)), int(math.floor(x1/self.CELL))+1):
            for j in range(int(math.floor(y0/self.CELL)), int(math.floor(y1/self.CELL))+1):
                yield (i, j)
    def add(self, g, net, layers):
        for L in layers:
            for k in self._keys(g.buffer(CLEAR)):
                self.b[L].setdefault(k, []).append((g, net))
    def clear(self, g, net, layers):
        probe = g.buffer(CLEAR - 1e-6)
        for L in layers:
            seen = set()
            for k in self._keys(g):
                for o, n in self.b[L].get(k, ()):
                    if n == net or id(o) in seen: continue
                    seen.add(id(o))
                    if probe.intersects(o): return False
        return True

# ---------------------------------------------------------------- emission

def seg(a, c, net, layer):
    return [Sym("segment"), [Sym("start"), round(a[0],4), round(a[1],4)],
            [Sym("end"), round(c[0],4), round(c[1],4)], [Sym("width"), TRACE],
            [Sym("layer"), layer], [Sym("net"), net], [Sym("uuid"), str(uuid.uuid4())]]

def via(pt, net):
    return [Sym("via"), [Sym("at"), round(pt[0],4), round(pt[1],4)],
            [Sym("size"), VIA_D], [Sym("drill"), VIA_DRILL],
            [Sym("layers"), "F.Cu", "B.Cu"], [Sym("net"), net],
            [Sym("uuid"), str(uuid.uuid4())]]

def zone(poly, net, layer):
    p = poly.buffer(-POUR_INSET)
    if hasattr(p, "geoms"): p = max(p.geoms, key=lambda g: g.area)
    pts = [[Sym("xy"), round(x,4), round(y,4)] for x, y in list(p.exterior.coords)[:-1]]
    return [Sym("zone"), [Sym("net"), net], [Sym("layers"), layer],
            [Sym("uuid"), str(uuid.uuid4())], [Sym("hatch"), Sym("edge"), 0.5],
            [Sym("connect_pads"), Sym("yes"), [Sym("clearance"), 0.3]],
            [Sym("min_thickness"), 0.2],
            [Sym("fill"), Sym("yes"), [Sym("thermal_gap"), 0.5],
             [Sym("thermal_bridge_width"), 0.5], [Sym("island_removal_mode"), 0]],
            [Sym("polygon"), [Sym("pts")] + pts]]

def netlist(pads):
    nets = {}
    for p in pads:
        if p["net"] in (None, "GND"): continue
        nets.setdefault(p["net"], []).append(p)
    order = []
    for n, ps in nets.items():
        if len(ps) < 2: continue
        xs = [p["x"] for p in ps]; ys = [p["y"] for p in ps]
        order.append(((max(xs)-min(xs)) + (max(ys)-min(ys)), n, ps))
    order.sort()                       # short nets first, they are the easiest
    return order

def near_cells(grid, pt, L, net, n=CAND):
    """Passable grid cells around a point, nearest first."""
    i0, j0 = grid.cell(*pt)
    out = []
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            i, j = i0+di, j0+dj
            if not grid.passable(i, j, L, net): continue
            x, y = grid.pos(i, j)
            out.append((math.hypot(x-pt[0], y-pt[1]), (L, i, j), (x, y)))
    out.sort()
    return out[:n]

# ---------------------------------------------------------------- the pass

def hooks(grid, space, p, net):
    """Ways of getting a trace onto pad `p`, best first.

    Each is (grid cell, stub) where the stub is the run of points from the
    grid cell back onto the pad centre, already checked against everything on
    the board.  A gullwing pin is normally reached through its escape point;
    an isolated pad is usually met head on, so its own cell comes first."""
    out = []
    for ept in entries(p):
        stub = [ept] if ept != (p["x"], p["y"]) else []
        if stub and not space.clear(
                LineString([ept, (p["x"], p["y"])]).buffer(TRACE/2), net, pad_layers(p)):
            continue
        for L in pad_layers(p):
            for _, cell, gpt in near_cells(grid, ept, L, net):
                pts = ([gpt] if gpt != ept else []) + stub + [(p["x"], p["y"])]
                if len(pts) > 1 and not all(
                        space.clear(LineString([pts[k], pts[k+1]]).buffer(TRACE/2),
                                    net, (L,))
                        for k in range(len(pts)-1) if pts[k] != pts[k+1]):
                    continue
                out.append((cell, pts))
                if len(out) >= HOOKS: return out
    return out

def keep(space, grid, added, net, pts, L):
    """Write one run of copper and remember it."""
    for k in range(len(pts)-1):
        if pts[k] == pts[k+1]: continue
        added.append(seg(pts[k], pts[k+1], net, LAYERS[L]))
    if len(pts) > 1:
        line = LineString(pts)
        space.add(line.buffer(TRACE/2), net, (L,))
        grid.block(line, net=net, layers=(L,))

def plan(pads, outline, step, order, keepout=None):
    """Route one ordering of the nets.  Returns the copper and the tally."""
    grid = Grid(outline, step=step)
    space = Space()
    if keepout is not None:
        grid.block(keepout, net="#", margin=PAD_MARGIN)
        space.add(keepout, "#keepout", (0, 1))
    for p in pads:
        grid.block(p["geom"], net=p["net"] if p["net"] else "#", layers=pad_layers(p))
    for p in pads:
        if p["net"]:
            # a pad reclaims the cells inside its own copper and its lane out,
            # so a neighbour's margin cannot end up owning the only way in
            grid.block(p["geom"], net=p["net"], margin=0.0,
                       layers=pad_layers(p), force=True)
            ln = lane(p)
            if ln is not None:
                grid.block(ln, net=p["net"], margin=0.0,
                           layers=pad_layers(p), force=True)
        space.add(p["geom"], p["net"] if p["net"] else "#\x00%d" % id(p), pad_layers(p))

    added, done, failed, fails, nvia = [], 0, 0, [], 0
    for span, net, ps in order:
        anchor = None
        for cell, pts in hooks(grid, space, ps[0], net):
            anchor = (cell, pts); break
        if anchor is None:
            failed += len(ps) - 1
            fails += [(net, q["ref"], q["num"]) for q in ps[1:]]
            continue
        cell, pts = anchor
        keep(space, grid, added, net, pts, cell[0])
        grid.claim([cell], net)
        connected = {cell}

        for p in ps[1:]:
            got = None
            for gcell, gpts in hooks(grid, space, p, net):
                cells = grid.route(sorted(connected), [gcell], net)
                if cells is None: continue
                runs, vias = simplify(cells, grid)
                geoms = []
                for Li, rp in runs:
                    for k in range(len(rp)-1):
                        if rp[k] == rp[k+1]: continue
                        geoms.append((LineString([rp[k], rp[k+1]]).buffer(TRACE/2), (Li,)))
                for v in vias:
                    geoms.append((Point(*v).buffer(VIA_D/2), (0, 1)))
                if not all(space.clear(g, net, ls) for g, ls in geoms): continue
                got = (cells, runs, vias, gpts, gcell); break
            if got is None:
                failed += 1; fails.append((net, p["ref"], p["num"])); continue
            cells, runs, vias, gpts, gcell = got
            grid.claim(cells, net)
            connected.update(cells)
            for L, rp in runs:
                keep(space, grid, added, net, rp, L)
            keep(space, grid, added, net, gpts, gcell[0])
            for v in vias:
                added.append(via(v, net)); nvia += 1
                space.add(Point(*v).buffer(VIA_D/2), net, (0, 1))
                grid.block(Point(*v).buffer(VIA_D/2), net=net, layers=(0, 1))
            done += 1
    return added, done, failed, fails, nvia

def route_board(path, label, step=GRID, tries=1, seed=7):
    """Route a board, keeping the best of several net orderings.

    One pass is greedy: an early net can wall off a later one for no better
    reason than that it was shorter.  There is no rip-up here, so instead the
    order is reshuffled and the best result kept -- worth doing on the
    daughterboard, which is dense but quick, and not on the halves, which are
    neither."""
    b, pads, outline, keepout = read(path)
    base = netlist(pads)
    rng = random.Random(seed)
    best = None
    for t in range(max(1, tries)):
        order = base if t == 0 else rng.sample(base, len(base))
        r = plan(pads, outline, step, order, keepout)
        if best is None or r[1] > best[1]: best = r
        if best[2] == 0: break
    added, done, failed, fails, nvia = best
    added = list(added)
    added.append(zone(outline, "GND", "F.Cu"))
    added.append(zone(outline, "GND", "B.Cu"))
    # drop any copper from an earlier pass, so running this twice replaces the
    # routing instead of laying a second set of traces on top of the first
    body = [c for c in b[1:]
            if not (isinstance(c, list) and c[0] in ("segment", "via", "zone", "arc"))]
    open(path, "w").write(dumps([Sym("kicad_pcb")] + body[:-1] + added + [body[-1]]) + "\n")
    return done, failed, fails, len([a for a in added if a[0] == "segment"]), nvia

if __name__ == "__main__":
    for name, step, tries in (("Symm60HE-Left", 0.5, 3), ("Symm60HE-Right", 0.5, 3),
                              ("Symm60HE-Daughterboard", 0.25, 4)):
        d, f, fl, ns, nv = route_board("../pcb/%s.kicad_pcb" % name, name, step, tries)
        print("%-24s %4d segments, %3d vias | %d routed, %d unrouted%s"
              % (name, ns, nv, d, f,
                 ("  " + ", ".join("%s@%s.%s" % x for x in fl[:4])) if fl else ""))
