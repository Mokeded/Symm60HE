"""Grid maze router.

A* on a 0.5 mm grid over both copper layers, with vias between them.  Obstacles are pads, drills and
already-routed copper, each inflated by half a trace plus clearance.  Nets with
several terminals are grown one terminal at a time onto whatever of the net is
already down, which is a cheap Steiner approximation and good enough here.

Two layers are not a luxury: a 0.65 mm TSSOP has 0.25 mm between adjacent pads,
and a 0.25 mm trace with 0.2 mm clearance needs 0.65 mm, so an interior pin
cannot be reached on one layer at all.  It has to escape by via.
"""
import heapq, math

# The design rule is picked so that the grid itself enforces it.  Cells are
# 0.5 mm apart orthogonally and 0.7071 mm diagonally, but two traces on
# diagonally adjacent cells pass within 0.3536 mm of each other, so anything
# needing more than that could not be guaranteed by cell ownership alone.
# 0.2 mm copper with 0.15 mm clearance needs 0.35 mm centre to centre, which
# fits, and is a relaxed spec for any fabricator (0.127/0.127 is the usual
# floor).  Crossings are still possible where two diagonals cut the same gap,
# so the caller re-checks the real geometry before keeping a route.
GRID = 0.5
TRACE = 0.2
CLEAR = 0.15
SPACING = TRACE + CLEAR                 # centre to centre, trace to trace
PAD_MARGIN = TRACE / 2 + CLEAR          # trace edge to pad edge

