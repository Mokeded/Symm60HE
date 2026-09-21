#!/usr/bin/env python3
"""Make corresponding left switch cells exact mirrors of the right layout.

The right half is authoritative.  Every corresponding switch cell on the left,
including the split spacebar, is reflected about the locked 151.209 mm
assembly axis.  Cell-owned Hall sensors, analogue capacitors, RGB LEDs and
their bypass capacitors move as rigid local clusters; routing is intentionally
left for the subsequent full-board routing pass.
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
from apply_doe_reference_tilt import (at_state, nearest_cell, reference,
                                      transform_footprint)
from make_layout_pcbs import aperture_center, stretch_footprint_connections
from sexp import Sym, dumps, find, loads

AXIS_MM = 151.209

# Physical counterparts ordered from the outside edge toward the split.
LEFT_TO_RIGHT = {
    "SWL1": "SWR5", "SWL2": "SWR3", "SWL3": "SWR2",
    "SWL4": "SWR1", "SWL5": "SWR6", "SWL6": "SWR7",
    "SWL7": "SWR8",
    "SWL8": "SWR11", "SWL9": "SWR10", "SWL10": "SWR9",
    "SWL11": "SWR12", "SWL12": "SWR13", "SWL13": "SWR14",
    "SWL14": "SWR15",
    "SWL15": "SWR18", "SWL16": "SWR17", "SWL17": "SWR16",
    "SWL18": "SWR19", "SWL19": "SWR20", "SWL20": "SWR21",
    "SWL21": "SWR25", "SWL22": "SWR23", "SWL23": "SWR22",
    "SWL24": "SWR27", "SWL25": "SWR28", "SWL26": "SWR29",
    "SWL27": "SWR34", "SWL28": "SWR33", "SWL29": "SWR32",
    "SWL30": "SWR31", "SWL31": "SWR30", "SWL32": "SWR35",
    "SWL33": "SWR36",
}

# Keep the addressable LED chain serpentine through the third key row.  The
# original numeric order put DL14 at the split end of row two and DL15 at the
# outside end of row three, forcing a 124 mm cross-board trace.  Reversing only
# the cell ownership of DL15..DL20 leaves every aperture at its intended key
# position while making both row transitions local.  Firmware consumes the
# reference/index map, so no switch or Hall-channel identity changes here.
LED_CELL_OVERRIDES = {
    "DL15": "SWL20", "DL16": "SWL19", "DL17": "SWL18",
    "DL18": "SWL17", "DL19": "SWL16", "DL20": "SWL15",
    "DL21": "SWL21", "DL22": "SWL22", "DL23": "SWL23",
    "DL24": "SWL24",
}

# The bottom Alt/space cells were the source of the visible keycap collision.
# Copy their complete local component geometry from the authoritative right
# half instead of preserving older asymmetric capacitor/LED offsets.  This
# keeps both the mechanics and the populated clearances exactly mirrored.
BOTTOM_EXACT_COUNTERPARTS = {
    "HEL32": "HER35", "CL32A": "CR35A", "CL32B": "CR35B",
    "DL30": "DR28", "CRGBL30": "CRGBR28",
    "HEL33": "HER36", "CL33A": "CR36A", "CL33B": "CR36B",
    "DL31": "DR32", "CRGBL31": "CRGBR32", "SL2": "SR3",
}


def state(row):
    return (float(row["x_mm"]), float(row["y_mm"]),
            float(row["rotation_deg"]))


def mirrored(cell):
    x, y, angle = cell
    return (round(2.0 * AXIS_MM - x, 3), round(y, 3), round(-angle, 3))


def transform_point(point, old_cell, new_cell):
    ox, oy, old_angle = old_cell
    nx, ny, new_angle = new_cell
    angle = math.radians(-(new_angle - old_angle))
    c, s = math.cos(angle), math.sin(angle)
    dx, dy = point[0] - ox, point[1] - oy
    return (nx + dx * c - dy * s, ny + dx * s + dy * c)


def move_zone_aperture_contours(board, aperture_moves):
    moved = 0
    for zone in find(board, "zone"):
        for polygon in find(zone, "polygon"):
            pts = next((item for item in polygon if isinstance(item, list) and
                        item and str(item[0]) == "pts"), None)
            xy = find(pts, "xy") if pts else []
            if not xy:
                continue
            xs = [float(point[1]) for point in xy]
            ys = [float(point[2]) for point in xy]
            if max(xs) - min(xs) >= 10.0 or max(ys) - min(ys) >= 10.0:
                continue
            center = ((min(xs) + max(xs)) / 2.0,
                      (min(ys) + max(ys)) / 2.0)
            for old_center, old_cell, new_cell in aperture_moves:
                if math.dist(center, old_center) > 0.08:
                    continue
                for point in xy:
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


def update_map(source: Path, output: Path):
    with source.open(newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        fields = reader.fieldnames
    by_ref = {row["ref"]: row for row in rows}
    old_cells = {ref: state(row) for ref, row in by_ref.items()}
    new_cells = dict(old_cells)
    for left_ref, right_ref in LEFT_TO_RIGHT.items():
        target = mirrored(old_cells[right_ref])
        new_cells[left_ref] = target
        row = by_ref[left_ref]
        # Keep sub-micron mirror precision in the source map.  KiCad will
        # quantize component placement to its manufacturing grid, but the map
        # remains an exact left/right geometry reference for 3D and audits.
        row["x_mm"] = f"{target[0]:.6f}".rstrip("0").rstrip(".")
        row["y_mm"] = f"{target[1]:.6f}".rstrip("0").rstrip(".")
        row["rotation_deg"] = f"{target[2]:.3f}".rstrip("0").rstrip(".")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return old_cells, new_cells


def direct_cell(ref):
    match = re.fullmatch(r"HEL(\d+)|CL(\d+)[AB]", ref)
    if not match:
        return None
    return "SWL" + next(value for value in match.groups()
                         if value is not None)


def migrate_board(source: Path, right_source: Path, output: Path,
                  old_cells, new_cells):
    board = loads(source.read_text())
    right_board = loads(right_source.read_text())
    right_by_ref = {reference(fp): fp for fp in find(right_board, "footprint")}
    led_cells = {}
    for footprint in find(board, "footprint"):
        ref = reference(footprint)
        if re.fullmatch(r"DL\d+", ref):
            led_cells[ref] = nearest_cell(at_state(footprint), old_cells, "Left")

    moved = []
    aperture_moves = []
    for footprint in find(board, "footprint"):
        ref = reference(footprint)
        cell_ref = direct_cell(ref)
        source_cell_ref = cell_ref
        led_match = re.fullmatch(r"DL(\d+)", ref)
        rgb_match = re.fullmatch(r"CRGBL(\d+)", ref)
        if led_match:
            source_cell_ref = led_cells[ref]
            cell_ref = LED_CELL_OVERRIDES.get(ref, source_cell_ref)
        elif rgb_match:
            led_ref = "DL" + rgb_match.group(1)
            source_cell_ref = led_cells.get(led_ref)
            cell_ref = LED_CELL_OVERRIDES.get(led_ref, source_cell_ref)
        elif ref == "RBPL29":
            cell_ref = led_cells.get("DL29")
            source_cell_ref = cell_ref
        elif ref == "SL1":
            cell_ref = "SWL21"
            source_cell_ref = cell_ref
        elif ref == "SL2":
            cell_ref = "SWL33"
            source_cell_ref = cell_ref
        if (not cell_ref or cell_ref not in new_cells or
                not source_cell_ref or source_cell_ref not in old_cells or
                old_cells[source_cell_ref] == new_cells[cell_ref]):
            continue
        old_state = at_state(footprint)
        old_aperture = (aperture_center(footprint)
                        if led_match else None)
        counterpart = BOTTOM_EXACT_COUNTERPARTS.get(ref)
        if counterpart:
            target_state = mirrored(at_state(right_by_ref[counterpart]))
            aperture_transform = (old_state, target_state)
        else:
            target_state = (
                *transform_point(old_state[:2], old_cells[source_cell_ref],
                                 new_cells[cell_ref]),
                old_state[2] + new_cells[cell_ref][2] -
                old_cells[source_cell_ref][2],
            )
            aperture_transform = (old_cells[source_cell_ref],
                                  new_cells[cell_ref])
        stretch_footprint_connections(board, footprint, old_state,
                                      target_state)
        transform_footprint(footprint, old_state, target_state)
        if old_aperture is not None:
            aperture_moves.append((old_aperture, *aperture_transform))
        moved.append((ref, cell_ref))

    # The five analogue muxes and their local bypass capacitors must occupy
    # the same proven component corridors as the authoritative right half.
    # Leaving the old left-only placement in place makes the newly mirrored
    # LEDs overlap AML2/AML3 and defeats both symmetry and DRC.
    for prefix_left, prefix_right in (("AML", "AMR"), ("CML", "CMR")):
        for index in range(1, 6):
            left_ref = f"{prefix_left}{index}"
            right_ref = f"{prefix_right}{index}"
            left_fp = next(fp for fp in find(board, "footprint")
                           if reference(fp) == left_ref)
            target = mirrored(at_state(right_by_ref[right_ref]))
            transform_footprint(left_fp, at_state(left_fp), target)
            moved.append((left_ref, right_ref))

    zone_contours = move_zone_aperture_contours(board, aperture_moves)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dumps(board) + "\n")
    print(f"{output.name}: moved {len(moved)} footprints across "
          f"{len(set(cell for _, cell in moved))} mirrored left cells and "
          f"{zone_contours} zone aperture contours")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--switch-map", type=Path,
                        default=ROOT / "Symm60HE-switch-map.csv")
    parser.add_argument("--board", type=Path,
                        default=ROOT / "pcb/Symm60HE-Left.kicad_pcb")
    parser.add_argument("--right-board", type=Path,
                        default=ROOT / "pcb/Symm60HE-Right.kicad_pcb")
    parser.add_argument("--output-map", type=Path)
    parser.add_argument("--output-board", type=Path)
    args = parser.parse_args()
    output_map = args.output_map or args.switch_map
    output_board = args.output_board or args.board
    old_cells, new_cells = update_map(args.switch_map, output_map)
    migrate_board(args.board, args.right_board, output_board,
                  old_cells, new_cells)
    print("all left switch cells, including SWL33/SL2, mirrored from right "
          f"about X={AXIS_MM:.3f} mm")


if __name__ == "__main__":
    main()
