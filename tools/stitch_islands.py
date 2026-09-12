#!/usr/bin/env python3
"""Tie each refilled outer GND island to the uninterrupted inner GND plane.

Run this after KiCad has refilled the zones.  It inspects the actual filled
polygons, preserves islands that already contain a GND via or plated GND hole,
and adds one 0.60/0.30 mm through via to every remaining island.  Candidate
positions are checked against real F.Cu and B.Cu copper before insertion.
"""
import math
import sys
from pathlib import Path

from shapely.geometry import Point, Polygon

sys.path.insert(0, str(Path(__file__).resolve().parent))
from finalize_planes import copper_space  # noqa: E402
from route import VIA_D, read, via  # noqa: E402
from sexp import dumps, find, first  # noqa: E402


STEP = 0.25
EDGE = VIA_D / 2 + 0.02


def polygon_from_filled(item):
    pts = first(item, "pts")
    if pts is None:
        return None
    coords = [(float(p[1]), float(p[2])) for p in pts[1:]
              if isinstance(p, list) and p and p[0] == "xy"]
    if len(coords) < 3:
        return None
    poly = Polygon(coords)
    return poly.buffer(0) if not poly.is_valid else poly


def candidates(poly):
    inset = poly.buffer(-EDGE)
    if inset.is_empty:
        return
    if hasattr(inset, "geoms"):
        inset = max(inset.geoms, key=lambda p: p.area)
    rp = inset.representative_point()
    yield rp.x, rp.y
    minx, miny, maxx, maxy = inset.bounds
    cx, cy = inset.centroid.x, inset.centroid.y
    points = []
    x = math.ceil(minx / STEP) * STEP
    while x <= maxx:
        y = math.ceil(miny / STEP) * STEP
        while y <= maxy:
            p = Point(x, y)
            if inset.contains(p):
                points.append(((x-cx)**2 + (y-cy)**2, x, y))
            y += STEP
        x += STEP
    for _, x, y in sorted(points):
        yield x, y


def stitch(path):
    board, pads, _, _ = read(path)
    space = copper_space(board, pads)
    anchors = []
    for item in find(board, "via"):
        at, net = first(item, "at"), first(item, "net")
        if net is not None and net[1] == "GND":
            anchors.append(Point(float(at[1]), float(at[2])))
    for pad in pads:
        if pad["net"] == "GND" and pad["thru"]:
            anchors.append(Point(pad["x"], pad["y"]))

    added = []
    for z in find(board, "zone"):
        net = first(z, "net")
        layer = first(z, "layer") or first(z, "layers")
        if net is None or net[1] != "GND" or layer is None or layer[1] not in ("F.Cu", "B.Cu"):
            continue
        for filled in find(z, "filled_polygon"):
            poly = polygon_from_filled(filled)
            if poly is None or any(poly.covers(a) for a in anchors):
                continue
            placed = False
            for x, y in candidates(poly):
                copper = Point(x, y).buffer(VIA_D / 2)
                if space.clear(copper, "GND", (0, 1)):
                    added.append(via((x, y), "GND"))
                    space.add(copper, "GND", (0, 1))
                    anchors.append(Point(x, y))
                    placed = True
                    break
            if not placed:
                print("warning: no clear via position in %s GND island %s" %
                      (layer[1], tuple(round(v, 2) for v in poly.bounds)))

    insert = next((i for i in range(len(board) - 1, 0, -1)
                   if isinstance(board[i], list) and board[i] and
                   board[i][0] == "embedded_fonts"), len(board))
    board[insert:insert] = added
    Path(path).write_text(dumps(board) + "\n")
    print("%-40s %d minimal GND island stitches" % (Path(path).name, len(added)))


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    for name in ("Symm60HE-Left", "Symm60HE-Right", "Symm60HE-Daughterboard"):
        stitch(root / "pcb" / (name + ".kicad_pcb"))
