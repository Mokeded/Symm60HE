#!/usr/bin/env python3
"""Move the ground pours' LED-aperture holes to where the LEDs actually are.

Each reverse-mount LED opening exists twice: once as the footprint's own
Edge.Cuts aperture, and once as a small hole polygon cloned into both GND zone
outlines when the planes were first poured.  A footprint carries its Edge.Cuts
with it when it moves; the cloned hole does not, so relocating the LEDs left
every pour with a void at the old position and none at the new one.

The voids are not free.  Ground copper that is missing cannot carry a return
path, and the pads it used to feed end up needing stitch vias -- or a via in
the pad -- to reach the plane at all.  This tool drops hole polygons that no
longer match any aperture and, unless told otherwise, clones a fresh hole for
each aperture that has none, so the pours match the board again.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shapely.geometry import MultiPoint

from sexp import Sym, dumps, find, first, loads

LED_FOOTPRINT = "SK6812MINI-E_ReverseMount"
MAX_HOLE = 10.0        # a polygon larger than this is the pour outline itself
MATCH = 0.08           # a hole this close to an aperture centre is that hole's


def aperture_outline(footprint):
    """Board-space points of a footprint's Edge.Cuts opening."""
    at = first(footprint, "at")
    x, y = float(at[1]), float(at[2])
    angle = math.radians(-(float(at[3]) if len(at) > 3 else 0.0))
    points = []
    for kind in ("fp_line", "fp_arc"):
        for item in find(footprint, kind):
            layer = first(item, "layer")
            if not layer or str(layer[1]) != "Edge.Cuts":
                continue
            for name in ("start", "mid", "end"):
                node = first(item, name)
                if not node:
                    continue
                lx, ly = float(node[1]), float(node[2])
                points.append((x + lx * math.cos(angle) - ly * math.sin(angle),
                               y + lx * math.sin(angle) + ly * math.cos(angle)))
    return points


def centre_of(points):
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)


def hole_polygon(points, margin):
    """A hole polygon following the aperture itself, plus `margin`.

    The opening rotates with its key, so a bounding box would leave a sliver of
    copper in each corner between the box and the real cut -- narrow enough for
    KiCad to flag the pour's connection width.  Follow the aperture instead.
    """
    hull = MultiPoint(points).convex_hull
    if margin:
        hull = hull.buffer(margin, join_style=2)
    corners = list(hull.exterior.coords)[:-1]
    return [Sym("polygon"),
            [Sym("pts")] + [[Sym("xy"), Sym(f"{x:.6f}"), Sym(f"{y:.6f}")]
                            for x, y in corners]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    parser.add_argument("--margin", type=float, default=0.0,
                        help="extra clearance around each aperture (mm)")
    parser.add_argument("--no-add", action="store_true",
                        help="only drop stale holes, do not clone new ones")
    parser.add_argument("--rebuild", action="store_true",
                        help="replace every aperture hole, matching or not")
    args = parser.parse_args()

    board = loads(Path(args.board).read_text())
    apertures = []
    for footprint in find(board, "footprint"):
        if LED_FOOTPRINT not in str(footprint[1]):
            continue
        points = aperture_outline(footprint)
        if points:
            apertures.append(points)
    centres = [centre_of(points) for points in apertures]

    removed = added = 0
    for zone in find(board, "zone"):
        kept = []
        matched = set()
        for item in zone:
            if not (isinstance(item, list) and item and
                    str(item[0]) == "polygon"):
                kept.append(item)
                continue
            pts = first(item, "pts")
            xy = find(pts, "xy") if pts else []
            if not xy:
                kept.append(item)
                continue
            xs = [float(value[1]) for value in xy]
            ys = [float(value[2]) for value in xy]
            if max(xs) - min(xs) >= MAX_HOLE or max(ys) - min(ys) >= MAX_HOLE:
                kept.append(item)          # the pour outline
                continue
            centre = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
            index = next((i for i, target in enumerate(centres)
                          if math.dist(centre, target) < MATCH), None)
            if index is None or args.rebuild:
                removed += 1
                continue
            matched.add(index)
            kept.append(item)
        if not args.no_add:
            for index, points in enumerate(apertures):
                if index in matched:
                    continue
                kept.append(hole_polygon(points, args.margin))
                added += 1
        zone[:] = kept

    Path(args.output).write_text(dumps(board) + "\n")
    print(f"dropped {removed} stale aperture holes; added {added} at the "
          f"current LED positions ({len(apertures)} apertures)")


if __name__ == "__main__":
    main()
