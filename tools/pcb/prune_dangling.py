#!/usr/bin/env python3
"""Remove exact copper items that KiCad explicitly reports as dangling."""

import argparse
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import dumps, first, loads


WARNING = re.compile(r"^\[(track_dangling|via_dangling)\]")
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
    parser.add_argument("board")
    parser.add_argument("drc_report")
    parser.add_argument("output")
    args = parser.parse_args()

    lines = Path(args.drc_report).read_text().splitlines()
    targets = []
    for index, line in enumerate(lines):
        if not WARNING.match(line):
            continue
        for detail in lines[index + 1:index + 5]:
            match = ITEM.search(detail)
            if match:
                x, y, kind, net, layer, length = match.groups()
                targets.append((kind, net, layer, float(x), float(y),
                                float(length) if length else None))
                break

    board = loads(Path(args.board).read_text())
    removed = []
    for kind, net, layer, x, y, length in targets:
        best = None
        for item in board[1:]:
            item_kind = "Via" if item and str(item[0]) == "via" else (
                "Track" if item and str(item[0]) == "segment" else None)
            if item_kind != kind:
                continue
            item_net = first(item, "net")
            if not item_net or str(item_net[1]) != net:
                continue
            if kind == "Via":
                at = first(item, "at")
                score = math.dist((x, y), (float(at[1]), float(at[2])))
            else:
                item_layer = first(item, "layer")
                if not item_layer or str(item_layer[1]) != layer:
                    continue
                start, end = first(item, "start"), first(item, "end")
                a = (float(start[1]), float(start[2]))
                b = (float(end[1]), float(end[2]))
                score = distance_to_segment((x, y), a, b)
                score += abs(math.dist(a, b) - length)
            if best is None or score < best[0]:
                best = (score, item)
        if best is None or best[0] > 0.02:
            raise RuntimeError(f"could not resolve {kind} {net} at {(x, y)}")
        board.remove(best[1])
        removed.append((kind, net, x, y))

    Path(args.output).write_text(dumps(board) + "\n")
    print(f"removed {len(removed)} exact DRC-reported dangling items")


if __name__ == "__main__":
    main()
