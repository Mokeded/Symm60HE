#!/usr/bin/env python3
"""Apply the image-matched DOE tilt to the live universal switch geometry.

Straight clusters remain fixed.  Tilted centres are transferred from the
1176x477 Geekhack KLE screenshot at 54 px/u and 19.05 mm/u, relative to a
straight anchor in each row.  The left and right rows are treated separately
because the supplied raster contains a real second-row asymmetry.

The active aperture/RGB placement candidate is migrated in place after a
timestamped recovery copy.  Each Hall/switch footprint, its two analogue
capacitors, its RGB LED and bypass capacitor, and any stabilizer are transformed
as a rigid cell.  Existing copper is intentionally retained as routing evidence;
the moved cells must be locally rerouted after placement approval.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import math
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from sexp import dumps, find, first, loads  # noqa: E402

PITCH_MM = 19.05
PIXELS_PER_U = 54.0
MM_PER_PIXEL = PITCH_MM / PIXELS_PER_U
SWITCH_MAP = ROOT / "Symm60HE-switch-map.csv"
DEFAULT_CANDIDATE = ROOT / "work/aperture-rgb69-two-layer-placement-candidate"

# anchor ref, anchor pixel, (moved ref, x px, y px, visual clockwise angle)
ROWS = (
    ("SWL1", (67.500, 103.500), (
        ("SWL4", 230.170, 106.272, 3),
        ("SWL5", 285.179, 112.045, 6),
        ("SWL6", 339.613, 119.781, 9),
        ("SWL7", 393.941, 128.371, 9),
    )),
    ("SWL9", (138.500, 157.500), (
        ("SWL10", 193.394, 158.411, 3),
        ("SWL11", 247.563, 163.403, 6),
        ("SWL12", 301.287, 169.030, 6),
        ("SWL13", 355.848, 177.076, 9),
        ("SWL14", 409.167, 185.448, 9),
    )),
    ("SWL16", (151.500, 211.500), (
        ("SWL17", 206.545, 213.160, 3),
        ("SWL18", 261.824, 219.166, 6),
        ("SWL19", 316.629, 226.520, 9),
        ("SWL20", 369.975, 234.996, 9),
    )),
    ("SWL22", (170.500, 265.500), (
        ("SWL23", 225.672, 268.246, 3),
        ("SWL24", 280.060, 275.427, 6),
        ("SWL25", 334.854, 284.037, 9),
        ("SWL26", 388.154, 292.524, 9),
    )),
    ("SWR5", (867.500, 111.500), (
        ("SWR1", 705.404, 112.189, -3),
        ("SWR6", 650.425, 117.034, -6),
        ("SWR7", 597.364, 123.928, -9),
        ("SWR8", 544.063, 132.410, -9),
    )),
    ("SWR9", (740.500, 165.500), (
        ("SWR12", 685.883, 167.644, -6),
        ("SWR13", 632.186, 173.270, -6),
        ("SWR14", 579.128, 181.480, -9),
        ("SWR15", 525.808, 189.951, -9),
    )),
    ("SWR17", (786.500, 219.500), (
        ("SWR16", 729.058, 220.102, -3),
        ("SWR19", 674.622, 223.098, -6),
        ("SWR20", 622.160, 229.343, -9),
        ("SWR21", 568.860, 237.785, -9),
    )),
    ("SWR23", (769.500, 273.500), (
        ("SWR22", 715.939, 274.845, -3),
        ("SWR27", 661.372, 278.779, -6),
        ("SWR28", 608.914, 286.119, -9),
        ("SWR29", 555.513, 294.577, -9),
    )),
)

STABILIZERS = {
    "Left": {"SL2": "SWL33"},
    "Right": {"SR3": "SWR36"},
}

# The steeper inner rows occupy space that the photo-matched shallow candidate
# previously used for two mux cells.  These bounded relocations were selected
# by a 0.5 mm grid search against every B.CrtYd, plated/NPTH hole, and board
# edge.  The paired decoupling capacitor retains its original 7.5 mm offset.
POST_TILT_RELOCATIONS = {
    "Left": {
        "AML3": (99.0, 79.5),
        "CML3": (106.5, 79.5),
        "CL25B": (110.0, 80.5),
    },
    "Right": {
        "AMR1": (192.5, 77.5),
        "CMR1": (200.0, 77.5),
    },
}


def read_map(path: Path):
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
        fields = stream.seek(0) or next(csv.reader(stream))
    return rows, fields


def state(row):
    return (float(row["x_mm"]), float(row["y_mm"]),
            float(row["rotation_deg"]))


def target_map(rows):
    by_ref = {row["ref"]: row for row in rows}
    targets = {}
    for anchor_ref, (anchor_px, anchor_py), members in ROWS:
        anchor_x, anchor_y, _ = state(by_ref[anchor_ref])
        for ref, px, py, visual_angle in members:
            targets[ref] = (
                round(anchor_x + (px - anchor_px) * MM_PER_PIXEL, 3),
                round(anchor_y + (py - anchor_py) * MM_PER_PIXEL, 3),
                -float(visual_angle),  # KiCad stored angle is opposite KLE visual angle.
            )

    # The universal PCB uses 2.25u rather than the reference's 3u spacebars.
    # Preserve the 1.5u modifier centre and transfer the reference's curved
    # modifier-to-space vector after subtracting the 0.75u width difference.
    left_alt = state(by_ref["SWL32"])
    reference_dx = (338.249 - 218.541) * MM_PER_PIXEL
    width_adjust = (3.0 - 2.25) * PITCH_MM / 2.0
    space_dx = reference_dx - width_adjust
    space_dy = (339.250 - 323.025) * MM_PER_PIXEL
    axis = (float(by_ref["SWL32"]["x_mm"]) +
            float(by_ref["SWR35"]["x_mm"])) / 2.0
    left_space = (round(left_alt[0] + space_dx, 3),
                  round(left_alt[1] + space_dy, 3), -9.0)
    targets["SWL32"] = (round(left_alt[0], 3), round(left_alt[1], 3), -5.0)
    targets["SWL33"] = left_space
    targets["SWR35"] = (round(2.0 * axis - left_alt[0], 3),
                        round(left_alt[1], 3), 5.0)
    targets["SWR36"] = (round(2.0 * axis - left_space[0], 3),
                        left_space[1], 9.0)
    return targets


def write_map(path: Path, rows, fields, targets):
    for row in rows:
        if row["ref"] not in targets:
            continue
        x, y, angle = targets[row["ref"]]
        row["x_mm"] = f"{x:.3f}".rstrip("0").rstrip(".")
        row["y_mm"] = f"{y:.3f}".rstrip("0").rstrip(".")
        row["rotation_deg"] = f"{angle:.3f}".rstrip("0").rstrip(".")
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def reference(fp):
    for prop in find(fp, "property"):
        if len(prop) > 2 and prop[1] == "Reference":
            return str(prop[2])
    return ""


def at_state(fp):
    at = first(fp, "at")
    return (float(at[1]), float(at[2]),
            float(at[3]) if len(at) > 3 else 0.0)


def transform_footprint(fp, old_cell, new_cell):
    x, y, angle = at_state(fp)
    ox, oy, old_angle = old_cell
    nx, ny, new_angle = new_cell
    visual_delta = math.radians(-(new_angle - old_angle))
    c, s = math.cos(visual_delta), math.sin(visual_delta)
    dx, dy = x - ox, y - oy
    at = first(fp, "at")
    at[1] = round(nx + dx * c - dy * s, 4)
    at[2] = round(ny + dx * s + dy * c, 4)
    rotated = angle + (new_angle - old_angle)
    if len(at) > 3:
        at[3] = round(rotated, 4)
    elif abs(rotated) > 1e-9:
        at.append(round(rotated, 4))


def direct_cell(side, ref):
    if side == "Left":
        match = re.fullmatch(r"HEL(\d+)|CL(\d+)[AB]", ref)
        prefix = "SWL"
    else:
        match = re.fullmatch(r"HER(\d+)|CR(\d+)[AB]", ref)
        prefix = "SWR"
    if not match:
        return None
    return prefix + next(value for value in match.groups() if value is not None)


def nearest_cell(position, old_cells, side):
    prefix = "SWL" if side == "Left" else "SWR"
    choices = [(math.hypot(position[0] - cell[0], position[1] - cell[1]), ref)
               for ref, cell in old_cells.items() if ref.startswith(prefix)]
    return min(choices)[1]


def migrate_board(path: Path, side: str, old_cells, new_cells):
    board = loads(path.read_text())
    leds = {}
    for fp in find(board, "footprint"):
        ref = reference(fp)
        if re.fullmatch(r"DL\d+" if side == "Left" else r"DR\d+", ref):
            leds[ref] = nearest_cell(at_state(fp), old_cells, side)

    moved = []
    for fp in find(board, "footprint"):
        ref = reference(fp)
        cell_ref = direct_cell(side, ref)
        led_match = re.fullmatch(r"D([LR])(\d+)", ref)
        rgb_match = re.fullmatch(r"CRGB([LR])(\d+)", ref)
        if led_match:
            cell_ref = leds[ref]
        elif rgb_match:
            led_ref = f"D{rgb_match.group(1)}{rgb_match.group(2)}"
            cell_ref = leds.get(led_ref)
        elif ref in STABILIZERS[side]:
            cell_ref = STABILIZERS[side][ref]
        if not cell_ref or cell_ref not in new_cells:
            continue
        if old_cells[cell_ref] == new_cells[cell_ref]:
            continue
        transform_footprint(fp, old_cells[cell_ref], new_cells[cell_ref])
        moved.append((ref, cell_ref))

    for fp in find(board, "footprint"):
        ref = reference(fp)
        if ref not in POST_TILT_RELOCATIONS[side]:
            continue
        at = first(fp, "at")
        at[1], at[2] = POST_TILT_RELOCATIONS[side][ref]
        moved.append((ref, "post-tilt-clearance"))

    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(dumps(board) + "\n")
    temporary.replace(path)
    print(f"{path.name}: moved {len(moved)} footprints across "
          f"{len(set(cell for _, cell in moved))} tilted key cells")
    return moved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    boards = [candidate / "Symm60HE-Left.kicad_pcb",
              candidate / "Symm60HE-Right.kicad_pcb"]
    missing = [path for path in [SWITCH_MAP, *boards] if not path.is_file()]
    if missing:
        raise SystemExit("missing required input: " + ", ".join(map(str, missing)))

    rows, fields = read_map(SWITCH_MAP)
    old_cells = {row["ref"]: state(row) for row in rows}
    targets = target_map(rows)
    new_cells = dict(old_cells)
    new_cells.update(targets)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    recovery = ROOT / "work" / f"recovery-before-doe-tilt-{stamp}"
    recovery.mkdir(parents=True)
    shutil.copy2(SWITCH_MAP, recovery / SWITCH_MAP.name)
    for board in boards:
        shutil.copy2(board, recovery / board.name)
    print("recovery:", recovery.relative_to(ROOT))

    for board, side in zip(boards, ("Left", "Right")):
        migrate_board(board, side, old_cells, new_cells)
    write_map(SWITCH_MAP, rows, fields, targets)

    max_shift = max(math.hypot(new_cells[ref][0] - old_cells[ref][0],
                               new_cells[ref][1] - old_cells[ref][1])
                    for ref in targets)
    print(f"switch map: updated {len(targets)} tilted positions; "
          f"maximum centre shift {max_shift:.3f} mm")
    print("copper: retained but not rerouted; candidate is placement-review only")


if __name__ == "__main__":
    main()
