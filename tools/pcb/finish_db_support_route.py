#!/usr/bin/env python3
"""Finish the two connections Freerouting cannot add to protected copper.

The support-pass route is deliberately run with all established routing
protected. Freerouting therefore leaves two same-net layer transitions open.
These explicit stitches land on the existing protected traces and add one GND
stitch in the small corner island reported after the new fan-outs are filled.
"""
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from route import seg, via  # noqa: E402
from sexp import dumps, loads  # noqa: E402


def append(board, items):
    insert = next((i for i in range(len(board) - 1, 0, -1)
                   if isinstance(board[i], list) and board[i] and
                   board[i][0] == "embedded_fonts"), len(board))
    board[insert:insert] = items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    board = loads(args.input.read_text())
    additions = [
        # Join Freerouting's B.Cu +3V3D fanout to the existing F.Cu rail.
        via((190.4340, 17.8669), "+3V3D"),
        seg((190.4340, 17.8669), (190.4340, 13.7663), "+3V3D", "F.Cu"),
        seg((190.4340, 13.7663), (190.7580, 13.4423), "+3V3D", "F.Cu"),
        # R4 to a point exactly on the established 45-degree BOOT0 trace.
        seg((176.8090, 1.7467), (177.5000, 1.0557), "BOOT0", "B.Cu"),
        seg((177.5000, 1.0557), (177.5000, -0.1706), "BOOT0", "B.Cu"),
        via((177.5000, -0.1706), "BOOT0"),
    ]
    append(board, additions)
    args.output.write_text(dumps(board) + "\n")
    print(f"added {len(additions)} support-route items")


if __name__ == "__main__":
    main()
