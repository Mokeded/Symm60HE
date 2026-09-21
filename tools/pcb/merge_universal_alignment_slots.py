#!/usr/bin/env python3
"""Replace intersecting universal-layout alignment drills with routed NPTH slots.

The paired switch positions are mutually exclusive, but their 1.75 mm
alignment holes overlap on the universal right half.  A single oval NPTH is an
unambiguous fabrication feature and preserves the full swept opening needed by
either switch position.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import Sym, dumps, find, first, loads  # noqa: E402


PAIRS = (
    ("HER24", (5.08, 0.0), "HER25", (-5.08, 0.0)),
    ("HER26", (-5.08, 0.0), "HER25", (5.08, 0.0)),
    ("HER3", (5.08, 0.0), "HER4", (-5.08, 0.0)),
    ("HER5", (-5.08, 0.0), "HER4", (5.08, 0.0)),
)


def close(a, b, tolerance=0.002):
    return math.dist(a, b) <= tolerance


def references(board):
    out = {}
    for footprint in find(board, "footprint"):
        for prop in find(footprint, "property"):
            if len(prop) > 2 and str(prop[1]) == "Reference":
                out[str(prop[2])] = footprint
                break
    return out


def fp_position(footprint):
    at = first(footprint, "at")
    if len(at) > 3 and abs(float(at[3])) > 0.001:
        raise RuntimeError("alignment-slot footprints must be unrotated")
    return float(at[1]), float(at[2])


def npth_at(footprint, local):
    matches = []
    for pad in find(footprint, "pad"):
        if len(pad) < 4 or str(pad[2]) != "np_thru_hole":
            continue
        at = first(pad, "at")
        if close((float(at[1]), float(at[2])), local):
            matches.append(pad)
    if len(matches) != 1:
        raise RuntimeError(f"expected one NPTH at {local}, found {len(matches)}")
    return matches[0]


def replace_value(expr, name, value):
    item = first(expr, name)
    if item is None:
        raise RuntimeError(f"missing {name}")
    item[1:] = value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    board = loads(args.board.read_text())
    refs = references(board)
    for owner_ref, owner_local, removed_ref, removed_local in PAIRS:
        owner, removed = refs[owner_ref], refs[removed_ref]
        owner_pad = npth_at(owner, owner_local)
        removed_pad = npth_at(removed, removed_local)
        ox, oy = fp_position(owner)
        rx, ry = fp_position(removed)
        a = (ox + owner_local[0], oy + owner_local[1])
        b = (rx + removed_local[0], ry + removed_local[1])
        center = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        span = math.dist(a, b) + 1.75
        replace_value(owner_pad, "at", [Sym(f"{center[0] - ox:.6f}"),
                                         Sym(f"{center[1] - oy:.6f}")])
        owner_pad[3] = Sym("oval")
        replace_value(owner_pad, "size", [Sym(f"{span:.6f}"), Sym("1.75")])
        replace_value(owner_pad, "drill", [Sym("oval"), Sym(f"{span:.6f}"),
                                            Sym("1.75")])
        removed.remove(removed_pad)
    args.output.write_text(dumps(board) + "\n")
    print(f"{args.board.name}: merged {len(PAIRS)} alignment-hole pairs into NPTH slots")


if __name__ == "__main__":
    main()
