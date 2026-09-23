#!/usr/bin/env python3
"""Put back the copper of any net a repair attempt left unconnected.

Ripping a rule violation out and routing it again is the right move when the
router succeeds, and a disaster when it does not: the stranded remainder is
pruned leaf by leaf until a working trace has become a dead net.  Rolling the
whole board back throws away the repairs that did work, so roll back one net at
a time -- the nets KiCad still reports as open are restored from the snapshot,
and everything else keeps its new routing.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import Sym, dumps, find, first, loads

ITEM = re.compile(r"@\([-0-9.]+ mm, [-0-9.]+ mm\): .*\[([^]]+)\]")


def open_nets(report):
    lines = Path(report).read_text().splitlines()
    nets = set()
    for index, line in enumerate(lines):
        if not line.startswith("[unconnected_items]"):
            continue
        for item_line in lines[index + 1:index + 5]:
            match = ITEM.search(item_line)
            if match:
                nets.add(match.group(1))
    return nets


def net_of(item):
    net = first(item, "net")
    return str(net[1]) if net and len(net) > 1 else ""


def is_copper(item):
    return (isinstance(item, list) and item and
            str(item[0]) in ("segment", "via"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("snapshot", help="the board as it was before the rip")
    parser.add_argument("drc_report")
    parser.add_argument("output")
    args = parser.parse_args()

    nets = open_nets(args.drc_report)
    if not nets:
        Path(args.output).write_text(Path(args.board).read_text())
        print("no open nets to restore")
        return

    board = loads(Path(args.board).read_text())
    snapshot = loads(Path(args.snapshot).read_text())
    kept = [item for item in board[1:]
            if not (is_copper(item) and net_of(item) in nets)]
    restored = [item for item in snapshot[1:]
                if is_copper(item) and net_of(item) in nets]
    Path(args.output).write_text(
        dumps([Sym("kicad_pcb")] + kept + restored) + "\n")
    print(f"restored {len(restored)} copper items on "
          f"{len(nets)} still-open net(s): {', '.join(sorted(nets))}")


if __name__ == "__main__":
    main()
