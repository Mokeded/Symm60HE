#!/usr/bin/env python3
"""Prove every PCB reference/pad/net tuple matches its captured symbol."""
from pathlib import Path
import sys

from mkschematics import components, symbol_name
from sexp import find, first, loads

ROOT = Path(__file__).resolve().parent.parent
BOARDS = ("Symm60HE-Left", "Symm60HE-Right", "Symm60HE-Daughterboard")


def symbol_map(path):
    tree = loads(path.read_text())
    result = {}
    for node in tree:
        if not isinstance(node, list) or not node or node[0] != "symbol":
            continue
        name = str(node[1])
        pins = {}
        def descendants(current, kind):
            for child in current:
                if isinstance(child, list):
                    if child and child[0] == kind:
                        yield child
                    yield from descendants(child, kind)
        for pin in descendants(node, "pin"):
            number, pin_name = first(pin, "number"), first(pin, "name")
            if number and pin_name:
                pins[str(number[1])] = str(pin_name[1])
        result[name] = pins
    return result


def main():
    ok = True
    for board in BOARDS:
        captured = symbol_map(ROOT / "pcb" / f"{board}.kicad_sym")
        expected = {symbol_name(part["ref"]): dict(part["pads"])
                    for part in components(ROOT / "pcb" / f"{board}.kicad_pcb")}
        if captured != expected:
            print(board, "MISMATCH")
            for key in sorted(set(captured) | set(expected)):
                if captured.get(key) != expected.get(key):
                    print(" ", key, "pcb=", expected.get(key), "schematic=", captured.get(key))
            ok = False
        else:
            print(board, f"ok: {len(expected)} symbols, "
                  f"{sum(map(len, expected.values()))} pad/net assignments")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
