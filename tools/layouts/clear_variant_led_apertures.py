#!/usr/bin/env python3
"""Remove routed copper from newly moved layout-variant LED apertures.

The deleted copper is intentionally left as DRC-visible opens.  A subsequent
`repair_open_routes.py` pass can reconnect those nets around the real cutout;
keeping the old copper would silently route through a milled opening.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from shapely.geometry import LineString, Point, box

sys.path.insert(0, str(Path(__file__).resolve().parent))
from route import read, rot
from sexp import dumps, find, first, loads


# Every LED whose aperture is moved away from the universal-board position on
# at least one fixed-layout derivative.  Copper crossing either the old route
# or the new opening is repaired after this pass.
MOVED_REFS = {
    "DL27", "DL29", "DL33", "DR29", "DR31", "DR36",
    "DR4", "DR5", "DR21", "DR22", "DR33", "DR34",
}


def reference(fp):
    for prop in find(fp, "property"):
        if len(prop) > 2 and str(prop[1]) == "Reference":
            return str(prop[2])
    return None


def opening(fp):
    at = first(fp, "at")
    fx, fy = float(at[1]), float(at[2])
    angle = float(at[3]) if len(at) > 3 else 0.0
    points = []
    for kind in ("fp_line", "fp_arc"):
        for item in find(fp, kind):
            layer = first(item, "layer")
            if not layer or str(layer[1]) != "Edge.Cuts":
                continue
            for name in ("start", "mid", "end"):
                point = first(item, name)
                if point:
                    dx, dy = rot(float(point[1]), float(point[2]), angle)
                    points.append((fx + dx, fy + dy))
    if not points:
        raise RuntimeError(f"{reference(fp)} has no Edge.Cuts aperture")
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return box(min(xs), min(ys), max(xs), max(ys))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--clearance", type=float, default=0.20)
    args = parser.parse_args()

    board = loads(args.board.read_text())
    # The generated board is text-derived from a filled universal master.
    # KiCad can otherwise retain cached filled-polygon voids for RGB
    # footprints that were removed before the CLI sees the board.  Discard
    # only those cached fill results; `finish_layout_pcbs.py` immediately asks
    # KiCad to refill both planes from the remaining real geometry.
    cleared_fills = 0
    for zone in find(board, "zone"):
        keep = []
        for item in zone:
            if (isinstance(item, list) and item and
                    str(item[0]) in ("filled_polygon", "filled_segments")):
                cleared_fills += 1
                continue
            keep.append(item)
        zone[:] = keep
    apertures = [opening(fp) for fp in find(board, "footprint")
                 if reference(fp) in MOVED_REFS]
    _, routed_pads, _, _ = read(args.board)
    moved_pads = [pad for pad in routed_pads if pad["ref"] in MOVED_REFS]
    removed = []
    output = [board[0]]
    for item in board[1:]:
        if not (isinstance(item, list) and item and
                str(item[0]) in ("segment", "via")):
            output.append(item)
            continue
        net = str(first(item, "net")[1])
        if str(item[0]) == "segment":
            start, end = first(item, "start"), first(item, "end")
            width = float(first(item, "width")[1])
            geometry = LineString(((float(start[1]), float(start[2])),
                                   (float(end[1]), float(end[2])))).buffer(width / 2)
        else:
            at = first(item, "at")
            geometry = Point(float(at[1]), float(at[2])).buffer(
                float(first(item, "size")[1]) / 2)
        aperture_hit = any(ap.buffer(args.clearance).intersects(geometry)
                           for ap in apertures)
        foreign_pad_hit = any(
            pad["net"] != net and
            pad["geom"].buffer(0.15).intersects(geometry)
            for pad in moved_pads)
        if aperture_hit or foreign_pad_hit:
            removed.append((str(item[0]), net))
        else:
            output.append(item)

    args.output.write_text(dumps(output) + "\n")
    nets = sorted({net for _, net in removed})
    print(f"removed {len(removed)} copper objects near {len(apertures)} "
          f"moved LED apertures; cleared {cleared_fills} cached zone fills; "
          f"nets: {', '.join(nets)}")


if __name__ == "__main__":
    main()
