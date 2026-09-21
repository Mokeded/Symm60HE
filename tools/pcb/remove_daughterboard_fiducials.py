#!/usr/bin/env python3
"""Remove local daughterboard fiducials while retaining its four M2 mounts."""
from pathlib import Path

from sexp import dumps, loads


ROOT = Path(__file__).resolve().parents[2]
BOARD = ROOT / "pcb/Symm60HE-Daughterboard.kicad_pcb"


def main():
    board = loads(BOARD.read_text())
    kept = [board[0]]
    removed = []
    for node in board[1:]:
        if (isinstance(node, list) and node and
                str(node[0]) == "footprint" and
                "Fiducial_1mm_" in str(node[1])):
            removed.append(str(node[1]))
            continue
        kept.append(node)
    BOARD.write_text(dumps(kept) + "\n")
    print(f"{BOARD.name}: removed {len(removed)} local fiducials; "
          "retained MHD1-MHD4 case mounts")


if __name__ == "__main__":
    main()
