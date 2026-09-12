#!/usr/bin/env python3
"""Add three local fiducials to each assembled side of the daughterboard."""
from copy import deepcopy
from pathlib import Path

from sexp import Sym, dumps, find, first, loads, newuuid, set_uuids

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "pcb/Symm60HE-Daughterboard.kicad_pcb"
POSITIONS = ((164.0, -3.0), (180.0, -5.0), (209.0, 18.0))


def template(side):
    filename = f"Fiducial_1mm_{side}Cu.kicad_mod"
    module = loads((ROOT / "Symm60HE_Project.pretty" / filename).read_text())
    body = [deepcopy(node) for node in module[2:]
            if not (isinstance(node, list) and node and
                    node[0] in ("version", "generator", "generator_version"))]
    return [Sym("footprint"), f"Symm60HE_Project:Fiducial_1mm_{side}Cu",
            [Sym("layer"), f"{side}.Cu"], newuuid(), [Sym("at"), 0, 0]] + body


def main():
    board = loads(BOARD.read_text())
    expected = {f"FID{side}{index}" for side in ("F", "B")
                for index in range(1, 4)}
    existing = {}
    for fp in find(board, "footprint"):
        if "Fiducial_1mm_" not in str(fp[1]):
            continue
        ref = next((prop[2] for prop in find(fp, "property")
                    if len(prop) > 2 and prop[1] == "Reference"), "")
        existing[str(ref)] = fp
    if set(existing) == expected:
        print(f"{BOARD.name}: six side-appropriate fiducials already present")
        return
    board[:] = [node for node in board if not (
        isinstance(node, list) and node and node[0] == "footprint" and
        "Fiducial_1mm_" in str(node[1]))]
    added = []
    for side in ("F", "B"):
        base = template(side)
        for index, (x, y) in enumerate(POSITIONS, 1):
            fp = deepcopy(base)
            first(fp, "at")[1:3] = [x, y]
            for prop in find(fp, "property"):
                if len(prop) > 2 and prop[1] == "Reference":
                    prop[2] = f"FID{side}{index}"
            set_uuids(fp)
            board.append(fp)
            added.append(f"FID{side}{index}")
    BOARD.write_text(dumps(board) + "\n")
    print(f"{BOARD.name}: added {', '.join(added)}")


if __name__ == "__main__":
    main()
