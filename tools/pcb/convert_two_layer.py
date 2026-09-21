#!/usr/bin/env python3
"""Convert a routed four-layer Symm60HE board to a two-layer candidate.

Signal tracks and through vias already use only F.Cu/B.Cu.  This conversion
removes the two internal copper layers, replaces the stackup with a 1.2 mm
two-layer core, and moves the uninterrupted internal planes onto the outside:

* keyboard halves: B.Cu GND, F.Cu +3V3A
* daughterboard: B.Cu GND, F.Cu GND

KiCad must refill and save the zones after conversion; its DRC then decides
whether the external signal routing has divided either plane into islands.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import Sym, dumps, find, first, loads  # noqa: E402


def layer(name, kind=None, user_name=None):
    item = [Sym("layer"), name]
    if kind is not None:
        item.append(kind)
    if user_name is not None:
        item.append(user_name)
    return item


def convert(path):
    board = loads(path.read_text())

    layers = first(board, "layers")
    layers[1:] = [item for item in layers[1:]
                  if not (isinstance(item, list) and len(item) > 1 and
                          item[1] in ("In1.Cu", "In2.Cu"))]

    setup = first(board, "setup")
    stackup = first(setup, "stackup")
    by_name = {item[1]: item for item in stackup[1:]
               if isinstance(item, list) and item and item[0] == "layer" and
               len(item) > 1 and not str(item[1]).startswith("dielectric ")}
    tail = [item for item in stackup[1:]
            if isinstance(item, list) and item and
            item[0] in ("copper_finish", "dielectric_constraints")]
    dielectric = [Sym("layer"), "dielectric 1",
                  [Sym("type"), "core"], [Sym("thickness"), Sym("1.11")],
                  [Sym("material"), "FR4"], [Sym("epsilon_r"), Sym("4.5")],
                  [Sym("loss_tangent"), Sym("0.02")]]
    order = ("F.SilkS", "F.Paste", "F.Mask", "F.Cu")
    lower = ("B.Cu", "B.Mask", "B.Paste", "B.SilkS")
    stackup[1:] = [by_name[name] for name in order] + [dielectric] + \
                  [by_name[name] for name in lower] + tail

    moved = 0
    for zone in find(board, "zone"):
        target = first(zone, "layer") or first(zone, "layers")
        if target is None or target[1] not in ("In1.Cu", "In2.Cu"):
            continue
        old_layer = target[1]
        new_layer = "B.Cu" if old_layer == "In1.Cu" else "F.Cu"
        target[1] = new_layer
        # A saved KiCad zone also carries its layer on each filled polygon.
        def rewrite_nested(node):
            if not isinstance(node, list):
                return
            if (node and node[0] in ("layer", "layers") and len(node) > 1 and
                    node[1] == old_layer):
                node[1] = new_layer
            for child in node:
                rewrite_nested(child)
        rewrite_nested(zone)
        moved += 1

    if moved != 2:
        raise RuntimeError(f"{path}: expected two inner zones, moved {moved}")
    text = dumps(board) + "\n"
    if "In1.Cu" in text or "In2.Cu" in text:
        raise RuntimeError(f"{path}: internal-layer reference remains")
    path.write_text(text)
    print(f"{path.name}: two copper layers; external planes ready for refill")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("boards", nargs="+", type=Path)
    args = parser.parse_args()
    for board_path in args.boards:
        convert(board_path)
