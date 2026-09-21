#!/usr/bin/env python3
"""Apply the explicit-3V3A and dual-GND manufacturing redesign.

The daughterboard candidate is generated/routed separately so this script only
promotes a candidate after the caller has run KiCad DRC.  The two keyboard
halves already contain explicit +3V3A tracks; their +3V3A zones are removed and
the existing B.Cu GND zone is duplicated onto F.Cu.  The compact mixed-side
daughterboard also receives GND zones on both external copper layers.
"""
from copy import deepcopy
from pathlib import Path
import argparse
import shutil

from sexp import Sym, dumps, first, loads, set_uuids
from route import read, zone

ROOT = Path(__file__).resolve().parents[2]
PCB = ROOT / "pcb"


def set_zone_layer(zone, layer):
    item = first(zone, "layer")
    if item is not None:
        item[1] = layer
        return
    item = first(zone, "layers")
    if item is None:
        raise RuntimeError("zone has no copper layer")
    item[1:] = [layer]


def convert_half(path):
    board = loads(path.read_text())
    zones = [item for item in board if isinstance(item, list) and item and
             item[0] == "zone"]
    ground = [z for z in zones if first(z, "net") and first(z, "net")[1] == "GND"]
    if not ground:
        raise RuntimeError(f"{path.name}: missing source GND zone")
    # Remove all existing +3V3A zones and any duplicate F.Cu GND zone.
    body = []
    for item in board[1:]:
        if isinstance(item, list) and item and item[0] == "zone":
            net = first(item, "net")
            layer = first(item, "layer") or first(item, "layers")
            if net and net[1] == "+3V3A":
                continue
            if net and net[1] == "GND" and layer and "F.Cu" in layer[1:]:
                continue
        body.append(item)
    front = deepcopy(next(z for z in ground
                          if (first(z, "layer") or first(z, "layers"))[1] == "B.Cu"))
    set_zone_layer(front, "F.Cu")
    set_uuids(front)
    # Filled polygons are derived data and must be rebuilt by KiCad.
    front[:] = [node for node in front
                if not (isinstance(node, list) and node and
                        node[0] in ("filled_polygon", "fill_segments"))]
    # Preserve the final embedded_fonts node as the last root item.
    board = [Sym("kicad_pcb")] + body[:-1] + [front, body[-1]]
    path.write_text(dumps(board) + "\n")


def ensure_daughter_ground(path):
    board, _, outline, _ = read(str(path))
    body = [item for item in board[1:]
            if not (isinstance(item, list) and item and item[0] == "zone" and
                    first(item, "net") and first(item, "net")[1] == "GND")]
    ground = [zone(outline, "GND", "F.Cu"),
              zone(outline, "GND", "B.Cu")]
    board = [Sym("kicad_pcb")] + body[:-1] + ground + [body[-1]]
    path.write_text(dumps(board) + "\n")


def all_smt_on_back(path):
    board = loads(path.read_text())
    bad = []
    for fp in [n for n in board if isinstance(n, list) and n and n[0] == "footprint"]:
        attr = first(fp, "attr")
        if not attr or "smd" not in attr[1:]:
            continue
        layer = first(fp, "layer")[1]
        ref = next((p[2] for p in fp if isinstance(p, list) and len(p) > 2 and
                    p[0] == "property" and p[1] == "Reference"), "?")
        if layer != "B.Cu":
            bad.append(ref)
    if bad:
        raise RuntimeError(f"{path.name}: front-side SMT remains: {', '.join(bad)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", nargs="?", type=Path,
                        help="optional DRC-clean all-B.Cu daughterboard candidate")
    parser.add_argument("--halves-only", action="store_true",
                        help="leave the compact mixed-side daughterboard unchanged")
    args = parser.parse_args()
    if not args.halves_only:
        if args.candidate is None or not args.candidate.is_file():
            raise SystemExit("a routed daughterboard candidate is required unless --halves-only is used")
        all_smt_on_back(args.candidate)
    for name in ("Symm60HE-Left", "Symm60HE-Right"):
        convert_half(PCB / f"{name}.kicad_pcb")
    if not args.halves_only:
        target = PCB / "Symm60HE-Daughterboard.kicad_pcb"
        shutil.copy2(args.candidate, target)
        all_smt_on_back(target)
        print("promoted", args.candidate, "->", target)
    else:
        print("left compact mixed-side daughterboard unchanged")
    ensure_daughter_ground(PCB / "Symm60HE-Daughterboard.kicad_pcb")
    print("removed +3V3A zones and provided dual-layer GND zones on all boards")


if __name__ == "__main__":
    main()
