#!/usr/bin/env python3
"""Replace the four close-pair RGB conflicts with shared LEDs.

The universal bottom-row alternatives put two switch centres only 4.7625 mm
apart.  Their alignment-hole pairs are rotated by 90 degrees, so a dedicated
LED at each switch centre collides with the upper alignment holes.  Keep one
electrical RGB-chain stage per close pair, place it at the exact horizontal
midpoint of the two upper alignment holes, and shift it 0.30 mm toward the
Hall sensors to improve visible separation from those holes.  The SOT-23 Hall
footprint is asymmetric, so rotate one Hall footprint in each close pair by
180 degrees.  That moves its copper pads out of the LED clearance path without
changing the Hall sensing centre or the vertical alignment-hole geometry.

The removed LEDs are selected deliberately:

* DL32 and DR35 duplicate the same RGB input/output nets as DL27 and DR29.
* DL28 and DR30 duplicate RGB stages that remain available at the alternate
  centre positions (DL33 and DR36).  DL29 and DR31 therefore remain as the
  shared LEDs for the outboard close pairs, preserving the complete chain.

Each removed LED's local 100 nF bypass capacitor is removed with it.  The
retained LED capacitors remain in their existing clear locations.
"""
from pathlib import Path
import argparse

from sexp import Sym, dumps, first, loads


EDITS = {
    "Left": {
        "moves": {
            "DL27": (10.9535, 83.2500),
            "DL29": (44.2915, 83.2500),
        },
        "rotate": {"HEL27", "HEL30"},
        "remove": {"DL32", "CRGBL32", "DL28", "CRGBL28"},
    },
    "Right": {
        "moves": {
            "DR29": (255.7460, 83.2500),
            "DR31": (289.0840, 83.2500),
        },
        "rotate": {"HER30", "HER33"},
        "remove": {"DR35", "CRGBR35", "DR30", "CRGBR30"},
    },
}


def reference(footprint):
    for item in footprint:
        if (isinstance(item, list) and len(item) > 2 and
                item[0] == "property" and item[1] == "Reference"):
            return str(item[2])
    return None


def edit_board(path, side):
    board = loads(path.read_text())
    spec = EDITS[side]
    seen = set()
    output = [board[0]]

    for item in board[1:]:
        if not (isinstance(item, list) and item and item[0] == "footprint"):
            output.append(item)
            continue

        ref = reference(item)
        if ref in spec["remove"]:
            seen.add(ref)
            continue

        if ref in spec["moves"]:
            at = first(item, "at")
            if at is None:
                raise RuntimeError(f"{path.name}: {ref} has no position")
            x, y = spec["moves"][ref]
            at[1], at[2] = Sym(str(x)), Sym(str(y))
            seen.add(ref)

        if ref in spec["rotate"]:
            at = first(item, "at")
            if at is None:
                raise RuntimeError(f"{path.name}: {ref} has no position")
            if len(at) == 3:
                at.append(Sym("180"))
            else:
                at[3] = Sym("180")
            seen.add(ref)

        output.append(item)

    expected = set(spec["moves"]) | spec["rotate"] | spec["remove"]
    missing = expected - seen
    if missing:
        raise RuntimeError(f"{path.name}: missing expected footprints: " +
                           ", ".join(sorted(missing)))

    path.write_text(dumps(output) + "\n")
    print(f"{path.name}: moved {len(spec['moves'])} shared LEDs; "
          f"rotated {len(spec['rotate'])} Hall footprints; "
          f"removed {len(spec['remove']) // 2} LEDs and their capacitors")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "candidate", type=Path,
        help="directory containing Symm60HE-Left/Right.kicad_pcb")
    args = parser.parse_args()

    for side in ("Left", "Right"):
        path = args.candidate / f"Symm60HE-{side}.kicad_pcb"
        if not path.is_file():
            raise SystemExit(f"missing {path}")
        edit_board(path, side)


if __name__ == "__main__":
    main()