class Grid:
    def __init__(self, poly, inset=0.6, step=GRID):
        b = poly.bounds
        self.step = step
        # A cell's diagonal neighbour has to be far enough away to hold another
        # net's trace; its orthogonal neighbour only is when the step is at
        # least SPACING, so a finer grid has to reserve a one-cell halo round
        # everything it routes.
        self.halo = step < SPACING
        assert step * 1.4142 >= SPACING - 1e-9, "grid too fine for the design rule"
        self.x0, self.y0 = b[0], b[1]
        self.nx = int((b[2] - b[0]) / step) + 2
        self.ny = int((b[3] - b[1]) / step) + 2
        area = poly.buffer(-inset)
        self.free = bytearray(self.nx * self.ny)
        from shapely.geometry import Point
        for j in range(self.ny):
            for i in range(self.nx):
                if area.contains(Point(self.x0 + i*step, self.y0 + j*step)):
                    self.free[j*self.nx + i] = 1
        n = self.nx * self.ny
        self.owner = [[None]*n, [None]*n]     # per layer: net occupying each cell
        self.LAYERS = ("B.Cu", "F.Cu")

    def idx(self, i, j): return j * self.nx + i
    def cell(self, x, y):
        return (int(round((x - self.x0) / self.step)), int(round((y - self.y0) / self.step)))
    def pos(self, i, j): return (self.x0 + i*self.step, self.y0 + j*self.step)
    def inside(self, i, j): return 0 <= i < self.nx and 0 <= j < self.ny

    def block(self, geom, net=None, margin=PAD_MARGIN, layers=(0, 1), force=False):
        """Mark cells covered by geom (plus margin) as owned by `net`.

        `force` overwrites an existing owner, which is how a pad reclaims the
        cells inside its own copper after a neighbour's margin has swept over
        them -- otherwise whichever pad happened to be blocked first would own
        the ground its neighbour has to be reached through."""
        g = geom.buffer(margin)
        b = g.bounds
        i0, j0 = self.cell(b[0], b[1]); i1, j1 = self.cell(b[2], b[3])
        from shapely.geometry import Point
        for j in range(max(0, j0-1), min(self.ny, j1+2)):
            for i in range(max(0, i0-1), min(self.nx, i1+2)):
                if g.contains(Point(*self.pos(i, j))):
                    k = self.idx(i, j)
                    for L in layers:
                        if force or self.owner[L][k] is None or net is None:
                            self.owner[L][k] = net if net is not None else "#"

    def passable(self, i, j, L, net):
        if not self.inside(i, j): return False
        k = self.idx(i, j)
        if not self.free[k]: return False
        o = self.owner[L][k]
        return o is None or o == net

    VIA_COST = 8.0

    def route(self, starts, goals, net):
        """A* over (layer, i, j).  Returns a path of (L, i, j)."""
        goalset = set(goals)
        if not starts or not goalset: return None
        gi0 = min(g[1] for g in goals)
        gi1 = max(g[1] for g in goals)
        gj0 = min(g[2] for g in goals)
        gj1 = max(g[2] for g in goals)
        def h(c):
            # Distance to the goal set's bounding box is a cheap admissible
            # lower bound.  Using the centroid makes a long routed tree look
            # farther away than it is and badly misdirects the search.
            di = gi0-c[1] if c[1] < gi0 else c[1]-gi1 if c[1] > gi1 else 0
            dj = gj0-c[2] if c[2] < gj0 else c[2]-gj1 if c[2] > gj1 else 0
            return (di + dj) * 0.9
        openq, came, best = [], {}, {}
        for s in starts:
            if not self.passable(s[1], s[2], s[0], net): continue
            best[s] = 0.0
            heapq.heappush(openq, (h(s), 0.0, s))
        NB = ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1))
        while openq:
            _, g, cur = heapq.heappop(openq)
            if cur in goalset:
                path = [cur]
                while cur in came:
                    cur = came[cur]; path.append(cur)
                return path[::-1]
            if g > best.get(cur, 1e18): continue
            L, ci, cj = cur
            for dx, dy in NB:
                nxt = (L, ci+dx, cj+dy)
                if not self.passable(nxt[1], nxt[2], L, net): continue
                if dx and dy:
                    # A diagonal step may not cut a corner, and may not slip
                    # between two occupied cells: if it could, two nets could
                    # cross each other's diagonals through the same gap and
                    # short.  Requiring both orthogonal neighbours rules out
                    # the corner cut and the crossing together, because the
                    # other net's diagonal owns exactly those two cells.
                    if not (self.passable(ci+dx, cj, L, net) and
                            self.passable(ci, cj+dy, L, net)): continue
                step = 1.0 if (dx == 0 or dy == 0) else 1.414
                if cur in came:
                    p = came[cur]
                    if p[0] == L and (ci-p[1], cj-p[2]) != (dx, dy): step += 0.4
                ng = g + step
                if ng < best.get(nxt, 1e18):
                    best[nxt] = ng; came[nxt] = cur
                    heapq.heappush(openq, (ng + h(nxt), ng, nxt))
            # change layer
            other = (1 - L, ci, cj)
            if self.passable(ci, cj, 1 - L, net):
                ng = g + self.VIA_COST
                if ng < best.get(other, 1e18):
                    best[other] = ng; came[other] = cur
                    heapq.heappush(openq, (ng + h(other), ng, other))
        return None

    def claim(self, path, net):
        for L, i, j in path:
            self.owner[L][self.idx(i, j)] = net
            if not self.halo: continue
            for di, dj in ((1,0), (-1,0), (0,1), (0,-1)):
                if not self.inside(i+di, j+dj): continue
                k = self.idx(i+di, j+dj)
                if self.owner[L][k] is None: self.owner[L][k] = net

def simplify(path, grid):
    """Split a (layer, i, j) path into per-layer runs and the vias between them.

    Returns (runs, vias) where each run is (layer_index, [points])."""
    runs, vias = [], []
    cur_layer, pts = path[0][0], [grid.pos(path[0][1], path[0][2])]
    for prev, cell in zip(path, path[1:]):
        if cell[0] != prev[0]:
            runs.append((cur_layer, pts))
            vias.append(grid.pos(cell[1], cell[2]))
            cur_layer, pts = cell[0], [grid.pos(cell[1], cell[2])]
        else:
            pts.append(grid.pos(cell[1], cell[2]))
    runs.append((cur_layer, pts))
    out = []
    for L, ps in runs:
        if len(ps) < 2:
            out.append((L, ps)); continue
        keep = [ps[0]]
        for k in range(1, len(ps)-1):
            ax, ay = keep[-1]; bx, by = ps[k]; cx, cy = ps[k+1]
            if (bx-ax)*(cy-by) != (by-ay)*(cx-bx):
                keep.append(ps[k])
        keep.append(ps[-1])
        out.append((L, keep))
    return out, vias
