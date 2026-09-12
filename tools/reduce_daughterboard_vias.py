#!/usr/bin/env python3
"""Remove daughterboard vias proven redundant after zone refill.

The controller routes use layer changes where congestion or bottom-side parts
require them.  These two GND vias, however, duplicate direct connections into
the continuous ground pours on both layers.  Removing them lowers the drill
count without moving signals, weakening USB routing, or changing the remaining
ground stitching topology.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import dumps, find, first, loads  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "pcb/Symm60HE-Daughterboard.kicad_pcb"
REDUNDANT_GND_VIAS = {(196.1507, 15.3095), (191.6749, 8.2817)}


def point(item):
    at = first(item, "at")
    return round(float(at[1]), 4), round(float(at[2]), 4)


def main():
    board = loads(BOARD.read_text())
    removed = []
    kept = []
    for item in board:
        if (isinstance(item, list) and item and item[0] == "via" and
                first(item, "net") and str(first(item, "net")[1]) == "GND" and
                point(item) in REDUNDANT_GND_VIAS):
            removed.append(point(item))
        else:
            kept.append(item)
    if removed:
        BOARD.write_text(dumps(kept) + "\n")
    print(f"{BOARD.name}: removed {len(removed)} redundant GND via(s); "
          f"remaining targets already absent={len(REDUNDANT_GND_VIAS) - len(removed)}")


if __name__ == "__main__":
    main()
