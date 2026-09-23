#!/usr/bin/env python3
"""Delete the copper that a DRC report names in mechanical-rule violations.

Restoring a layout's switch-alignment holes to their ordinary axis, or moving a
footprint, can leave a track or via sitting on top of an unplated hole or too
close to the board edge.  Those are not connectivity errors, so the repair
router never sees them; it only routes what KiCad reports as an open.  Removing
exactly the copper KiCad names turns each one into an open that the next repair
pass routes properly -- which, unlike a hand nudge, keeps the rule satisfied.
"""

import argparse
import math
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import Sym, dumps, find, first, loads


CATEGORIES = ("hole_clearance", "copper_edge_clearance", "hole_to_hole",
              "holes_co_located", "clearance", "shorting_items",
              "tracks_crossing")
ITEM = re.compile(
    r"@\(([-0-9.]+) mm, ([-0-9.]+) mm\): (Track|Via) \[([^]]+)\]"
    r"(?:.*length ([0-9.]+) mm)?")


def parse(report, categories, shorter_only=False):
    """Return the (x, y, kind, net) copper items named under `categories`.

    With `shorter_only`, a violation between two pieces of copper gives up only
    the shorter one.  A clearance error is a complaint about a gap, and the
    cheapest way to widen it is to move the piece with less to lose -- ripping
    a trace that crosses the whole board to settle a 30 um gap costs a route
    the router then cannot reproduce.
    """
    lines = Path(report).read_text().splitlines()
    wanted = set()
    for index, line in enumerate(lines):
        if not any(line.startswith(f"[{name}]") for name in categories):
            continue
        found = []
        for item_line in lines[index + 1:index + 5]:
            match = ITEM.search(item_line)
            if match:
                x, y, kind, net, length = match.groups()
                found.append((float(x), float(y), kind, net,
                              float(length) if length else 0.0))
        if shorter_only and len(found) > 1:
            # Prefer moving a track over a via.  A via is a layer change the
            # rest of its net is built around -- rip it and the router usually
            # cannot reproduce the crossing, so the copper comes back exactly
            # where it was.  Among tracks, the shorter one has less to lose.
            found = [min(found, key=lambda item: (item[2] == "Via", item[4]))]
        wanted.update(item[:4] for item in found)
    return wanted


def hits(item, x, y, kind):
    name = str(item[0])
    if name == "via":
        if kind != "Via":
            return False
        at = first(item, "at")
        return math.dist((float(at[1]), float(at[2])), (x, y)) < 0.005
    if kind != "Track":
        return False
    start, end = first(item, "start"), first(item, "end")
    ax, ay = float(start[1]), float(start[2])
    bx, by = float(end[1]), float(end[2])
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    t = 0.0 if not length else max(0.0, min(1.0, ((x - ax) * dx +
                                                 (y - ay) * dy) / length))
    return math.dist((ax + t * dx, ay + t * dy), (x, y)) < 0.005


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("drc_report")
    parser.add_argument("output")
    parser.add_argument("--category", action="append", choices=CATEGORIES,
                        help="limit to these violation types")
    parser.add_argument("--shorter-only", action="store_true",
                        help="give up only the shorter piece of each pair")
    args = parser.parse_args()

    board = loads(Path(args.board).read_text())
    wanted = parse(args.drc_report, args.category or CATEGORIES,
                   args.shorter_only)
    kept = []
    removed = 0
    for item in board[1:]:
        if (isinstance(item, list) and item and
                str(item[0]) in ("segment", "via")):
            net = first(item, "net")
            name = str(net[1]) if net and len(net) > 1 else ""
            kind = "Via" if str(item[0]) == "via" else "Track"
            if any(n == name and hits(item, x, y, k)
                   for x, y, k, n in wanted if k == kind):
                removed += 1
                continue
        kept.append(item)
    Path(args.output).write_text(dumps([Sym("kicad_pcb")] + kept) + "\n")
    print(f"removed {removed} rule-violating copper items")


if __name__ == "__main__":
    main()
