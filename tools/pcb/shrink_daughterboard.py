#!/usr/bin/env python3
"""Create a routed daughterboard candidate with a shorter rounded outline."""
from pathlib import Path
import argparse

from shapely.geometry import box

from route import read
from sexp import Sym, dumps, first, newuuid


def edge(a, b):
    return [Sym("gr_line"), [Sym("start"), round(a[0], 5), round(a[1], 5)],
            [Sym("end"), round(b[0], 5), round(b[1], 5)],
            [Sym("stroke"), [Sym("width"), 0.1], [Sym("type"), Sym("solid")]],
            [Sym("layer"), "Edge.Cuts"], newuuid()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--height", type=float, required=True)
    parser.add_argument("--width", type=float)
    args = parser.parse_args()
    board, _, outline, _ = read(str(args.source))
    x0, y0, x1, _ = outline.bounds
    width = args.width or (x1 - x0)
    inset = ((x1 - x0) - width) / 2
    x0, x1 = x0 + inset, x1 - inset
    candidate = box(x0, y0, x1, y0 + args.height).buffer(
        -1.0, join_style=1, quad_segs=16).buffer(1.0, join_style=1, quad_segs=16)
    body = [item for item in board[1:]
            if not (isinstance(item, list) and item and item[0].startswith("gr_") and
                    first(item, "layer") and first(item, "layer")[1] == "Edge.Cuts")]
    points = list(candidate.exterior.coords)
    edges = [edge(a, b) for a, b in zip(points, points[1:])]
    insert = next(i for i, item in enumerate(body)
                  if isinstance(item, list) and item and item[0] in ("segment", "via", "zone"))
    updated = [Sym("kicad_pcb")] + body[:insert] + edges + body[insert:]
    args.output.write_text(dumps(updated) + "\n")
    print(f"wrote {args.output}: {width:.2f} x {args.height:.2f} mm")


if __name__ == "__main__":
    main()
