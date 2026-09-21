#!/usr/bin/env python3
"""Resolve redundant close vias and off-centre via connections.

Coordinates are tied to the routed universal masters.  Every edit is exact
and idempotent; a fresh KiCad DRC remains the manufacturing acceptance gate.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import Sym, dumps, first, loads  # noqa: E402


def point(item, name):
    value = first(item, name)
    return float(value[1]), float(value[2])


def close(a, b, tolerance=0.002):
    return math.dist(a, b) <= tolerance


def remove_via(board, at, net):
    removed = 0
    for item in list(board[1:]):
        if not (isinstance(item, list) and item and str(item[0]) == "via"):
            continue
        item_net = first(item, "net")
        if (item_net and str(item_net[1]) == net and
                close(point(item, "at"), at)):
            board.remove(item)
            removed += 1
    return removed


def remove_segment(board, net, layer, a, b):
    removed = 0
    for item in list(board[1:]):
        if not (isinstance(item, list) and item and
                str(item[0]) == "segment"):
            continue
        item_net, item_layer = first(item, "net"), first(item, "layer")
        if (not item_net or str(item_net[1]) != net or not item_layer or
                str(item_layer[1]) != layer):
            continue
        start, end = point(item, "start"), point(item, "end")
        if ((close(start, a) and close(end, b)) or
                (close(start, b) and close(end, a))):
            board.remove(item)
            removed += 1
    return removed


def move_endpoint(board, net, layer, old, new):
    changed = 0
    for item in board[1:]:
        if not (isinstance(item, list) and item and
                str(item[0]) == "segment"):
            continue
        item_net, item_layer = first(item, "net"), first(item, "layer")
        if (not item_net or str(item_net[1]) != net or not item_layer or
                str(item_layer[1]) != layer):
            continue
        for name in ("start", "end"):
            value = first(item, name)
            if close((float(value[1]), float(value[2])), old):
                value[1], value[2] = new
                changed += 1
    return changed


def add_segment(board, net, layer, start, end, width=0.2):
    item = [Sym("segment"),
            [Sym("start"), start[0], start[1]],
            [Sym("end"), end[0], end[1]],
            [Sym("width"), width],
            [Sym("layer"), layer],
            [Sym("net"), net],
            [Sym("uuid"), str(uuid.uuid4())]]
    index = next((i for i in range(len(board) - 1, 0, -1)
                  if isinstance(board[i], list) and board[i] and
                  str(board[i][0]) == "embedded_fonts"), len(board))
    board.insert(index, item)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    board = loads(args.board.read_text())
    name = args.board.name
    operations = 0

    if "Left" in name:
        operations += remove_via(board, (69.7587, 79.586837), "GND")
        operations += remove_via(board, (73.4628, 77.8856), "ADC_L4")
        operations += remove_segment(board, "ADC_L4", "B.Cu",
                                     (73.4628, 77.8856), (73.5, 78.0))
        operations += move_endpoint(board, "ADC_L4", "B.Cu",
                                    (73.4628, 77.8856), (73.5, 78.0))

    elif "Right" in name:
        operations += remove_via(board, (277.0, 7.0), "VBUS")
        operations += remove_via(board, (286.2383, 8.28), "GND")
        operations += remove_via(board, (282.7383, 2.03), "GND")
        operations += remove_via(board, (294.1279, 56.5534), "HE_R35")
        operations += remove_via(board, (277.199, 1.7043), "RGB_R_04")
        operations += remove_segment(board, "RGB_R_04", "F.Cu",
                                     (276.799, 1.907), (277.199, 1.7043))
        operations += move_endpoint(board, "RGB_R_04", "B.Cu",
                                    (277.199, 1.7043), (276.799, 1.907))
        add_segment(board, "RGB_R_04", "F.Cu", (276.799, 1.907),
                    (277.533, 1.8043))
        operations += 1

        # RGB_R_06 previously relied on the annulus of one via touching three
        # nearby track endpoints.  Centre both layers on the via explicitly.
        operations += remove_segment(board, "RGB_R_06", "B.Cu",
                                     (170.9883, 12.03), (171.2, 12.5))
        operations += move_endpoint(board, "RGB_R_06", "B.Cu",
                                    (170.9883, 12.03), (170.9883, 12.28))
        operations += move_endpoint(board, "RGB_R_06", "F.Cu",
                                    (171.2, 12.5), (170.9883, 12.28))
        # Pull the F.Cu escape inward before joining the long run so it clears
        # the neighbouring reverse-LED aperture at the full 0.20 mm rule.
        for item in list(board[1:]):
            if not (isinstance(item, list) and item and
                    str(item[0]) == "segment"):
                continue
            net, layer = first(item, "net"), first(item, "layer")
            if (not net or str(net[1]) != "RGB_R_06" or not layer or
                    str(layer[1]) != "F.Cu"):
                continue
            a, b = point(item, "start"), point(item, "end")
            if close(a, (170.9883, 12.28)) and close(b, (180.7383, 12.28)):
                board.remove(item)
                add_segment(board, "RGB_R_06", "F.Cu",
                            (170.9883, 12.28), (171.4, 12.8))
                add_segment(board, "RGB_R_06", "F.Cu",
                            (171.4, 12.8), (180.7383, 12.28))
                operations += 1
                break

    args.output.write_text(dumps(board) + "\n")
    print(f"{name}: {operations} exact drill/via cleanup operation(s)")


if __name__ == "__main__":
    main()
