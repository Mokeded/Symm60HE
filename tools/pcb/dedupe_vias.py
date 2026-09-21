#!/usr/bin/env python3
"""Remove exact duplicate same-net vias without changing connectivity."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import dumps, first, loads


def value(item, name):
    found = first(item, name)
    return tuple(str(part) for part in found[1:]) if found else ()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    board = loads(args.board.read_text())
    seen = {}
    removed = 0
    output = [board[0]]
    for item in board[1:]:
        if not (isinstance(item, list) and item and str(item[0]) == "via"):
            output.append(item)
            continue
        at = first(item, "at")
        coordinate = (round(float(at[1]), 4), round(float(at[2]), 4))
        signature = (value(item, "net"), value(item, "size"),
                     value(item, "drill"), value(item, "layers"))
        if coordinate in seen:
            if seen[coordinate] != signature:
                raise RuntimeError(
                    f"non-equivalent co-located vias at {coordinate}")
            removed += 1
            continue
        seen[coordinate] = signature
        output.append(item)
    args.output.write_text(dumps(output) + "\n")
    print(f"{args.board.name}: removed {removed} exact duplicate vias")


if __name__ == "__main__":
    main()
