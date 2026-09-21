#!/usr/bin/env python3
"""Mirror every text object plotted on a back-side PCB layer.

KiCad expects text on B.Silkscreen/B.Fab to carry an explicit mirrored
justification.  This is presentation metadata only; component placement,
copper and board geometry are unchanged.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import Sym, dumps, first, loads  # noqa: E402


TEXT_KINDS = {"property", "fp_text", "gr_text", "gr_text_box"}


def visit(node):
    changed = 0
    if isinstance(node, list) and node:
        if str(node[0]) in TEXT_KINDS:
            layer = first(node, "layer")
            effects = first(node, "effects")
            if (layer and str(layer[1]).startswith("B.") and effects):
                justify = first(effects, "justify")
                if justify is None:
                    effects.append([Sym("justify"), Sym("mirror")])
                    changed += 1
                elif not any(str(value) == "mirror" for value in justify[1:]):
                    justify.append(Sym("mirror"))
                    changed += 1
        for child in node[1:]:
            changed += visit(child)
    return changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    board = loads(args.board.read_text())
    changed = visit(board)
    args.output.write_text(dumps(board) + "\n")
    print(f"{args.board.name}: mirrored {changed} back-side text object(s)")


if __name__ == "__main__":
    main()
