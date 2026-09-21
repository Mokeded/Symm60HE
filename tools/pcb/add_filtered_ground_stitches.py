#!/usr/bin/env python3
"""Add only new, drill-clear vias from the ground-stitch candidate pass."""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preroute_nets import edge_cutout_keepout
from repair_open_routes import add_existing_copper
import route
from route import Space, lane, pad_layers, read, stitch
from router import Grid
from sexp import Sym, dumps, find, first, loads


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    route.CLEAR = 0.20
    pad_margin = route.TRACE / 2 + route.CLEAR
    expr, pads, outline, drawing_keepout = read(args.board)
    cutouts = edge_cutout_keepout(expr)
    keepouts = [item for item in (drawing_keepout, cutouts) if item is not None]
    keepout = unary_union(keepouts) if keepouts else None
    grid = Grid(outline, step=0.25)
    space = Space()
    if keepout is not None:
        grid.block(keepout, net="#keepout", margin=pad_margin)
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
    add_existing_copper(expr, grid, space)

    candidates = []
    stitch(grid, space, candidates, pads, "GND", "F.Cu")
    stitch(grid, space, candidates, pads, "GND", "B.Cu")
    stitch(grid, space, candidates, pads, "GND", "F.Cu",
           spacing=12.0, bridge=True)
    candidate_vias = [item for item in candidates
                      if isinstance(item, list) and item and item[0] == "via"]

    # Reject every candidate that overlaps an existing drill, including an
    # already-present same-net via.  The stitch planner deliberately allows
    # same-net overlap; fabrication drill files do not.
    drill_centres = []
    source = loads(args.board.read_text())
    for item in find(source, "via"):
        at = first(item, "at")
        drill_centres.append((float(at[1]), float(at[2]),
                              float(first(item, "drill")[1]) / 2))
    for pad in pads:
        if not pad["thru"]:
            continue
        radius = min(pad["geom"].bounds[2] - pad["geom"].bounds[0],
                     pad["geom"].bounds[3] - pad["geom"].bounds[1]) / 4
        drill_centres.append((pad["x"], pad["y"], radius))

    accepted = []
    for item in candidate_vias:
        at = first(item, "at")
        point = (float(at[1]), float(at[2]))
        radius = float(first(item, "drill")[1]) / 2
        if any(math.dist(point, (x, y)) < radius + other_radius + 0.05
               for x, y, other_radius in drill_centres):
            continue
        accepted.append(item)
        drill_centres.append((point[0], point[1], radius))

    body = source[1:]
    args.output.write_text(
        dumps([Sym("kicad_pcb")] + body[:-1] + accepted + [body[-1]]) + "\n")
    print(f"added {len(accepted)} drill-clear GND stitching vias")


if __name__ == "__main__":
    main()
