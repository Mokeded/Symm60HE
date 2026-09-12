#!/usr/bin/env python3
"""Mirror the left-half FFC entry while preserving straight cable conductors.

JL1 originally had the same orientation as JR1.  Rotating JL1 by 180 degrees
makes the two half-board cable entries face opposite directions.  The numbered
pad nets are reversed so the net order at the physical pad row is unchanged;
short B.Cu extensions join that row to the existing routing.
"""
from pathlib import Path
import argparse
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from route import read, seg  # noqa: E402
from outline import LEFT_PCB  # noqa: E402
from sexp import Sym, dumps, find, first, loads, newuuid  # noqa: E402


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


def set_net(pad, name):
    net = first(pad, "net")
    if net is None:
        pad.append([Sym("net"), name])
    elif len(net) == 2:
        net[1] = name
    else:
        net[2] = name


def edge(a, b):
    return [Sym("gr_line"), [Sym("start"), round(a[0], 5), round(a[1], 5)],
            [Sym("end"), round(b[0], 5), round(b[1], 5)],
            [Sym("stroke"), [Sym("width"), 0.1], [Sym("type"), Sym("solid")]],
            [Sym("layer"), "Edge.Cuts"], newuuid()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--x", type=float, default=148.209,
                        help="new JL1 footprint centre (default: 148.209 mm)")
    args = parser.parse_args()

    board, _, outline, _ = read(str(args.source))
    connector = next(fp for fp in find(board, "footprint")
                     if prop(fp, "Reference") == "JL1")
    at = first(connector, "at")
    if abs(float(at[3]) - 90.0) > 1e-6:
        raise RuntimeError(f"JL1 expected at 90 degrees, found {at[3]}")

    numbered = {int(p[1]): p for p in find(connector, "pad")
                if str(p[1]).isdigit() and 1 <= int(p[1]) <= 12}
    if set(numbered) != set(range(1, 13)):
        raise RuntimeError("JL1 does not contain exactly pads 1 through 12")
    old = {number: (global_pad(connector, pad),
                    (first(pad, "net")[2] if len(first(pad, "net")) > 2
                     else first(pad, "net")[1]))
           for number, pad in numbered.items()}

    at[1] = args.x
    at[3] = 270
    for pad in find(connector, "pad"):
        pa = first(pad, "at")
        if len(pa) > 3:
            pa[3] = 270
        else:
            pa.append(270)
    for number in range(1, 13):
        set_net(numbered[number], old[13 - number][1])

    bridges = []
    for old_number in range(1, 13):
        new_pad = numbered[13 - old_number]
        start = old[old_number][0]
        end = global_pad(connector, new_pad)
        if math.dist(start, end) > 1e-5:
            bridges.append(seg(start, end, old[old_number][1], "B.Cu"))

    # Rotating about the pad-row locus moves the connector's two mechanical
    # pads toward the centre seam. Extend only the existing connector tongue;
    # this leaves 1.0 mm between the two half-board outlines.
    extended = LEFT_PCB
    edge_items = [edge(a, b) for a, b in
                  zip(extended.exterior.coords, list(extended.exterior.coords)[1:])]

    # Keep embedded_fonts last and place copper before any zones. Replace the
    # old Edge.Cuts contour with the locally extended connector tongue.
    tail = board[-1]
    body = [item for item in board[1:-1]
            if not (isinstance(item, list) and item and
                    item[0].startswith("gr_") and first(item, "layer") and
                    first(item, "layer")[1] == "Edge.Cuts")]
    insert = next((i for i, item in enumerate(body)
                   if isinstance(item, list) and item and item[0] == "zone"),
                  len(body))
    updated = ([Sym("kicad_pcb")] + body[:insert] + edge_items + bridges +
               body[insert:] + [tail])
    args.output.write_text(dumps(updated) + "\n")
    print(f"wrote {args.output}: JL1 at ({args.x:.3f}, {float(at[2]):.3f}) rot 270")
    print("reversed JL1 pin nets; added", len(bridges), "B.Cu pad-row extensions")
    print("extended the left connector tongue to x=151.209 mm")


if __name__ == "__main__":
    main()
