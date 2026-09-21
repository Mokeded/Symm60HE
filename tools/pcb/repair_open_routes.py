#!/usr/bin/env python3
"""Route the non-GND open pairs in a KiCad DRC report around existing copper."""

import argparse
import math
import os
import re
import sys
import uuid
from pathlib import Path

from shapely.geometry import LineString, Point, box as sbox

sys.path.insert(0, str(Path(__file__).resolve().parent))
import route as route_module
from route import (CLEAR, PAD_MARGIN, TRACE, VIA_D, LAYERS, Space, keep,
                   lane, pad_layers, read, rot, seg, via)
from router import Grid, simplify
from sexp import Sym, dumps, find, first


ITEM = re.compile(
    r"@\(([-0-9.]+) mm, ([-0-9.]+) mm\): .* \[([^]]+)\].* on ([FB]\.Cu)")


def num(expr, name, index=1):
    item = first(expr, name)
    return float(item[index])


def layer_index(name):
    return LAYERS.index(name)


def endpoint_cells(grid, space, point, layer, net, radius=48):
    i0, j0 = grid.cell(*point)
    out = []
    for dj in range(-radius, radius + 1):
        for di in range(-radius, radius + 1):
            i, j = i0 + di, j0 + dj
            if not grid.passable(i, j, layer, net):
                continue
            p = grid.pos(i, j)
            line = LineString([point, p])
            if point != p and not space.clear(line.buffer(TRACE / 2), net,
                                               (layer,)):
                continue
            out.append((math.hypot(p[0] - point[0], p[1] - point[1]),
                        (layer, i, j), p))
    out.sort()
    return out[:128]


def add_existing_copper(board_expr, grid, space):
    for item in find(board_expr, "segment"):
        start = first(item, "start")
        end = first(item, "end")
        width = num(item, "width")
        layer = first(item, "layer")[1]
        net = first(item, "net")[1]
        geom = LineString([(float(start[1]), float(start[2])),
                           (float(end[1]), float(end[2]))]).buffer(width / 2)
        li = layer_index(layer)
        grid.block(geom, net=net, layers=(li,))
        space.add(geom, net, (li,))
    for item in find(board_expr, "via"):
        at = first(item, "at")
        size = num(item, "size")
        net = first(item, "net")[1]
        geom = Point(float(at[1]), float(at[2])).buffer(size / 2)
        grid.block(geom, net=net, layers=(0, 1))
        space.add(geom, net, (0, 1))


def add_edge_cutouts(board_expr, grid, space):
    """Reserve reverse-mount LED openings on both copper layers."""
    for fp in find(board_expr, "footprint"):
        edge_items = []
        for kind in ("fp_line", "fp_arc"):
            for item in find(fp, kind):
                layer = first(item, "layer")
                if layer and layer[1] == "Edge.Cuts":
                    edge_items.append(item)
        if not edge_items:
            continue
        at = first(fp, "at")
        fx, fy = float(at[1]), float(at[2])
        angle = float(at[3]) if len(at) > 3 else 0.0
        points = []
        for item in edge_items:
            for name in ("start", "mid", "end"):
                p = first(item, name)
                if p:
                    dx, dy = rot(float(p[1]), float(p[2]), angle)
                    points.append((fx + dx, fy + dy))
        if not points:
            continue
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        opening = sbox(min(xs), min(ys), max(xs), max(ys))
        # DRC requires 0.25 mm from copper edge to the cutout.  Space.clear
        # already supplies 0.15 mm and half the trace supplies 0.10 mm.
        grid.block(opening, net="#edge", margin=0.25 + TRACE / 2,
                   layers=(0, 1))
        space.add(opening.buffer(0.10), "#edge", (0, 1))


def route_pair(grid, space, added, p0, layer0, p1, layer1, net):
    starts = endpoint_cells(grid, space, p0, layer0, net)
    goals = endpoint_cells(grid, space, p1, layer1, net)
    if not starts or not goals:
        print("  no endpoint cells", net, p0, layer0, len(starts),
              p1, layer1, len(goals))
        return False
    active_starts = list(starts)
    active_goals = list(goals)
    accepted = None
    for attempt in range(32):
        path = grid.route([s[1] for s in active_starts],
                          [g[1] for g in active_goals], net)
        if path is None:
            break
        start_map = {s[1]: s[2] for s in active_starts}
        goal_map = {g[1]: g[2] for g in active_goals}
        start_point = start_map[path[0]]
        goal_point = goal_map[path[-1]]
        runs, vias = simplify(path, grid)
        geometries = []
        if p0 != start_point:
            geometries.append((LineString([p0, start_point]).buffer(TRACE / 2),
                               (layer0,)))
        if p1 != goal_point:
            geometries.append((LineString([goal_point, p1]).buffer(TRACE / 2),
                               (layer1,)))
        for li, points in runs:
            for a, b in zip(points, points[1:]):
                if a != b:
                    geometries.append((LineString([a, b]).buffer(TRACE / 2),
                                       (li,)))
        for via_point in vias:
            geometries.append((Point(*via_point).buffer(VIA_D / 2), (0, 1)))
        exact_clear = all(space.clear(geom, net, layers)
                          for geom, layers in geometries)
        if exact_clear or os.environ.get("SYMM60_ALLOW_GRID_ONLY") == "1":
            accepted = (path, start_point, goal_point, runs, vias)
            break
        # The multi-source search chose the geometrically closest escape pair,
        # but the straight connector from that cell can graze fine-pitch
        # copper.  Exclude the chosen end alternately and try another legal
        # escape without changing the grid or existing route.
        if attempt % 2 == 0 and len(active_starts) > 1:
            active_starts = [s for s in active_starts if s[1] != path[0]]
        elif len(active_goals) > 1:
            active_goals = [g for g in active_goals if g[1] != path[-1]]
        else:
            break
    if accepted is None:
        print("  no exact-clearance grid path", net, p0, layer0,
              p1, layer1)
        return False
    path, start_point, goal_point, runs, vias = accepted

    if p0 != start_point:
        keep(space, grid, added, net, [p0, start_point], layer0)
    grid.claim(path, net)
    for li, points in runs:
        keep(space, grid, added, net, points, li)
    if p1 != goal_point:
        keep(space, grid, added, net, [goal_point, p1], layer1)
    for point in vias:
        added.append(via(point, net))
        geom = Point(*point).buffer(VIA_D / 2)
        space.add(geom, net, (0, 1))
        grid.block(geom, net=net, layers=(0, 1))
    return True


