#!/usr/bin/env python3
"""Put the right Alt and split spacebar on the normal row pitch.

The right half is the authoritative layout.  Alt is placed exactly one
19.05 mm pitch below M on the M-row angle; the split spacebar is placed one
pitch below B on the B-row angle.  The complete Hall/LED/capacitor/stabilizer
cell moves rigidly, connected track endpoints are stretched to their new pads,
and the matching copper-zone LED-aperture contours move with the LED.

Run ``mirror_right_layout_to_left.py`` afterwards to make the complete left
key field (including its split spacebar) an exact reflection of the right.
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from make_layout_pcbs import (aperture_center, at_state, move_footprint,
                              reference)
from sexp import Sym, dumps, find, first, loads

PITCH_MM = 19.05
RIGHT_BOTTOM_DATUMS = {
    "SWR35": ("SWR27", 6.0),   # Alt exactly one pitch below M
    "SWR36": ("SWR29", 9.0),   # Space exactly one pitch below B
}
STABILIZERS = {"SR3": "SWR36"}


def state(row):
    return (float(row["x_mm"]), float(row["y_mm"]),
            float(row["rotation_deg"]))


def target_below(above, angle_deg):
    angle = math.radians(angle_deg)
    return (above[0] + math.sin(angle) * PITCH_MM,
            above[1] + math.cos(angle) * PITCH_MM,
            angle_deg)


def transform_point(point, old_cell, new_cell):
    ox, oy, old_angle = old_cell
    nx, ny, new_angle = new_cell
    angle = math.radians(-(new_angle - old_angle))
    c, s = math.cos(angle), math.sin(angle)
    dx, dy = point[0] - ox, point[1] - oy
    return (nx + dx * c - dy * s, ny + dx * s + dy * c)


def direct_cell(ref):
    match = re.fullmatch(r"HER(\d+)|CR(\d+)[AB]", ref)
    if not match:
        return None
    return "SWR" + next(value for value in match.groups()
                         if value is not None)


def nearest_cell(position, cells):
    return min((math.dist(position[:2], cell[:2]), ref)
               for ref, cell in cells.items())[1]


def polygon_center(polygon):
    pts = first(polygon, "pts")
    values = find(pts, "xy") if pts else []
    if not values:
        return None
    xs = [float(value[1]) for value in values]
    ys = [float(value[2]) for value in values]
    return ((min(xs) + max(xs)) / 2.0,
            (min(ys) + max(ys)) / 2.0,
            max(xs) - min(xs), max(ys) - min(ys))


def move_zone_aperture_contours(board, aperture_moves):
    moved = 0
    for zone in find(board, "zone"):
        for polygon in find(zone, "polygon"):
            center = polygon_center(polygon)
            if center is None or center[2] >= 10.0 or center[3] >= 10.0:
                continue
            for old_center, old_cell, new_cell in aperture_moves:
                if math.dist(center[:2], old_center) > 0.08:
                    continue
                for point in find(first(polygon, "pts"), "xy"):
                    x, y = transform_point((float(point[1]), float(point[2])),
                                           old_cell, new_cell)
                    point[1:3] = [Sym(f"{x:.6f}"), Sym(f"{y:.6f}")]
                moved += 1
                break
        zone[:] = [item for item in zone
                   if not (isinstance(item, list) and item and
                           str(item[0]) in ("filled_polygon",
                                            "filled_segments"))]
    return moved


def update_map(source, output):
    with source.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = reader.fieldnames
    by_ref = {row["ref"]: row for row in rows}
    old_cells = {ref: state(row) for ref, row in by_ref.items()}
    new_cells = dict(old_cells)
    for target_ref, (above_ref, angle) in RIGHT_BOTTOM_DATUMS.items():
        target = target_below(old_cells[above_ref], angle)
        new_cells[target_ref] = target
        row = by_ref[target_ref]
        row["x_mm"] = f"{target[0]:.6f}".rstrip("0").rstrip(".")
        row["y_mm"] = f"{target[1]:.6f}".rstrip("0").rstrip(".")
        row["rotation_deg"] = f"{target[2]:.6f}".rstrip("0").rstrip(".")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return old_cells, new_cells


def migrate_board(source, output, old_cells, new_cells):
    board = loads(source.read_text())
    fps = find(board, "footprint")
    led_cells = {}
    for fp in fps:
        ref = reference(fp)
        if ref and re.fullmatch(r"DR\d+", ref):
            led_cells[ref] = nearest_cell(at_state(fp), old_cells)

    moves = []
    aperture_moves = []
    for fp in fps:
        ref = reference(fp)
        cell_ref = direct_cell(ref)
        led_match = re.fullmatch(r"DR(\d+)", ref or "")
        rgb_match = re.fullmatch(r"CRGBR(\d+)", ref or "")
        if led_match:
            cell_ref = led_cells[ref]
        elif rgb_match:
            cell_ref = led_cells.get("DR" + rgb_match.group(1))
        elif ref in STABILIZERS:
            cell_ref = STABILIZERS[ref]
        if cell_ref not in RIGHT_BOTTOM_DATUMS:
            continue
        old_cell, new_cell = old_cells[cell_ref], new_cells[cell_ref]
        if old_cell == new_cell:
            continue
        if led_match:
            aperture_moves.append((aperture_center(fp), old_cell, new_cell))
        target = transform_point(at_state(fp)[:2], old_cell, new_cell)
        target_rotation = at_state(fp)[2] + new_cell[2] - old_cell[2]
        move_footprint(board, fp, target[0], target[1], target_rotation,
                       stretch=True)
        moves.append((ref, cell_ref))

    zone_contours = move_zone_aperture_contours(board, aperture_moves)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dumps(board) + "\n")
    print(f"{output.name}: moved {len(moves)} footprints in two bottom "
          f"cells and {zone_contours} zone aperture contours")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--switch-map", type=Path,
                        default=ROOT / "Symm60HE-switch-map.csv")
    parser.add_argument("--board", type=Path,
                        default=ROOT / "pcb/Symm60HE-Right.kicad_pcb")
    parser.add_argument("--output-map", type=Path)
    parser.add_argument("--output-board", type=Path)
    args = parser.parse_args()
    output_map = args.output_map or args.switch_map
    output_board = args.output_board or args.board
    old_cells, new_cells = update_map(args.switch_map, output_map)
    migrate_board(args.board, output_board, old_cells, new_cells)
    for ref in RIGHT_BOTTOM_DATUMS:
        print(ref, "->", tuple(round(value, 6)
                               for value in new_cells[ref]))


if __name__ == "__main__":
    main()
