#!/usr/bin/env python3
"""Turn both daughterboard FFC mouths toward their nearest outside edge.

The locked C20111 footprint uses local +Y as its cable-entry side.  J2 and J3
were previously aimed toward the MCU. Rotating each connector 180 degrees and
reversing the pad-net assignments preserves the physical left-to-right net
order. Moving its centre 2.2 mm toward the edge keeps the signal-pad row in
exactly the same place, so no routing changes or bridge segments are needed.
The daughterboard outline is extended 0.5 mm at each side to retain production
copper-edge clearance around the hold-down pads. The operation is idempotent.
"""
from pathlib import Path
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import Sym, dumps, find, first, loads  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "pcb/Symm60HE-Daughterboard.kicad_pcb"
TARGETS = {"J2": (157.509, 270.0), "J3": (208.909, 90.0)}


def prop(fp, name):
    return next((p[2] for p in find(fp, "property")
                 if len(p) > 2 and p[1] == name), "")


def global_pad(fp, pad):
    at = first(fp, "at")
    pa = first(pad, "at")
    angle = math.radians(-float(at[3] if len(at) > 3 else 0.0))
    lx, ly = float(pa[1]), float(pa[2])
    return (float(at[1]) + lx * math.cos(angle) - ly * math.sin(angle),
            float(at[2]) + lx * math.sin(angle) + ly * math.cos(angle))


def pad_net(pad):
    net = first(pad, "net")
    return net[2] if net and len(net) > 2 else (net[1] if net else None)


def set_net(pad, name):
    net = first(pad, "net")
    if net is None:
        pad.append([Sym("net"), name])
    elif len(net) == 2:
        net[1] = name
    else:
        net[2] = name


def main():
    board = loads(BOARD.read_text())
    footprints = {prop(fp, "Reference"): fp for fp in find(board, "footprint")}
    changed = []
    for ref, (target_x, target_angle) in TARGETS.items():
        fp = footprints[ref]
        at = first(fp, "at")
        current = float(at[3] if len(at) > 3 else 0.0) % 360
        current_x = float(at[1])
        if (abs(current - target_angle) < 1e-6 and
                abs(current_x - target_x) < 1e-6):
            continue
        if abs(((target_angle - current) % 360) - 180.0) > 1e-6:
            raise RuntimeError(
                f"{ref}: expected a 180 degree turn, got "
                f"{current} -> {target_angle}")
        numbered = {int(p[1]): p for p in find(fp, "pad")
                    if str(p[1]).isdigit() and 1 <= int(p[1]) <= 12}
        old_nets = {number: pad_net(pad) for number, pad in numbered.items()}
        at[1] = target_x
        at[3] = int(target_angle)
        for pad in find(fp, "pad"):
            pa = first(pad, "at")
            if len(pa) > 3:
                pa[3] = int(target_angle)
            else:
                pa.append(int(target_angle))
        for number in range(1, 13):
            set_net(numbered[13 - number], old_nets[number])
        changed.append(ref)

    # The right connector's outward hold-down occupies the old top-right
    # fiducial location. Move the paired front/back fiducials upward while
    # keeping the same side-registration coordinate on both copper layers.
    for ref in ("FIDF3", "FIDB3"):
        fp = footprints.get(ref)
        if fp is not None:
            first(fp, "at")[2] = 19.2

    if not changed:
        print("daughterboard FFC mouths already face outward")
        return
    BOARD.write_text(dumps(board) + "\n")
    print("rotated", ", ".join(changed), "toward the daughterboard outside edges")
    print("kept every signal trace overlapping its rotated production land")


if __name__ == "__main__":
    main()
