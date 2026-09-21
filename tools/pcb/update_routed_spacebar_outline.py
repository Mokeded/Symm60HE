#!/usr/bin/env python3
"""Apply the current mirrored spacebar outline to the routed half PCBs.

This deliberately preserves component placement and every copper item that
still fits.  Only copper made invalid by the smaller outline is removed for a
subsequent local repair, and the existing GND-zone outer contours are resized.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from compact_routed_halves import (  # noqa: E402
    detach_and_prune_copper,
    replace_outline_and_ground_zones,
    validate_led_clearance,
)
from outline import LEFT_PCB_ENCLOSURE, RIGHT_PCB_ENCLOSURE  # noqa: E402
from rebuild_unrouted_keycap_inset import (  # noqa: E402
    at_state, reference, set_at,
)
from sexp import dumps, find, loads  # noqa: E402
from relocate_half_mounts import MOUNTS  # noqa: E402


BOARD_DIR = (ROOT / "work" /
             "enclosure-style-hotswap-freerouting-candidate" /
             "routed-final")
MOUNT_MOVES = MOUNTS


def update(side, polygon):
    path = BOARD_DIR / f"Symm60HE-{side}.kicad_pcb"
    board = loads(path.read_text())
    footprints = {reference(fp): fp for fp in find(board, "footprint")}
    moved = []
    for ref, (x, y) in MOUNT_MOVES[side].items():
        footprint = footprints.get(ref)
        if footprint is None:
            raise RuntimeError(f"{path.name}: missing {ref}")
        old_x, old_y, angle = at_state(footprint)
        set_at(footprint, x, y, angle)
        moved.append((ref, old_x, old_y, x, y))
    removed, repair_nets = detach_and_prune_copper(
        board, moving_pads={}, deltas={}, outline=polygon)
    board, old_edges, resized_zones, new_edges = \
        replace_outline_and_ground_zones(board, polygon, zone_shifts=[])
    temporary = path.with_suffix(path.suffix + ".spacebar-outline-tmp")
    temporary.write_text(dumps(board) + "\n")
    validate_led_clearance(temporary, side, polygon)
    temporary.replace(path)
    print(f"{path.name}: {old_edges} -> {new_edges} Edge.Cuts; "
          f"resized {resized_zones} GND zones; removed {len(removed)} "
          "out-of-outline copper items")
    print("  repair nets: " + (", ".join(repair_nets) or "none"))
    for ref, old_x, old_y, x, y in moved:
        print(f"  {ref}: ({old_x:.3f}, {old_y:.3f}) -> "
              f"({x:.3f}, {y:.3f})")


def main():
    update("Left", LEFT_PCB_ENCLOSURE)
    update("Right", RIGHT_PCB_ENCLOSURE)


if __name__ == "__main__":
    main()
