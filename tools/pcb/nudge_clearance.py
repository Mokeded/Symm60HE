#!/usr/bin/env python3
"""Shift a track a few microns off its neighbour to settle a clearance finding.

Some gaps are short by less than the width of the rounding that produced them:
a trace passes a mux pad at 0.147 mm against a 0.150 mm rule, or slips by a via
at 0.117 mm.  Ripping the trace out does not help, because on a board this full
the router puts it back exactly where it was -- if it can route it at all.  What
the gap needs is what a person would do by hand: take hold of that segment and
drag it a hair.

Each offending segment is moved directly away from whatever it is too close to,
by the shortfall plus a small margin.  Its ends carry the copper that joins them
along with them, so the connection is unchanged, and a segment that lands on a
pad or via is left alone -- that end is a landing, not a corner.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import re
import sys
import uuid

from shapely.geometry import LineString, Point
from shapely.ops import nearest_points

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import Sym, dumps, find, first, loads

VIOLATION = re.compile(
    r"^\[(?:clearance|hole_clearance|copper_edge_clearance)\]: "
    r"(?:Clearance|Hole clearance|Board edge clearance) violation "
    r"\(\s*(?:board setup constraints )?(?:hole |edge )?clearance ([0-9.]+) mm; "
    r"actual ([0-9.]+) mm\)")
ITEM = re.compile(
    r"@\(([-0-9.]+) mm, ([-0-9.]+) mm\): (Track|Via|Pad|Zone|NPTH pad)"
    r"(?:[^[]*\[([^]]+)\])?(?:.*length ([0-9.]+) mm)?")


def findings(report):
    """(required, actual, items) for every clearance violation."""
    lines = Path(report).read_text().splitlines()
    out = []
    for index, line in enumerate(lines):
        match = VIOLATION.match(line)
        if not match:
            continue
        required, actual = float(match.group(1)), float(match.group(2))
        items = []
        for item_line in lines[index + 1:index + 5]:
            found = ITEM.search(item_line)
            if found:
                x, y, kind, net, length = found.groups()
                items.append((float(x), float(y), kind, net or "",
                              float(length) if length else 0.0))
        if len(items) == 2:
            out.append((required, actual, items))
    return out


def point_of(item, name):
    node = first(item, name)
    return (float(node[1]), float(node[2]))


def set_point(item, name, point):
    node = first(item, name)
    node[1:3] = [Sym(f"{point[0]:.6f}"), Sym(f"{point[1]:.6f}")]


def net_of(item):
    net = first(item, "net")
    return str(net[1]) if net and len(net) > 1 else ""


def geometry_of(item):
    if str(item[0]) == "via":
        return Point(*point_of(item, "at"))
    return LineString([point_of(item, "start"), point_of(item, "end")])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("drc_report")
    parser.add_argument("output")
    parser.add_argument("--margin", type=float, default=0.02,
                        help="how far past the rule to move (mm)")
    parser.add_argument("--limit", type=float, default=0.2,
                        help="largest shift worth making by hand (mm)")
    args = parser.parse_args()

    board = loads(Path(args.board).read_text())
    segments = [item for item in board[1:]
                if isinstance(item, list) and item and
                str(item[0]) == "segment"]

    moved = 0
    for required, actual, items in findings(args.drc_report):
        shift = required - actual + args.margin
        if shift > args.limit:
            continue
        tracks = [item for item in items if item[2] == "Track"]
        if not tracks:
            continue
        # move the shorter track; the other item stays where it is
        x, y, _, net, _ = min(tracks, key=lambda item: item[4])
        other = next(item for item in items if item[:2] != (x, y))
        # KiCad reports the point where two segments of the run meet, so take
        # whichever of them actually passes the obstacle, and bend that one.
        obstacle = Point(other[0], other[1])
        candidates = [segment for segment in segments
                      if net_of(segment) == net and
                      geometry_of(segment).distance(Point(x, y)) < 0.005]
        target = min(candidates,
                     key=lambda segment: geometry_of(segment).distance(obstacle),
                     default=None)
        if target is None:
            continue
        start, end = point_of(target, "start"), point_of(target, "end")
        span = math.dist(start, end)
        if span < 0.4:
            continue          # too short to bend without disturbing a landing
        line = geometry_of(target)
        along = min(max(line.project(obstacle), 0.18), span - 0.18)
        here = line.interpolate(along)
        dx, dy = here.x - obstacle.x, here.y - obstacle.y
        length = math.hypot(dx, dy)
        if length < 1e-9:
            continue
        dx, dy = dx / length * shift, dy / length * shift
        # Bend the segment around the obstacle instead of sliding it: the two
        # ends may be landings on a pad or a via, and those must not move.
        corner = (here.x + dx, here.y + dy)
        set_point(target, "end", corner)
        tail = [Sym("segment"),
                [Sym("start"), Sym(f"{corner[0]:.6f}"), Sym(f"{corner[1]:.6f}")],
                [Sym("end"), Sym(f"{end[0]:.6f}"), Sym(f"{end[1]:.6f}")],
                first(target, "width"),
                first(target, "layer"),
                first(target, "net"),
                [Sym("uuid"), str(uuid.uuid4())]]
        board.append(tail)
        segments.append(tail)
        moved += 1

    Path(args.output).write_text(dumps(board) + "\n")
    print(f"nudged {moved} segment(s) clear")


if __name__ == "__main__":
    main()
