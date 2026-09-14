#!/usr/bin/env python3
"""Give the two keyboard halves mirrored outlines and FPC-connector locations."""
from pathlib import Path
import argparse
import math
import sys

from shapely.affinity import scale
from shapely.geometry import box as sbox
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
from outline import axis_mm, round_pcb_outer_corners  # noqa: E402
from route import read, seg, via  # noqa: E402
from sexp import Sym, dumps, find, first, newuuid  # noqa: E402

RIGHT_FFC_X = 154.209
LEFT_FFC_X = 2 * axis_mm - RIGHT_FFC_X


def prop(fp, name):
    return next((p[2] for p in find(fp, "property")
                 if len(p) > 2 and p[1] == name), "")


def global_pad(fp, pad):
    at = first(fp, "at")
    pa = first(pad, "at")
    angle = math.radians(-float(at[3] if len(at) > 3 else 0.0))
    lx, ly = float(pa[1]), float(pa[2])
    return (float(at[1]) + lx * math.cos(angle) - ly * math.sin(angle),
            float(at[2]) + lx * math.sin(angle) + ly * math.cos(angle))


def edge(a, b):
    return [Sym("gr_line"), [Sym("start"), round(a[0], 5), round(a[1], 5)],
            [Sym("end"), round(b[0], 5), round(b[1], 5)],
            [Sym("stroke"), [Sym("width"), 0.1], [Sym("type"), Sym("solid")]],
            [Sym("layer"), "Edge.Cuts"], newuuid()]


def replace_outline_and_move(board, outline, connector_ref, new_x,
                             bridge_on_front=False):
    connector = next(fp for fp in find(board, "footprint")
                     if prop(fp, "Reference") == connector_ref)
    numbered = [p for p in find(connector, "pad") if str(p[1]).isdigit()]
    old = [(global_pad(connector, pad),
            (first(pad, "net")[2] if len(first(pad, "net")) > 2
             else first(pad, "net")[1]))
           for pad in numbered]
    first(connector, "at")[1] = round(new_x, 4)
    bridges = []
    for pad, (start, net) in zip(numbered, old):
        end = global_pad(connector, pad)
        if math.dist(start, end) <= 1e-5 or net == "GND":
            continue
        if bridge_on_front:
            # Keep the moved connector's fanout parallel without crossing the
            # dense B.Cu routes already occupying this strip.
            left = (end[0] + 1.0, end[1])
            # The old pad centre is already a clearance-proven landing point
            # for the existing route. Put the return via there rather than in
            # the congested fanout immediately beside it.
            right = start
            bridges.extend([seg(end, left, net, "B.Cu"), via(left, net),
                            seg(left, right, net, "F.Cu"), via(right, net)])
        else:
            bridges.append(seg(start, end, net, "B.Cu"))

    edge_items = [edge(a, b) for a, b in
                  zip(outline.exterior.coords, list(outline.exterior.coords)[1:])]
    tail = board[-1]
    body = [item for item in board[1:-1]
            if not (isinstance(item, list) and item and
                    item[0].startswith("gr_") and first(item, "layer") and
                    first(item, "layer")[1] == "Edge.Cuts")]
    insert = next((i for i, item in enumerate(body)
                   if isinstance(item, list) and item and item[0] == "zone"),
                  len(body))
    return ([Sym("kicad_pcb")] + body[:insert] + edge_items + bridges +
            body[insert:] + [tail]), len(bridges)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--left", type=Path, required=True)
    parser.add_argument("--right", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    left_board, _, left_outline, _ = read(str(args.left))
    right_board, _, right_outline, _ = read(str(args.right))
    right_mirrored = scale(right_outline, xfact=-1, yfact=1,
                           origin=(axis_mm, 0))
    shared_left = unary_union([left_outline, right_mirrored])
    shared_left = round_pcb_outer_corners(shared_left).simplify(
        0.001, preserve_topology=True)
    shared_right = scale(shared_left, xfact=-1, yfact=1,
                         origin=(axis_mm, 0))

    left_board, left_bridges = replace_outline_and_move(
        left_board, shared_left, "JL1", LEFT_FFC_X)
    right_board, right_bridges = replace_outline_and_move(
        right_board, shared_right, "JR1", RIGHT_FFC_X, bridge_on_front=True)
    left_out = args.output_dir / "Symm60HE-Left.kicad_pcb"
    right_out = args.output_dir / "Symm60HE-Right.kicad_pcb"
    left_out.write_text(dumps(left_board) + "\n")
    right_out.write_text(dumps(right_board) + "\n")
    print("axis", axis_mm, "source-outline seam", 0.0)
    print("FPC connector centres", round(LEFT_FFC_X, 4), round(RIGHT_FFC_X, 4))
    print("left outline", tuple(round(v, 4) for v in shared_left.bounds),
          "bridges", left_bridges)
    print("right outline", tuple(round(v, 4) for v in shared_right.bounds),
          "bridges", right_bridges)
    print("mirror difference",
          shared_right.symmetric_difference(scale(
              shared_left, xfact=-1, yfact=1, origin=(axis_mm, 0))).area)


if __name__ == "__main__":
    main()
