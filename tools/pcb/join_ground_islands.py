#!/usr/bin/env python3
"""Tie every stranded GND pad back to the ground plane with the fewest vias.

A pour is not a net.  Moving the reverse-mount LEDs into the switches' south
RGB pockets put an aperture and four pads in the middle of several pour
corridors, which fences small patches of GND copper off from the plane;
KiCad's island removal then deletes them and the pads that fed them are left
unconnected.  Those pads cannot be reached by ordinary routing either, because
the copper that boxes them in belongs to other nets.

This tool works on the copper that is actually there.  It clusters the GND
pads, vias, tracks and filled polygons geometrically, then for each cluster
that is not the main plane it places, in order of preference:

1. a short track to a via that already reaches the plane,
2. one via -- inside the pad where nothing else fits -- into the plane on the
   opposite layer, or
3. a via into a fenced pour region plus a second via joining that region to the
   plane.

The planning fill is taken with island removal disabled, so a region KiCad
would drop still counts as a place a via may land; the board itself keeps its
own fill settings.
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

from shapely.geometry import LineString, Point, Polygon
from shapely.prepared import prep
from shapely.strtree import STRtree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from route import VIA_D, VIA_DRILL, read
from sexp import Sym, dumps, find, first, loads

TRACE = 0.20
CLEAR = 0.16          # 0.15 rule plus a rounding margin
LAYERS = ("F.Cu", "B.Cu")
APERTURE_MARGIN = 0.25
STUB_REACH = 4.0      # longest track stub to an existing plane via
VIA_REACH = 3.0       # farthest a new via may sit from its stranded pad


def other(layer):
    return "B.Cu" if layer == "F.Cu" else "F.Cu"


def refill_without_island_removal(board_path, cli):
    """Return board text refilled with every island kept (planning only)."""
    text = Path(board_path).read_text()
    patched = text.replace("(island_removal_mode 0)", "(island_removal_mode 1)")
    if "(island_removal_mode 1)" not in patched:
        patched = re.sub(r"\(fill yes\b", "(fill yes (island_removal_mode 1)",
                         patched)
    with tempfile.TemporaryDirectory(prefix="symm60he-islands-") as temp:
        work = Path(temp) / Path(board_path).name
        work.write_text(patched)
        for extra in ("kicad_pro", "kicad_prl"):
            sibling = Path(board_path).with_suffix("." + extra)
            if sibling.is_file():
                shutil.copy2(sibling, work.with_suffix("." + extra))
        table = Path(board_path).parent / "fp-lib-table"
        if table.is_file():
            shutil.copy2(table, Path(temp) / "fp-lib-table")
        subprocess.run([cli, "pcb", "drc", "--refill-zones", "--save-board",
                        "--severity-error", "-o", str(work) + ".rpt",
                        str(work)], check=False, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        return work.read_text()


def ground_fills(expr):
    fills = {layer: [] for layer in LAYERS}
    for zone in find(expr, "zone"):
        net = first(zone, "net")
        if not net or str(net[1]) != "GND":
            continue
        for polygon in find(zone, "filled_polygon"):
            layer = str(first(polygon, "layer")[1])
            if layer not in fills:
                continue
            points = [(float(p[1]), float(p[2]))
                      for p in find(first(polygon, "pts"), "xy")]
            if len(points) < 3:
                continue
            shape = Polygon(points)
            if not shape.is_valid:
                shape = shape.buffer(0)
            parts = (shape.geoms if shape.geom_type == "MultiPolygon"
                     else [shape])
            fills[layer] += [part for part in parts if part.area > 0.01]
    return fills


class Board:
    """Everything the planner needs to know about one board."""

    def __init__(self, board_path, planning_text):
        self.expr, self.pads, self.outline, _ = read(board_path)
        plan_expr = loads(planning_text)
        # Two fills: the board's own (islands already removed, so it shows what
        # is really connected) and the planning one (islands kept, so a via may
        # be planned into copper KiCad would otherwise drop and then keep).
        self.real_fills = ground_fills(self.expr)
        self.fills = ground_fills(plan_expr)
        self.trees = {layer: STRtree(self.fills[layer]) for layer in LAYERS}
        self.real_trees = {layer: STRtree(self.real_fills[layer])
                           for layer in LAYERS}
        self.inner = (self.outline.buffer(-0.6)
                      if self.outline is not None else None)
        self.obstacles = []      # (geometry, layers, net)
        for pad in self.pads:
            layers = LAYERS if pad["thru"] else (pad["layer"],)
            self.obstacles.append((pad["geom"], layers, pad["net"]))
        for footprint in find(self.expr, "footprint"):
            if "SK6812MINI-E_ReverseMount" not in str(footprint[1]):
                continue
            at = first(footprint, "at")
            angle = math.radians(-(float(at[3]) if len(at) > 3 else 0.0))
            box = [(-1.74, -1.54), (1.74, -1.54), (1.74, 1.54), (-1.74, 1.54)]
            points = [(float(at[1]) + x * math.cos(angle) - y * math.sin(angle),
                       float(at[2]) + x * math.sin(angle) + y * math.cos(angle))
                      for x, y in box]
            self.obstacles.append(
                (Polygon(points).buffer(APERTURE_MARGIN), LAYERS, "#aperture"))
        for segment in find(self.expr, "segment"):
            start, end = first(segment, "start"), first(segment, "end")
            width = float(first(segment, "width")[1])
            self.obstacles.append((
                LineString([(float(start[1]), float(start[2])),
                            (float(end[1]), float(end[2]))]).buffer(width / 2),
                (str(first(segment, "layer")[1]),),
                str(first(segment, "net")[1])))
        for via in find(self.expr, "via"):
            at = first(via, "at")
            self.obstacles.append((
                Point(float(at[1]), float(at[2])).buffer(
                    float(first(via, "size")[1]) / 2),
                LAYERS, str(first(via, "net")[1])))
        self.obstacles = [item for item in self.obstacles if item[2] != "GND"]
        self.geometries = [item[0] for item in self.obstacles]
        self.tree = STRtree(self.geometries)

    def region(self, layer, x, y):
        point = Point(x, y)
        for index in self.trees[layer].query(point):
            if self.fills[layer][index].contains(point):
                return int(index)
        return None

    def real_region(self, layer, x, y):
        """Index of the board's own filled polygon covering a point, if any."""
        point = Point(x, y)
        for index in self.real_trees[layer].query(point):
            if self.real_fills[layer][index].contains(point):
                return int(index)
        return None

    def clear(self, geometry, layers, margin=CLEAR):
        for index in self.tree.query(geometry.buffer(margin)):
            obstacle, obstacle_layers, _ = self.obstacles[index]
            if (set(obstacle_layers) & set(layers) and
                    obstacle.distance(geometry) < margin):
                return False
        return True

    def via_fits(self, x, y):
        point = Point(x, y)
        return (self.clear(point.buffer(VIA_D / 2), LAYERS) and
                (self.inner is None or self.inner.contains(point)))

    def track_fits(self, points, layer):
        return self.clear(LineString(points).buffer(TRACE / 2), (layer,))

    def occupy(self, geometry, layers):
        self.geometries.append(geometry)
        self.obstacles.append((geometry, layers, "#new"))
        self.tree = STRtree(self.geometries)


