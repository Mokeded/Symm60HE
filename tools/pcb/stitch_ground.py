#!/usr/bin/env python3
"""Add checked GND pad taps and plane-stitching vias to a routed board."""

import argparse
import sys
from pathlib import Path

from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preroute_nets import edge_cutout_keepout
from repair_open_routes import add_existing_copper
import route
from route import (Space, lane, pad_layers, read, stitch)
from router import Grid
from sexp import Sym, dumps


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    parser.add_argument("--step", type=float, default=0.25)
    args = parser.parse_args()

    # KiCad's active copper-clearance rule on these boards is 0.20 mm.  The
    # general maze router intentionally uses a 0.15 mm fabrication minimum,
    # but ground taps must satisfy the actual project DRC rule.
    route.CLEAR = 0.20
    pad_margin = route.TRACE / 2 + route.CLEAR

    board_expr, pads, outline, drawing_keepout = read(args.board)
    cutouts = edge_cutout_keepout(board_expr)
    keepouts = [g for g in (drawing_keepout, cutouts) if g is not None]
    keepout = unary_union(keepouts) if keepouts else None
    grid = Grid(outline, step=args.step)
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
    add_existing_copper(board_expr, grid, space)

    added = []
    # A pad already on one pour can still sit on an isolated island.  Give
    # bottom pads a checked path to the top pour and vice versa.
    bottom_to_top = stitch(grid, space, added, pads, "GND", "F.Cu")
    top_to_bottom = stitch(grid, space, added, pads, "GND", "B.Cu")
    # Finally ensure the two otherwise independent pours share distributed
    # ground references even where no component pad forces a connection.
    bridge = stitch(grid, space, added, pads, "GND", "F.Cu",
                    spacing=12.0, bridge=True)

    body = board_expr[1:]
    Path(args.output).write_text(
        dumps([Sym("kicad_pcb")] + body[:-1] + added + [body[-1]]) + "\n")
    print("bottom-to-top", bottom_to_top, "top-to-bottom", top_to_bottom,
          "bridge", bridge, "objects", len(added))


if __name__ == "__main__":
    main()
