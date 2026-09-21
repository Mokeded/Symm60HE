#!/usr/bin/env python3
"""Pre-route selected constrained nets before the global autorouter pass."""

import argparse
import sys
from pathlib import Path

from shapely.geometry import box as sbox
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
from route import netlist, plan, read, rot
from sexp import Sym, dumps, find, first


def edge_cutout_keepout(board_expr):
    openings = []
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
                point = first(item, name)
                if point:
                    dx, dy = rot(float(point[1]), float(point[2]), angle)
                    points.append((fx + dx, fy + dy))
        if points:
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            openings.append(sbox(min(xs), min(ys), max(xs), max(ys)).buffer(0.10))
    return unary_union(openings) if openings else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    parser.add_argument("--net", action="append", required=True)
    parser.add_argument("--step", type=float, default=0.25)
    args = parser.parse_args()

    board_expr, pads, outline, drawing_keepout = read(args.board)
    cutouts = edge_cutout_keepout(board_expr)
    keepouts = [g for g in (drawing_keepout, cutouts) if g is not None]
    keepout = unary_union(keepouts) if keepouts else None
    wanted = set(args.net)
    order = [entry for entry in netlist(pads) if entry[1] in wanted]
    present = {entry[1] for entry in order}
    missing = wanted - present
    if missing:
        raise SystemExit("nets not routable/present: " + ", ".join(sorted(missing)))
    # Constrained nets are supplied in user order so paired universal-layout
    # sensors can claim their escape corridors before less critical nets.
    rank = {name: index for index, name in enumerate(args.net)}
    order.sort(key=lambda entry: rank[entry[1]])
    added, done, failed, failures, vias, _ = plan(
        pads, outline, args.step, order, keepout, planes=())
    body = board_expr[1:]
    Path(args.output).write_text(
        dumps([Sym("kicad_pcb")] + body[:-1] + added + [body[-1]]) + "\n")
    print("routed", done, "failed", failed, "vias", vias,
          ", ".join("%s@%s.%s" % failure for failure in failures))


if __name__ == "__main__":
    main()
