#!/usr/bin/env python3
"""Relocate every half-board mount to the shared PCB/plate pattern.

Each half has an independently clearance-optimized pattern. The PCB footprints
are isolated 2.2 mm NPTH holes so a
metal screw cannot accidentally join GND to routed copper; the intended case
spacer is a non-magnetic nylon M2 part with a maximum 4.0 mm body diameter.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from sexp import Sym, dumps, find, first, loads, newuuid  # noqa: E402
from mechanics import PCB_MOUNT_REFS as MOUNTS  # noqa: E402

MOUNT_LABEL_OFFSET = (0.0, -3.15)


def reference(footprint):
    return next((str(prop[2]) for prop in find(footprint, "property")
                 if len(prop) > 2 and str(prop[1]) == "Reference"), None)


def remove_named(node, *names):
    wanted = set(names)
    node[:] = [item for item in node
               if not (isinstance(item, list) and item and
                       str(item[0]) in wanted)]


def make_npth(footprint):
    footprint[1] = "Symm60HE_Project:MountingHole_2.2mm_M2_NPTH"
    description = first(footprint, "descr")
    if description:
        description[1] = "Isolated 2.2 mm clearance hole for an M2 plate-mount screw"
    value = next((prop for prop in find(footprint, "property")
                  if len(prop) > 2 and str(prop[1]) == "Value"), None)
    if value:
        value[2] = "M2_NPTH"
    pads = find(footprint, "pad")
    if len(pads) != 1:
        raise RuntimeError("mount footprint must contain exactly one pad")
    pad = pads[0]
    pad[1] = ""
    pad[2] = Sym("np_thru_hole")
    size = first(pad, "size")
    drill = first(pad, "drill")
    size[1:] = [Sym("2.2"), Sym("2.2")]
    drill[1:] = [Sym("2.2")]
    remove_named(pad, "net", "zone_connect", "remove_unused_layers")
    # A bare NPTH looks almost identical to the many switch-alignment drills in
    # KiCad's 3D view. Add a 4.8 mm OD front-silkscreen ring so the four case
    # standoffs on each half are unmistakable without changing the drill.
    has_marker = any(
        first(graphic, "layer") is not None and
        first(graphic, "layer")[1] == "F.SilkS"
        for graphic in find(footprint, "fp_circle"))
    if not has_marker:
        footprint.append([
            Sym("fp_circle"), [Sym("center"), Sym("0"), Sym("0")],
            [Sym("end"), Sym("2.4"), Sym("0")],
            [Sym("stroke"), [Sym("width"), Sym("0.3")],
             [Sym("type"), Sym("solid")]],
            [Sym("fill"), Sym("none")], [Sym("layer"), "F.SilkS"],
            newuuid(),
        ])


def place_reference_label(footprint, ref):
    offset = MOUNT_LABEL_OFFSET
    reference_property = next(
        prop for prop in find(footprint, "property")
        if len(prop) > 2 and str(prop[1]) == "Reference")
    at = first(reference_property, "at")
    at[1:3] = [Sym(f"{offset[0]:.3f}"), Sym(f"{offset[1]:.3f}")]


def clear_zone_cache(board):
    removed = 0
    for zone in find(board, "zone"):
        before = len(zone)
        remove_named(zone, "filled_polygon", "filled_segments")
        removed += before - len(zone)
    return removed


def update(path, side):
    board = loads(path.read_text())
    by_ref = {reference(fp): fp for fp in find(board, "footprint")}
    for ref, (x, y) in MOUNTS[side].items():
        footprint = by_ref.get(ref)
        if footprint is None:
            raise RuntimeError(f"{path.name}: missing {ref}")
        at = first(footprint, "at")
        at[1:3] = [Sym(f"{x:.6f}"), Sym(f"{y:.6f}")]
        make_npth(footprint)
        place_reference_label(footprint, ref)
    cleared = clear_zone_cache(board)
    path.write_text(dumps(board) + "\n")
    print(f"{path}: four clearance-optimized 2.2 mm NPTH mounts; "
          f"cleared {cleared} cached zone fills")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--board-dir", action="append", type=Path,
        help="directory containing the Left and Right board files; repeatable")
    args = parser.parse_args()
    directories = args.board_dir or [ROOT / "pcb"]
    for directory in directories:
        for side in ("Left", "Right"):
            matches = sorted(directory.glob(f"Symm60HE-*-{side}.kicad_pcb"))
            direct = directory / f"Symm60HE-{side}.kicad_pcb"
            if direct.exists():
                matches.insert(0, direct)
            if len(matches) != 1:
                raise RuntimeError(
                    f"{directory}: expected one {side} board, found {matches}")
            update(matches[0], side)


if __name__ == "__main__":
    main()
