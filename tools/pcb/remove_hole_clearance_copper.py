#!/usr/bin/env python3
"""Remove exact routed copper named in KiCad clearance findings.

Pads and mechanical holes are never removed.  The resulting electrical opens
are rerouted by repair_open_routes.py and must pass a fresh strict DRC.
"""
from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import dumps, first, loads  # noqa: E402


ITEM = re.compile(
    r"@\(([-0-9.]+) mm, ([-0-9.]+) mm\): "
    r"(Track|Via) \[([^]]+)\](?: on ([FB]\.Cu))?(?:, length ([-0-9.]+) mm)?")


def distance_to_segment(point, start, end):
    px, py = point
    ax, ay = start
    bx, by = end
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.dist(point, start)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) /
                          (dx * dx + dy * dy)))
    return math.dist(point, (ax + t * dx, ay + t * dy))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--include-clearance", action="store_true",
        help="also remove tracks/vias named in ordinary clearance findings")
    parser.add_argument(
        "--category", action="append", default=[],
        help="additional DRC category whose first routed-copper item is removed")
    args = parser.parse_args()

    lines = args.report.read_text().splitlines()
    targets = []
    for index, line in enumerate(lines):
        category_names = ["hole_clearance", *args.category]
        if args.include_clearance:
            category_names.append("clearance")
        categories = tuple(f"[{name}]" for name in category_names)
        if not line.startswith(categories):
            continue
        for detail in lines[index + 1:index + 6]:
            match = ITEM.search(detail)
            if match:
                x, y, kind, net, layer, length = match.groups()
                targets.append((kind, net, layer, float(x), float(y),
                                float(length) if length else None))
                break

    board = loads(args.board.read_text())
    chosen = []
    for kind, net, layer, x, y, length in targets:
        best = None
        for item in board[1:]:
            item_kind = ("Via" if isinstance(item, list) and item and
                         str(item[0]) == "via" else
                         "Track" if isinstance(item, list) and item and
                         str(item[0]) == "segment" else None)
            if item_kind != kind:
                continue
            item_net = first(item, "net")
            if not item_net or str(item_net[1]) != net:
                continue
            if kind == "Via":
                at = first(item, "at")
                score = math.dist((x, y),
                                  (float(at[1]), float(at[2])))
            else:
                item_layer = first(item, "layer")
                if not item_layer or str(item_layer[1]) != layer:
                    continue
                start, end = first(item, "start"), first(item, "end")
                a = float(start[1]), float(start[2])
                b = float(end[1]), float(end[2])
                score = distance_to_segment((x, y), a, b)
                if length is not None:
                    score += abs(math.dist(a, b) - length)
            if best is None or score < best[0]:
                best = score, item
        if best is None or best[0] > 0.025:
            raise RuntimeError(f"could not resolve {kind} {net} at {(x, y)}")
        if all(best[1] is not item for item in chosen):
            chosen.append(best[1])

    for item in chosen:
        board.remove(item)
    args.output.write_text(dumps(board) + "\n")
    print(f"removed {len(chosen)} unique hole-clearance copper item(s)")


if __name__ == "__main__":
    main()
