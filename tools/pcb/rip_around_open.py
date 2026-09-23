#!/usr/bin/env python3
"""Clear a small window of foreign copper around an open the router cannot reach.

`repair_open_routes.py` only adds copper: it never moves what is already down,
so a pad that a neighbouring net has walled in stays unroutable no matter how
many grid offsets or via costs it is given.  Removing the foreign segments in a
small radius around the stranded endpoint turns one impossible connection into
two or three ordinary ones, which the next repair pass routes normally.

The window is deliberately small, only segments are taken (never vias, so no
layer transition disappears), and nothing is removed unless the report says the
endpoint is genuinely unconnected.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import re
import sys

from shapely.geometry import LineString, Point

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import Sym, dumps, find, first, loads

ITEM = re.compile(
    r"@\(([-0-9.]+) mm, ([-0-9.]+) mm\): (?:Pad|Track|Via) [^[]*\[([^]]+)\]")


def open_points(report, nets):
    lines = Path(report).read_text().splitlines()
    points = []
    for index, line in enumerate(lines):
        if not line.startswith("[unconnected_items]"):
            continue
        for item_line in lines[index + 1:index + 5]:
            match = ITEM.search(item_line)
            if not match:
                continue
            x, y, net = match.groups()
            if net == "GND" or (nets and net not in nets):
                continue
            points.append((float(x), float(y), net))
    return points


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("drc_report")
    parser.add_argument("output")
    parser.add_argument("--radius", type=float, default=1.6)
    parser.add_argument("--net", action="append", default=[],
                        help="limit to these nets (default: every open net)")
    args = parser.parse_args()

    board = loads(Path(args.board).read_text())
    points = open_points(args.drc_report, set(args.net))
    if not points:
        Path(args.output).write_text(dumps(board) + "\n")
        print("no open endpoints to clear")
        return

    kept = []
    removed = 0
    for item in board[1:]:
        if isinstance(item, list) and item and str(item[0]) == "segment":
            net = first(item, "net")
            name = str(net[1]) if net and len(net) > 1 else ""
            start, end = first(item, "start"), first(item, "end")
            line = LineString([(float(start[1]), float(start[2])),
                               (float(end[1]), float(end[2]))])
            if name != "GND" and any(
                    name != net_name and
                    line.distance(Point(x, y)) < args.radius
                    for x, y, net_name in points):
                removed += 1
                continue
        kept.append(item)
    Path(args.output).write_text(dumps([Sym("kicad_pcb")] + kept) + "\n")
    print(f"cleared {removed} foreign segments around "
          f"{len(points)} open endpoint(s)")


if __name__ == "__main__":
    main()
