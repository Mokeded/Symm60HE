#!/usr/bin/env python3
"""Remove copper belonging to nets this board can no longer connect.

Dropping a layout's unused switches and LEDs takes their pads with them, which
leaves some nets with a single pad and some with none at all.  Whatever copper
those nets still own cannot join anything: it is a stub by definition, it shows
up in DRC as a dangling track run after run, and a Specctra export of the board
carries nets the autorouter cannot normalise.

Nets that still have two or more pads are left alone, as are the pours.
"""

from __future__ import annotations

import argparse
import collections
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import Sym, dumps, find, first, loads


def net_of(item):
    net = first(item, "net")
    return str(net[1]) if net and len(net) > 1 else ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    parser.add_argument("--keep", action="append", default=["GND"],
                        help="never touch these nets")
    args = parser.parse_args()

    board = loads(Path(args.board).read_text())
    pads = collections.Counter()
    for footprint in find(board, "footprint"):
        for pad in find(footprint, "pad"):
            name = net_of(pad)
            if name:
                pads[name] += 1

    doomed = set()
    kept = []
    for item in board[1:]:
        if (isinstance(item, list) and item and
                str(item[0]) in ("segment", "via")):
            name = net_of(item)
            if name and name not in args.keep and pads[name] < 2:
                doomed.add(name)
                continue
        kept.append(item)

    Path(args.output).write_text(dumps([Sym("kicad_pcb")] + kept) + "\n")
    print(f"dropped copper on {len(doomed)} unconnectable net(s)"
          + (f": {', '.join(sorted(doomed))}" if doomed else ""))


if __name__ == "__main__":
    main()
