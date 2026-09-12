#!/usr/bin/env python3
"""Add uninterrupted inner power planes and conservative GND stitching.

The signal router is intentionally limited to F.Cu/B.Cu.  On a dense switch
field those traces can split an outer-layer pour into islands, so the release
boards use a four-layer 1.2 mm stack: In1.Cu is GND; In2.Cu is +3V3A on the
halves and a second GND plane on the daughterboard.  Existing through vias
connect the analog-supply taps to In2.  The separate ``stitch_islands.py``
pass adds only the vias that the refilled outer pours actually need.
"""
import math
import sys
from pathlib import Path

from shapely.geometry import LineString, Point

sys.path.insert(0, str(Path(__file__).resolve().parent))
from route import (VIA_D, LAYERS, Space, entries, pad_layers, read, seg, via,
                   zone)  # noqa: E402
from sexp import Sym, dumps, find, first, loads  # noqa: E402


PITCH = 12.0
EDGE = 1.0
SHARE = 3.5


def copper_space(board, pads):
    space = Space()
    for pad in pads:
        space.add(pad["geom"], pad["net"] or ("#pad-%d" % id(pad)),
                  (0, 1) if pad["thru"] else ((0,) if pad["layer"] == "B.Cu" else (1,)))
    for item in find(board, "segment"):
        start, end = first(item, "start"), first(item, "end")
        width, layer, net = first(item, "width"), first(item, "layer"), first(item, "net")
        which = 0 if layer[1] == "B.Cu" else 1
        geom = LineString([(float(start[1]), float(start[2])),
                           (float(end[1]), float(end[2]))]).buffer(float(width[1]) / 2)
        space.add(geom, net[1], (which,))
    for item in find(board, "via"):
        at, size, net = first(item, "at"), first(item, "size"), first(item, "net")
        space.add(Point(float(at[1]), float(at[2])).buffer(float(size[1]) / 2),
                  net[1], (0, 1))
    return space


def existing_vias(board):
    result = []
    for item in find(board, "via"):
        at, net = first(item, "at"), first(item, "net")
        result.append((float(at[1]), float(at[2]), net[1]))
    return result


def pad_taps(board, pads, outline, space, plane_nets):
    """Give each small group of SMD plane pads a checked through-via escape."""
    added = []
    anchors = existing_vias(board)
    safe = outline.buffer(-EDGE)
    for pad in sorted((p for p in pads if p["net"] in plane_nets and not p["thru"]),
                      key=lambda p: (p["y"], p["x"])):
        if any(n == pad["net"] and math.hypot(x-pad["x"], y-pad["y"]) <= SHARE
               for x, y, n in anchors):
            continue
        placed = False
        for x, y in entries(pad)[:-1]:
            copper = Point(x, y).buffer(VIA_D / 2)
            stub = LineString([(pad["x"], pad["y"]), (x, y)]).buffer(0.1)
            if not safe.contains(copper):
                continue
            if not space.clear(copper, pad["net"], (0, 1)):
                continue
            if not space.clear(stub, pad["net"], pad_layers(pad)):
                continue
            layer_index = pad_layers(pad)[0]
            added.append(seg((pad["x"], pad["y"]), (x, y), pad["net"],
                             LAYERS[layer_index]))
            added.append(via((x, y), pad["net"]))
            space.add(stub, pad["net"], (layer_index,))
            space.add(copper, pad["net"], (0, 1))
            anchors.append((x, y, pad["net"]))
            placed = True
            break
        if not placed:
            print("warning: no clear plane tap for %s.%s (%s)" %
                  (pad["ref"], pad["num"], pad["net"]))
    return added


def add_planes(path, daughterboard=False):
    board, pads, outline, _ = read(path)
    layers = first(board, "layers")
    names = {item[1] for item in layers[1:] if isinstance(item, list) and len(item) > 1}
    missing = {"In1.Cu", "In2.Cu"}.difference(names)
    if missing:
        raise RuntimeError("%s is not a four-layer board (missing %s)" %
                           (path, ", ".join(sorted(missing))))

    # Idempotent when used after a fresh generator/router run.
    def is_inner_zone(item):
        if not (isinstance(item, list) and item and item[0] == "zone"):
            return False
        layer = first(item, "layers") or first(item, "layer")
        return layer is not None and layer[1] in ("In1.Cu", "In2.Cu")

    board[1:] = [item for item in board[1:] if not is_inner_zone(item)]

    added = [zone(outline, "GND", "In1.Cu")]
    added.append(zone(outline, "GND" if daughterboard else "+3V3A", "In2.Cu"))

    insert = next((i for i in range(len(board) - 1, 0, -1)
                   if isinstance(board[i], list) and board[i] and
                   board[i][0] == "embedded_fonts"), len(board))
    board[insert:insert] = added
    Path(path).write_text(dumps(board) + "\n")
    print("%-40s 2 uninterrupted inner planes" % Path(path).name)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    for name in ("Symm60HE-Left", "Symm60HE-Right", "Symm60HE-Daughterboard"):
        add_planes(root / "pcb" / (name + ".kicad_pcb"),
                   daughterboard=name.endswith("Daughterboard"))
