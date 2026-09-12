#!/usr/bin/env python3
"""Lock every routed FFC footprint to BOOMELE 1.0-12P / LCSC C20111.

Only pad-local geometry is synchronized.  Pad UUIDs, nets, layers, footprint
placement and routing remain untouched.  The longer production pads overlap
the previous track endpoints, which KiCad DRC verifies after this update.
"""
from pathlib import Path
from copy import deepcopy

from sexp import dumps, find, first, loads, set_uuids

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "Symm60HE_Project.pretty/FFC_12P_1.00mm_TopContact.kicad_mod"
BOARDS = (
    ROOT / "pcb/Symm60HE-Left.kicad_pcb",
    ROOT / "pcb/Symm60HE-Right.kicad_pcb",
    ROOT / "pcb/Symm60HE-Daughterboard.kicad_pcb",
)


def reference(fp):
    return next((p[2] for p in find(fp, "property")
                 if len(p) > 2 and p[1] == "Reference"), "")


def pad_key(pad, seen):
    number = str(pad[1])
    occurrence = seen.get(number, 0)
    seen[number] = occurrence + 1
    return number, occurrence


def prune_old_ground_fanout(board, board_name):
    """Remove the generic-footprint GND fanout inside the longer C20111 pads.

    Those pads connect directly to the same-layer GND pour.  Keeping the old
    fanout would run grounded copper through adjacent production lands.
    """
    remove = []
    for item in board:
        if not isinstance(item, list) or not item or item[0] != "segment":
            continue
        net = first(item, "net")
        start, end = first(item, "start"), first(item, "end")
        if not net or str(net[1]) != "GND" or not start or not end:
            continue
        x1, y1, x2, y2 = map(float, (start[1], start[2], end[1], end[2]))
        near_left_half = (board_name == "Symm60HE-Left.kicad_pcb" and
                          max(x1, x2) >= 145 and min(x1, x2) <= 149 and
                          max(y1, y2) >= 48 and min(y1, y2) <= 63)
        near_db_left = (board_name == "Symm60HE-Daughterboard.kicad_pcb" and
                        (156 <= x1 <= 160 or 156 <= x2 <= 160) and
                        4 <= min(y1, y2) and max(y1, y2) <= 8)
        near_db_right = (board_name == "Symm60HE-Daughterboard.kicad_pcb" and
                         (207 <= x1 <= 209 or 207 <= x2 <= 209) and
                         10 <= min(y1, y2) and max(y1, y2) <= 13)
        if near_left_half or near_db_left or near_db_right:
            remove.append(item)
    for item in remove:
        board.remove(item)
    return len(remove)


def main():
    library = loads(LIB.read_text())
    graphic_types = {"fp_line", "fp_rect", "fp_arc", "fp_poly",
                     "fp_text", "fp_text_box"}
    library_graphics = [deepcopy(item) for item in library[2:]
                        if isinstance(item, list) and item and
                        item[0] in graphic_types]
    source = {}
    seen = {}
    for pad in find(library, "pad"):
        source[pad_key(pad, seen)] = (
            list(first(pad, "at")[1:]), list(first(pad, "size")[1:]))

    total = 0
    for path in BOARDS:
        board = loads(path.read_text())
        changed = 0
        for fp in find(board, "footprint"):
            if "FFC_12P_1.00mm_TopContact" not in str(fp[1]):
                continue
            seen = {}
            back = first(fp, "layer")[1] == "B.Cu"
            for pad in find(fp, "pad"):
                key = pad_key(pad, seen)
                if key not in source:
                    raise RuntimeError(f"unexpected pad {key} in {path.name}:{reference(fp)}")
                at, size = source[key]
                placed_at = first(pad, "at")
                # A flipped footprint mirrors its library-local Y coordinate.
                # Preserve KiCad's existing per-pad rotation; it is required
                # for rotated/flipped connector instances.
                rotation = placed_at[3:]
                y = float(at[1])
                placed_at[1:] = [at[0], -y if back else y] + rotation
                first(pad, "size")[1:] = size
            # Keep the board copy visually and semantically synchronized with
            # the locked library footprint. This includes the newly explicit
            # body and cable-entry marker, but not reference/value properties.
            fp[:] = [item for item in fp
                     if not (isinstance(item, list) and item and
                             item[0] in graphic_types)]
            for item in library_graphics:
                copied = deepcopy(item)
                set_uuids(copied)
                fp.append(copied)
            changed += 1
        if not changed:
            raise RuntimeError(f"no FFC connector found in {path}")
        pruned = prune_old_ground_fanout(board, path.name)
        path.write_text(dumps(board) + "\n")
        total += changed
        print(f"{path.name}: locked {changed} connector footprint(s) to C20111; "
              f"removed {pruned} obsolete GND fanout segment(s)")
    if total != 4:
        raise RuntimeError(f"expected four FFC connector footprints, found {total}")


if __name__ == "__main__":
    main()
