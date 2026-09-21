#!/usr/bin/env python3
"""Move the daughterboard case mounts to a symmetric perimeter rectangle.

The side FPC connectors occupy most of the original 27 mm board height, so a
four-millimetre extension is added only to the bottom edge.  This creates clear
corner mounting land while preserving the existing USB-C edge and overhang.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from sexp import Sym, dumps, find, first, loads  # noqa: E402


CENTER_X = 187.209
TOP_EDGE = -6.7633
OLD_BOTTOM_EDGE = 20.2367
BOTTOM_EXTENSION = 4.0
BOTTOM_EDGE = OLD_BOTTOM_EDGE + BOTTOM_EXTENSION
CENTER_Y = (TOP_EDGE + BOTTOM_EDGE) / 2

LEFT_MOUNT = CENTER_X - 22.0
RIGHT_MOUNT = CENTER_X + 22.0
TOP_MOUNT = CENTER_Y - 12.2367
BOTTOM_MOUNT = CENTER_Y + 12.2367


def reference(fp):
    for prop in find(fp, "property"):
        if len(prop) > 2 and str(prop[1]) == "Reference":
            return str(prop[2])
    return None


def set_at(fp, x, y):
    at = first(fp, "at")
    at[1] = Sym(f"{x:.6f}")
    at[2] = Sym(f"{y:.6f}")


def pad_positions(fp):
    at = first(fp, "at")
    x, y = float(at[1]), float(at[2])
    rotation = math.radians(-(float(at[3]) if len(at) > 3 else 0.0))
    result = {}
    for pad in find(fp, "pad"):
        number = str(pad[1])
        if not number:
            continue
        pat = first(pad, "at")
        px, py = float(pat[1]), float(pat[2])
        result[number] = (
            x + px * math.cos(rotation) - py * math.sin(rotation),
            y + px * math.sin(rotation) + py * math.cos(rotation),
        )
    return result


def close(a, b, tolerance=0.0002):
    return math.dist(a, b) <= tolerance


def move_f1_with_tracks(board, fp):
    old_pads = pad_positions(fp)
    set_at(fp, 204.8, -1.6)
    new_pads = pad_positions(fp)
    changed = 0
    for item in board[1:]:
        if not (isinstance(item, list) and item and
                str(item[0]) == "segment"):
            continue
        for endpoint_name in ("start", "end"):
            endpoint = first(item, endpoint_name)
            point = (float(endpoint[1]), float(endpoint[2]))
            for number, old in old_pads.items():
                if close(point, old):
                    endpoint[1] = Sym(f"{new_pads[number][0]:.6f}")
                    endpoint[2] = Sym(f"{new_pads[number][1]:.6f}")
                    changed += 1
    if changed != 2:
        raise RuntimeError(f"expected two F1 track endpoints, changed {changed}")


def shift_bottom_point(point):
    if point and float(point[2]) > OLD_BOTTOM_EDGE - 1.1:
        point[2] = Sym(f"{float(point[2]) + BOTTOM_EXTENSION:.6f}")
        return 1
    return 0


def extend_outline_and_zones(board):
    edge_points = []
    for item in board[1:]:
        if not (isinstance(item, list) and item and
                str(item[0]).startswith("gr_")):
            continue
        layer = first(item, "layer")
        if not layer or str(layer[1]) != "Edge.Cuts":
            continue
        for name in ("start", "mid", "end"):
            point = first(item, name)
            if point:
                edge_points.append(point)
    ys = [float(point[2]) for point in edge_points]
    height = max(ys) - min(ys)
    changed = 0
    if abs(height - 27.0) < 0.01:
        changed += sum(shift_bottom_point(point) for point in edge_points)
        for zone in find(board, "zone"):
            polygons = [item for item in zone[1:]
                        if isinstance(item, list) and item and
                        str(item[0]) == "polygon"]
            if not polygons:
                raise RuntimeError("daughterboard zone has no outline polygon")
            # The daughterboard has no internal Edge.Cuts apertures.  Its
            # single zone polygon is the rounded board outline.
            for polygon in polygons:
                pts = first(polygon, "pts")
                if pts:
                    for point in find(pts, "xy"):
                        changed += shift_bottom_point(point)
    elif abs(height - 31.0) >= 0.01:
        raise RuntimeError(f"unexpected daughterboard height {height:.3f} mm")

    # Filled polygons are cached geometry.  KiCad's DRC/save pass rebuilds
    # them from the expanded zone outline and the relocated mounting holes.
    for zone in find(board, "zone"):
        zone[:] = [item for item in zone
                   if not (isinstance(item, list) and item and
                           str(item[0]) in ("filled_polygon", "filled_segments"))]
    return changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    board = loads(args.board.read_text())
    by_ref = {reference(fp): fp for fp in find(board, "footprint")}
    changed = extend_outline_and_zones(board)
    move_f1_with_tracks(board, by_ref["F1"])

    set_at(by_ref["MHD1"], LEFT_MOUNT, TOP_MOUNT)
    set_at(by_ref["MHD3"], RIGHT_MOUNT, TOP_MOUNT)
    set_at(by_ref["MHD4"], LEFT_MOUNT, BOTTOM_MOUNT)
    set_at(by_ref["MHD2"], RIGHT_MOUNT, BOTTOM_MOUNT)

    args.output.write_text(dumps(board) + "\n")
    print(
        f"outline 50.0 x {BOTTOM_EDGE - TOP_EDGE:.1f} mm; "
        f"mounts ({LEFT_MOUNT:.3f}, {TOP_MOUNT:.4f}) to "
        f"({RIGHT_MOUNT:.3f}, {BOTTOM_MOUNT:.4f}); "
        f"{changed} outline/zone points shifted; F1 moved inward"
    )


if __name__ == "__main__":
    main()
