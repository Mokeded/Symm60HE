#!/usr/bin/env python3
"""Mark every 0R_DNP footprint as do-not-populate in the PCB sources."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from sexp import Sym, dumps, find, first, loads  # noqa: E402


def property_value(footprint, name):
    return next((str(item[2]) for item in find(footprint, "property")
                 if len(item) > 2 and str(item[1]) == name), None)


def mark(path):
    board = loads(path.read_text())
    changed = []
    for footprint in find(board, "footprint"):
        if property_value(footprint, "Value") != "0R_DNP":
            continue
        attr = first(footprint, "attr")
        if attr is None:
            attr = [Sym("attr"), Sym("smd")]
            footprint.append(attr)
        if not any(str(value) == "dnp" for value in attr[1:]):
            attr.append(Sym("dnp"))
            changed.append(property_value(footprint, "Reference"))
    path.write_text(dumps(board) + "\n")
    print(f"{path.name}: marked {len(changed)} DNP footprint(s)")


if __name__ == "__main__":
    for board_name in ("Symm60HE-Left.kicad_pcb", "Symm60HE-Right.kicad_pcb"):
        mark(ROOT / "pcb" / board_name)