def parse_pairs(report):
    lines = Path(report).read_text().splitlines()
    pairs = []
    for index, line in enumerate(lines):
        if not line.startswith("[unconnected_items]"):
            continue
        items = []
        for item_line in lines[index + 1:index + 5]:
            match = ITEM.search(item_line)
            if match:
                x, y, net, layer = match.groups()
                items.append(((float(x), float(y)), layer_index(layer), net))
        if (len(items) == 2 and items[0][2] == items[1][2]
                and (items[0][2] != "GND" or
                     os.environ.get("SYMM60_ROUTE_GND") == "1")):
            pairs.append((items[0], items[1]))
    return pairs


def nearby_same_net_points(board_expr, point, layer, net, radius=10.0):
    """Offer existing track vertices near a DRC representative coordinate.

    KiCad often reports a point in the middle of a track rather than its open
    vertex.  Escaping directly from that midpoint can be impossible even when
    one end of the same copper run has ample room.
    """
    out = [(0.0, point)]
    probe = Point(*point)
    for segment in find(board_expr, "segment"):
        if (str(first(segment, "net")[1]) != str(net) or
                str(first(segment, "layer")[1]) != LAYERS[layer]):
            continue
        start, end = first(segment, "start"), first(segment, "end")
        a = (float(start[1]), float(start[2]))
        b = (float(end[1]), float(end[2]))
        line = LineString((a, b))
        if line.distance(probe) > 0.25:
            continue
        for candidate in (a, b):
            distance = math.dist(point, candidate)
            if distance <= radius:
                out.append((distance, candidate))
    unique = []
    seen = set()
    for _, candidate in sorted(out):
        key = (round(candidate[0], 4), round(candidate[1], 4))
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique[:12]


def main():
    global TRACE, CLEAR, PAD_MARGIN
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("drc_report")
    parser.add_argument("output")
    parser.add_argument("--step", type=float, default=0.25)
    parser.add_argument("--trace-width", type=float, default=TRACE)
    parser.add_argument("--clearance", type=float, default=CLEAR)
    args = parser.parse_args()

    # Keep repair geometry consistent with the board/netclass used by the
    # autorouter.  The defaults preserve the historical 0.20 mm route; dense
    # boards may explicitly use the project's 0.15 mm manufacturing minimum.
    TRACE = args.trace_width
    CLEAR = args.clearance
    PAD_MARGIN = TRACE / 2 + CLEAR
    route_module.TRACE = TRACE
    route_module.CLEAR = CLEAR
    route_module.PAD_MARGIN = PAD_MARGIN

    board_expr, pads, outline, keepout = read(args.board)
    grid = Grid(outline, step=args.step)
    space = Space()
    if keepout is not None:
        grid.block(keepout, net="#keepout", margin=PAD_MARGIN)
        space.add(keepout, "#keepout", (0, 1))
    for pad in pads:
        layers = pad_layers(pad)
        grid.block(pad["geom"], net=pad["net"] or "#pad", layers=layers)
        if pad["net"]:
            grid.block(pad["geom"], net=pad["net"], margin=0,
                       layers=layers, force=True)
            escape = lane(pad)
            if escape is not None:
                grid.block(escape, net=pad["net"], margin=0,
                           layers=layers, force=True)
        space.add(pad["geom"], pad["net"] or "#pad", layers)
    add_existing_copper(board_expr, grid, space)
    add_edge_cutouts(board_expr, grid, space)

    added = []
    failures = []
    for first_item, second_item in parse_pairs(args.drc_report):
        p0, layer0, net = first_item
        p1, layer1, _ = second_item
        routed = False
        for candidate0 in nearby_same_net_points(
                board_expr, p0, layer0, net):
            for candidate1 in nearby_same_net_points(
                    board_expr, p1, layer1, net):
                if route_pair(grid, space, added, candidate0, layer0,
                              candidate1, layer1, net):
                    routed = True
                    break
            if routed:
                break
        if not routed:
            failures.append(net)

    body = board_expr[1:]
    Path(args.output).write_text(
        dumps([Sym("kicad_pcb")] + body[:-1] + added + [body[-1]]) + "\n")
    print("added", len(added), "objects; failed", len(failures),
          ", ".join(failures))


if __name__ == "__main__":
    main()
