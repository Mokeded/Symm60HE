#!/usr/bin/env python3
"""Apply exact post-router detours required by strict manufacturing DRC."""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import dumps, first, loads  # noqa: E402


def close(a, b, tolerance=0.002):
    return math.dist(a, b) <= tolerance


def coords(item, name):
    value = first(item, name)
    return float(value[1]), float(value[2])


def move_via_and_endpoints(board, net_name, old, new):
    moved = 0
    for item in board[1:]:
        if not (isinstance(item, list) and item):
            continue
        net = first(item, "net")
        if not net or str(net[1]) != net_name:
            continue
        if str(item[0]) == "via":
            at = first(item, "at")
            if close((float(at[1]), float(at[2])), old):
                at[1], at[2] = new
                moved += 1
        elif str(item[0]) == "segment":
            for endpoint in ("start", "end"):
                value = first(item, endpoint)
                if close((float(value[1]), float(value[2])), old):
                    value[1], value[2] = new
    return moved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    board = loads(args.board.read_text())
    moved = 0
    if "left" in args.board.name.lower():
        moved += move_via_and_endpoints(
            board, "RGB_L_29", (50.247, 80.1043), (50.397, 80.5043))
        moved += move_via_and_endpoints(
            board, "RGB_L_29", (50.847, 79.5043), (50.847, 79.3543))
        moved += move_via_and_endpoints(
            board, "HE_L26", (73.947, 84.3043), (73.997, 84.0543))
        moved += move_via_and_endpoints(
            board, "HE_L26", (73.647, 87.3043), (73.447, 87.1543))
    args.output.write_text(dumps(board) + "\n")
    print(f"{args.board.name}: adjusted {moved} manufacturing-route via(s)")


if __name__ == "__main__":
    main()
