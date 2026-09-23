#!/usr/bin/env python3
"""Clear a window of copper around the unplated holes a DRC report complains about.

A fixed-layout board puts its close-pair switches' alignment drills back on the
ordinary axis, into space the universal routing was free to use.  Removing only
the copper KiCad names leaves the router threading the same needle it just
failed, so take a small window around each offending hole instead: the nets
involved then have room to go round, and the repair pass reconnects them.

Only the holes named in the report are touched, and ground copper is left to
the pours.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from shapely.geometry import LineString, Point
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import Sym, dumps, find, first, loads

CATEGORIES = ("hole_clearance", "copper_edge_clearance")
HOLE = re.compile(r"@\(([-0-9.]+) mm, ([-0-9.]+) mm\): NPTH pad")


def flagged_holes(report):
    lines = Path(report).read_text().splitlines()
    out = []
    for index, line in enumerate(lines):
        if not any(line.startswith(f"[{name}]") for name in CATEGORIES):
            continue
        for item_line in lines[index + 1:index + 5]:
            match = HOLE.search(item_line)
            if match:
                out.append((float(match.group(1)), float(match.group(2))))
    return out


def net_of(item):
    net = first(item, "net")
    return str(net[1]) if net and len(net) > 1 else ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("drc_report")
    parser.add_argument("output")
    parser.add_argument("--radius", type=float, default=1.4,
                        help="how much room to clear around each hole (mm)")
    args = parser.parse_args()

    holes = flagged_holes(args.drc_report)
    board = loads(Path(args.board).read_text())
    if not holes:
        Path(args.output).write_text(dumps(board) + "\n")
        print("no offending holes in the report")
        return

    window = unary_union([Point(x, y).buffer(args.radius) for x, y in holes])
    kept, cut = [], 0
    for item in board[1:]:
        if (isinstance(item, list) and item and
                str(item[0]) in ("segment", "via") and net_of(item) != "GND"):
            if str(item[0]) == "via":
                at = first(item, "at")
                shape = Point(float(at[1]), float(at[2]))
            else:
                start, end = first(item, "start"), first(item, "end")
                shape = LineString([(float(start[1]), float(start[2])),
                                    (float(end[1]), float(end[2]))])
            if shape.intersects(window):
                cut += 1
                continue
        kept.append(item)
    Path(args.output).write_text(dumps([Sym("kicad_pcb")] + kept) + "\n")
    print(f"cleared {cut} copper items around {len(holes)} offending hole(s)")


if __name__ == "__main__":
    main()
