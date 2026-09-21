#!/usr/bin/env python3
"""Merge the generated FN40HE support footprints into a routed daughterboard.

`mkboards.py` is the source of truth for placement and connectivity. This
helper transfers only C3-C15 and R4 from a freshly generated board, preserving
all copper and user routing in the destination. The operation is idempotent.
"""
from pathlib import Path
import argparse
import copy
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import dumps, find, loads  # noqa: E402

SUPPORT_REFS = {"R4", *(f"C{i}" for i in range(3, 16))}


def reference(footprint):
    for prop in find(footprint, "property"):
        if len(prop) > 2 and prop[1] == "Reference":
            return prop[2]
    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path,
                        help="fresh mkboards.py daughterboard containing support parts")
    parser.add_argument("destination", type=Path, help="routed board to augment")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    source = loads(args.source.read_text())
    board = loads(args.destination.read_text())
    present = {reference(fp) for fp in find(board, "footprint")}
    additions = [copy.deepcopy(fp) for fp in find(source, "footprint")
                 if reference(fp) in SUPPORT_REFS and reference(fp) not in present]
    missing = SUPPORT_REFS - present - {reference(fp) for fp in additions}
    if missing:
        raise RuntimeError("generated source is missing: " + ", ".join(sorted(missing)))

    insert = next((i for i in range(len(board) - 1, 0, -1)
                   if isinstance(board[i], list) and board[i] and
                   board[i][0] == "embedded_fonts"), len(board))
    board[insert:insert] = additions
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(dumps(board) + "\n")
    for fp in additions:
        print("added", reference(fp))


if __name__ == "__main__":
    main()