def clusters(board):
    """Union-find over GND pads, vias, tracks and fill regions."""
    nodes = []            # (kind, geometry, layers, reference)
    for pad in board.pads:
        if pad["net"] == "GND":
            nodes.append(("pad", pad["geom"], LAYERS if pad["thru"]
                          else (pad["layer"],), pad))
    for segment in find(board.expr, "segment"):
        if str(first(segment, "net")[1]) != "GND":
            continue
        start, end = first(segment, "start"), first(segment, "end")
        width = float(first(segment, "width")[1])
        nodes.append(("track",
                      LineString([(float(start[1]), float(start[2])),
                                  (float(end[1]), float(end[2]))]
                                 ).buffer(width / 2),
                      (str(first(segment, "layer")[1]),), None))
    for via in find(board.expr, "via"):
        if str(first(via, "net")[1]) != "GND":
            continue
        at = first(via, "at")
        nodes.append(("via",
                      Point(float(at[1]), float(at[2])).buffer(
                          float(first(via, "size")[1]) / 2),
                      LAYERS, (float(at[1]), float(at[2]))))
    for layer in LAYERS:
        for index, shape in enumerate(board.real_fills[layer]):
            nodes.append(("fill", shape, (layer,), (layer, index)))

    parent = list(range(len(nodes)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        a, b = root(i), root(j)
        if a != b:
            parent[b] = a

    tree = STRtree([node[1] for node in nodes])
    for i, (_, geometry, layers, _) in enumerate(nodes):
        for j in tree.query(geometry):
            j = int(j)
            if j <= i:
                continue
            if not set(layers) & set(nodes[j][2]):
                continue
            if geometry.intersects(nodes[j][1]):
                union(i, j)
    groups = {}
    for i, node in enumerate(nodes):
        groups.setdefault(root(i), []).append(node)
    ordered = sorted(groups.values(),
                     key=lambda group: sum(node[1].area for node in group),
                     reverse=True)
    # Copper with no pad on it is not an open connection; only the plane and
    # the clusters that strand a pad are interesting.
    return ordered[:1] + [group for group in ordered[1:]
                          if any(node[0] == "pad" for node in group)]


def stub_paths(x0, y0, x1, y1):
    yield [(x0, y0), (x1, y1)]
    yield [(x0, y0), (x0, y1), (x1, y1)]
    yield [(x0, y0), (x1, y0), (x1, y1)]
    dx, dy = x1 - x0, y1 - y0
    if abs(dx) > abs(dy):
        yield [(x0, y0), (x1 - math.copysign(abs(dy), dx), y0), (x1, y1)]
    else:
        yield [(x0, y0), (x0, y1 - math.copysign(abs(dx), dy)), (x1, y1)]


def plan_cluster(board, group, main, plane_vias):
    """Return (tracks, vias) joining one stranded cluster to the plane."""
    pads = [node[3] for node in group if node[0] == "pad"]
    # Copper of this cluster itself: a via landing in it needs no stub.
    own = {layer: set() for layer in LAYERS}
    for kind, geometry, layers, payload in group:
        if kind == "fill":
            own[payload[0]].add(payload[1])
    # A via anywhere on this cluster's own pour reaches every pad on it, so
    # take the whole fenced region rather than only the pad's surroundings.
    for layer in LAYERS:
        for region in sorted(own[layer]):
            spot = join_shape(board, layer, board.real_fills[layer][region],
                              main)
            if spot:
                return [], [spot]
    for pad in sorted(pads, key=lambda pad: -pad["geom"].area):
        layer = pad["layer"]
        for x, y in sorted(plane_vias,
                           key=lambda via: math.dist(via, (pad["x"], pad["y"]))):
            if math.dist((x, y), (pad["x"], pad["y"])) > STUB_REACH:
                break
            for path in stub_paths(pad["x"], pad["y"], x, y):
                if board.track_fits(path, layer):
                    return [(path, layer)], []
        spots = []
        inside = pad["geom"].buffer(-VIA_D / 2)
        if not inside.is_empty:
            x0, y0, x1, y1 = inside.bounds
            contains = prep(inside)
            steps = 0.05
            gx = x0
            while gx <= x1:
                gy = y0
                while gy <= y1:
                    if contains.contains(Point(gx, gy)):
                        spots.append((math.dist((gx, gy), (pad["x"], pad["y"])),
                                      gx, gy, True))
                    gy += steps
                gx += steps
        spots.append((0.0, pad["x"], pad["y"], True))
        reach = int(VIA_REACH / 0.1)
        for i in range(-reach, reach + 1):
            for j in range(-reach, reach + 1):
                distance = math.hypot(i, j) * 0.1
                if 0.55 <= distance <= VIA_REACH:
                    spots.append((distance, pad["x"] + i * 0.1,
                                  pad["y"] + j * 0.1, False))
        scored = []
        for distance, x, y, in_pad in sorted(spots):
            target = other(layer)
            region = board.region(target, x, y)
            if region is None:
                continue
            if in_pad:
                # The annulus may sit inside this pad's own copper; only the
                # drill and the far layer have to clear their neighbours.
                if not (board.clear(Point(x, y).buffer(VIA_D / 2), (target,)) and
                        board.clear(Point(x, y), (layer,), VIA_DRILL / 2 + 0.2)):
                    continue
                path = None
            elif board.real_region(layer, x, y) in own[layer]:
                # Already standing on this cluster's own pour.
                if not board.via_fits(x, y):
                    continue
                path = None
            else:
                if not board.via_fits(x, y):
                    continue
                path = next((candidate for candidate
                             in stub_paths(pad["x"], pad["y"], x, y)
                             if board.track_fits(candidate, layer)), None)
                if path is None:
                    continue
            if region in main[target]:
                return ([(path, layer)] if path else [], [(x, y)])
            joint = join_region(board, target, region, main)
            if joint:
                scored.append((distance, path, layer, (x, y), joint, target,
                               region))
            if len(scored) >= 6:
                break
        if scored:
            _, path, layer, spot, joint, target, region = scored[0]
            main[target].add(region)
            return ([(path, layer)] if path else [], [spot, joint])
    return None


def join_region(board, layer, region, main):
    """One via inside `region` that lands on the plane of the other layer."""
    return join_shape(board, layer, board.fills[layer][region], main)


def join_shape(board, layer, polygon, main):
    """One via inside `polygon` on `layer` that lands on the other plane."""
    shape = polygon.buffer(-(VIA_D / 2 + 0.05))
    if shape.is_empty:
        return None
    x0, y0, x1, y1 = shape.bounds
    contains = prep(shape)
    gx = x0
    while gx <= x1:
        gy = y0
        while gy <= y1:
            if (contains.contains(Point(gx, gy)) and
                    board.region(other(layer), gx, gy) in main[other(layer)] and
                    board.via_fits(gx, gy)):
                return (gx, gy)
            gy += 0.2
        gx += 0.2
    return None


def make_segment(a, b, layer):
    return [Sym("segment"),
            [Sym("start"), Sym(f"{a[0]:.6f}"), Sym(f"{a[1]:.6f}")],
            [Sym("end"), Sym(f"{b[0]:.6f}"), Sym(f"{b[1]:.6f}")],
            [Sym("width"), Sym(f"{TRACE:.2f}")],
            [Sym("layer"), layer],
            [Sym("net"), "GND"],
            [Sym("uuid"), str(uuid.uuid4())]]


def make_via(point):
    return [Sym("via"),
            [Sym("at"), Sym(f"{point[0]:.6f}"), Sym(f"{point[1]:.6f}")],
            [Sym("size"), Sym(f"{VIA_D:.2f}")],
            [Sym("drill"), Sym(f"{VIA_DRILL:.2f}")],
            [Sym("layers"), "F.Cu", "B.Cu"],
            [Sym("net"), "GND"],
            [Sym("uuid"), str(uuid.uuid4())]]


def find_kicad_cli():
    found = shutil.which("kicad-cli") or shutil.which("kicad-cli.exe")
    if found:
        return found
    raise RuntimeError("kicad-cli not found")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args()

    cli = os.environ.get("SYMM60_KICAD_CLI") or find_kicad_cli()
    source = args.board
    added_total = 0
    for _ in range(max(1, args.rounds)):
        planning = refill_without_island_removal(source, cli)
        board = Board(source, planning)
        groups = clusters(board)
        if len(groups) <= 1:
            break
        main_group = groups[0]
        main = {layer: set() for layer in LAYERS}
        plane_vias = []
        for kind, geometry, layers, payload in main_group:
            if kind == "fill":
                # Name the planning region that covers this connected copper.
                point = geometry.representative_point()
                region = board.region(payload[0], point.x, point.y)
                if region is not None:
                    main[payload[0]].add(region)
            elif kind == "via":
                plane_vias.append(payload)
        additions = []
        joined = 0
        for group in groups[1:]:
            plan = plan_cluster(board, group, main, plane_vias)
            if not plan:
                continue
            tracks, vias = plan
            for path, layer in tracks:
                for a, b in zip(path, path[1:]):
                    if a != b:
                        additions.append(make_segment(a, b, layer))
                        board.occupy(LineString([a, b]).buffer(TRACE / 2),
                                     (layer,))
            for point in vias:
                additions.append(make_via(point))
                board.occupy(Point(*point).buffer(VIA_D / 2), LAYERS)
                plane_vias.append(point)
            joined += 1
        if not additions:
            break
        body = loads(Path(source).read_text())
        Path(args.output).write_text(
            dumps([Sym("kicad_pcb")] + body[1:] + additions) + "\n")
        added_total += len(additions)
        source = args.output
        print(f"joined {joined} of {len(groups) - 1} stranded GND clusters")
    if source is not args.output and args.output != args.board:
        Path(args.output).write_text(Path(args.board).read_text())
    print(f"added {added_total} ground-joining objects")


if __name__ == "__main__":
    main()
