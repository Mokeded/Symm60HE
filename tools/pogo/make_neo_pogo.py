#!/usr/bin/env python3
"""Build the Neo-style separated pogo architecture.

The production FFC design remains untouched.  This variant keeps the existing
57 x 28 mm controller PCB rigid, adds one floating FFC-to-pogo spring board per
side, and substitutes 12-contact target connectors directly into copies of the
two keyboard halves.  Short 12-way FFCs are the only compliant links.  No
target daughterboards and no flexures etched into FR-4 are used.
"""
from copy import deepcopy
from pathlib import Path
import csv
import math
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_serpentine_pogo import (add_missing_uuids, global_pad, prop,
                                  swap_front_back)  # noqa: E402
from sexp import Sym, dumps, find, first, loads, newuuid, set_uuids  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "pcb/variants/pogo-neo"
LIB = ROOT / "Symm60HE_Project.pretty"
TRACE_W = 0.20
VIA_SIZE = 0.60
VIA_DRILL = 0.30
MODULE_W = 20.0
MODULE_H = 20.0
CONTACT_Y = 5.0
FFC_Y = 15.0

FFC_NETS = ["+3V3A", "GND", "MUX_A0", "MUX_A1", "MUX_A2", "GND",
            "ADC_1", "GND", "ADC_2", "GND", "ADC_3", "ADC_4"]
HALF_FFC_NETS = {
    "L": ["ADC_L4", "ADC_L3", "GND", "ADC_L2", "GND", "ADC_L1",
          "GND", "MUX_A2", "MUX_A1", "MUX_A0", "GND", "+3V3A"],
    "R": ["+3V3A", "GND", "MUX_A0", "MUX_A1", "MUX_A2", "GND",
          "ADC_R1", "GND", "ADC_R2", "GND", "ADC_R3", "ADC_R4"],
}

# Physical left-to-right assignment on the spring block.  Signals stay in the
# same order as the 12-way FFC; the four extra positions reinforce power and
# ground rather than introduce another logical signal.
DIRECT_TARGET = {
    "Left": {"old_ref": "JL1", "new_ref": "PTL1", "boundary": 144.0,
             "x": 148.0, "rotation": -90.0},
    "Right": {"old_ref": "JR1", "new_ref": "PTR1", "boundary": 158.0,
              "x": 154.418, "rotation": 90.0},
}
TARGET_ORDER = {
    # Physical order after sorting the rotated target pads by Y then X.  The
    # ground positions also keep the two-layer fanouts from crossing.
    "Left": ["ADC_L4", "ADC_L3", "GND", "ADC_L2", "GND", "ADC_L1",
             "GND", "MUX_A2", "MUX_A1", "MUX_A0", "GND", "+3V3A"],
    "Right": ["ADC_R4", "ADC_R3", "GND", "ADC_R2", "GND", "ADC_R1",
              "MUX_A2", "MUX_A1", "GND", "MUX_A0", "GND", "+3V3A"],
}

# Physical bottom-to-top target order. Ground occupies four contacts, matching
# the existing 12-way interface without the routing and footprint penalty of
# the superseded 16-contact experiment.
TARGET_ORDER = {
    "Left": ["ADC_L4", "ADC_L3", "GND", "ADC_L2", "GND", "ADC_L1",
             "GND", "MUX_A2", "MUX_A1", "MUX_A0", "GND", "+3V3A"],
    "Right": ["ADC_R4", "ADC_R3", "GND", "ADC_R2", "GND", "ADC_R1",
              "MUX_A2", "MUX_A1", "GND", "MUX_A0", "GND", "+3V3A"],
}


def renamed(net, side):
    return net.replace("ADC_", f"ADC_{side}") if net.startswith("ADC_") else net


def skeleton():
    text = '''(kicad_pcb (version 20260206) (generator "pcbnew")
      (generator_version "10.0")
      (general (thickness 1.2))
      (paper "A4")
      (layers (0 "F.Cu" signal) (2 "B.Cu" signal)
        (5 "F.SilkS" user "F.Silkscreen")
        (7 "B.SilkS" user "B.Silkscreen")
        (1 "F.Mask" user) (3 "B.Mask" user)
        (13 "F.Paste" user) (15 "B.Paste" user)
        (25 "Edge.Cuts" user) (31 "F.CrtYd" user "F.Courtyard")
        (29 "B.CrtYd" user "B.Courtyard")
        (35 "F.Fab" user) (33 "B.Fab" user))
      (setup (pad_to_mask_clearance 0)))'''
    return loads(text)


def segment(a, b, net, layer="F.Cu", width=TRACE_W):
    return [Sym("segment"), [Sym("start"), round(a[0], 4), round(a[1], 4)],
            [Sym("end"), round(b[0], 4), round(b[1], 4)],
            [Sym("width"), width], [Sym("layer"), layer],
            [Sym("net"), net], newuuid()]


def via(point, net):
    return [Sym("via"), [Sym("at"), round(point[0], 4), round(point[1], 4)],
            [Sym("size"), VIA_SIZE], [Sym("drill"), VIA_DRILL],
            [Sym("layers"), "F.Cu", "B.Cu"], [Sym("net"), net], newuuid()]


def polyline(board, points, net, layer="F.Cu"):
    for start, end in zip(points, points[1:]):
        if math.dist(start, end) > 1e-6:
            board.append(segment(start, end, net, layer))


def add_outline(board):
    corners = [(0, 0), (MODULE_W, 0), (MODULE_W, MODULE_H),
               (0, MODULE_H), (0, 0)]
    for start, end in zip(corners, corners[1:]):
        board.append([
            Sym("gr_line"), [Sym("start"), *start], [Sym("end"), *end],
            [Sym("stroke"), [Sym("width"), 0.1], [Sym("type"), Sym("solid")]],
            [Sym("layer"), "Edge.Cuts"], newuuid(),
        ])


def add_note(board, text, at, layer="F.SilkS"):
    board.append([
        Sym("gr_text"), text, [Sym("at"), *at], [Sym("layer"), layer],
        newuuid(), [Sym("effects"), [Sym("font"), [Sym("size"), 0.8, 0.8],
                                             [Sym("thickness"), 0.12]]],
    ])


def place_footprint(board, filename, reference, x, y, pin_map):
    fp = loads((LIB / filename).read_text())
    fp = deepcopy(fp)
    fp[:] = [item for item in fp if not (
        isinstance(item, list) and item and item[0] in
        ("version", "generator", "generator_version"))]
    fp.insert(2, [Sym("at"), x, y])
    for item in find(fp, "property"):
        if item[1] == "Reference":
            item[2] = reference
    for pad in find(fp, "pad"):
        if str(pad[1]).isdigit():
            pad.append([Sym("net"), pin_map[int(pad[1])]])
    set_uuids(fp)
    add_missing_uuids(fp)
    board.append(fp)
    return fp


def build_direct_target_half(side):
    """Replace the half's FFC with a directly mounted 12-contact target."""
    cfg = DIRECT_TARGET[side]
    source = ROOT / f"pcb/Symm60HE-{side}.kicad_pcb"
    board = loads(source.read_text())
    old = next(fp for fp in find(board, "footprint")
               if prop(fp, "Reference") == cfg["old_ref"])
    connector_nets = {first(pad, "net")[1] for pad in find(old, "pad")
                      if first(pad, "net")}
    boundary = cfg["boundary"]
    is_left = side == "Left"
    anchors = []
    kept = []

    # Remove only the old connector's local breakout and terminate the retained
    # routing cleanly at a controlled vertical handoff line.
    for item in board:
        if not (isinstance(item, list) and item and item[0] == "segment" and
                first(item, "net")[1] in connector_nets):
            kept.append(item)
            continue
        start = tuple(map(float, first(item, "start")[1:3]))
        end = tuple(map(float, first(item, "end")[1:3]))
        if max(start[1], end[1]) < 44 or min(start[1], end[1]) > 68:
            kept.append(item)
            continue
        start_inside = start[0] >= boundary if is_left else start[0] <= boundary
        end_inside = end[0] >= boundary if is_left else end[0] <= boundary
        if start_inside and end_inside:
            continue
        if not start_inside and not end_inside:
            kept.append(item)
            continue
        if abs(end[0] - start[0]) < 1e-9:
            continue
        ratio = (boundary - start[0]) / (end[0] - start[0])
        handoff = (boundary, start[1] + ratio * (end[1] - start[1]))
        outside = start if not start_inside else end
        net = first(item, "net")[1]
        layer = first(item, "layer")[1]
        width = float(first(item, "width")[1])
        kept.append(segment(outside, handoff, net, layer, width))
        anchors.append((net, handoff, layer))
    board[:] = kept
    board[:] = [item for item in board if item is not old and not (
        isinstance(item, list) and item and item[0] == "via" and
        first(item, "net")[1] in connector_nets and
        44 <= float(first(item, "at")[2]) <= 68 and
        ((float(first(item, "at")[1]) >= boundary) if is_left else
         (float(first(item, "at")[1]) <= boundary)))]

    signal_anchors = {}
    for net, point, layer in anchors:
        if net != "GND":
            signal_anchors.setdefault(net, []).append((point, layer))
    signal_anchors = {net: values[len(values) // 2]
                      for net, values in signal_anchors.items()}
    expected = set(TARGET_ORDER[side]) - {"GND"}
    if set(signal_anchors) != expected:
        raise RuntimeError((side, sorted(expected - set(signal_anchors)),
                            sorted(set(signal_anchors) - expected)))

    fp = loads((LIB / "MillMax_856-10-012-30-051000.kicad_mod").read_text())
    fp = deepcopy(fp)
    fp[:] = [item for item in fp if not (
        isinstance(item, list) and item and item[0] in
        ("version", "generator", "generator_version"))]
    fp.insert(2, [Sym("at"), cfg["x"], 56.0, cfg["rotation"]])
    for item in find(fp, "property"):
        if item[1] == "Reference":
            item[2] = cfg["new_ref"]
    swap_front_back(fp)
    set_uuids(fp)
    add_missing_uuids(fp)
    board.append(fp)
    pads = sorted((pad for pad in find(fp, "pad") if str(pad[1]).isdigit()),
                  key=lambda pad: (global_pad(fp, pad)[1],
                                   global_pad(fp, pad)[0]))
    for pad, net in zip(pads, TARGET_ORDER[side]):
        pad.append([Sym("net"), net])

    direction = 1 if is_left else -1
    for pad in pads:
        net = first(pad, "net")[1]
        if net == "GND":
            continue
        pad_point = global_pad(fp, pad)
        handoff, layer = signal_anchors[net]
        if layer == "B.Cu":
            polyline(board, [pad_point, handoff], net, "B.Cu")
        elif side == "Left" and net == "ADC_L1":
            # The retained left breakout exchanges ADC_L1 and MUX_A2 order.
            # Cross that one permutation on B.Cu and transfer at the handoff;
            # every other conductor remains in the ordered F.Cu fanout.
            board.append(via(handoff, net))
            polyline(board, [pad_point, handoff], net, "B.Cu")
        else:
            escape = (pad_point[0] - direction * 0.8, pad_point[1])
            board.append(via(escape, net))
            polyline(board, [pad_point, escape], net, "B.Cu")
            polyline(board, [escape, handoff], net, "F.Cu")

    output = OUT / f"Symm60HE-Neo-{side}-Half.kicad_pcb"
    output.write_text(dumps(board) + "\n")
    shutil.copy2(source.with_suffix(".kicad_pro"), output.with_suffix(".kicad_pro"))
    return output, {int(pad[1]): first(pad, "net")[1] for pad in pads}


def build_module(side, contact_map):
    side_letter = "L" if side == "Left" else "R"
    kind = "Spring"
    ffc_sequence = [renamed(name, side_letter) for name in FFC_NETS]
    names = []
    for name in ffc_sequence:
        if name not in names:
            names.append(name)
    board = skeleton()
    ffc_map = {pin: name for pin, name in enumerate(ffc_sequence, 1)}
    ffc = place_footprint(board, "FFC_12P_1.00mm_TopContact.kicad_mod",
                          "JF1", 10, FFC_Y, ffc_map)
    for item in find(ffc, "property"):
        if item[1] == "Reference" and first(item, "hide") is None:
            item.append([Sym("hide"), Sym("yes")])
    contact_file = "MillMax_854-22-012-30-004101.kicad_mod"
    contact_ref = "PS1"
    contact = place_footprint(board, contact_file, contact_ref, 10, CONTACT_Y,
                              contact_map)
    if side == "Left":
        first(contact, "at").append(180)
    add_outline(board)
    # The keyed carrier pocket locates this board from its perimeter; there are
    # deliberately no locating holes through the module.  This is closer to a
    # removable clipped connector cassette and leaves the fanout unobstructed.

    ffc_pads = {int(pad[1]): global_pad(ffc, pad) for pad in find(ffc, "pad")
                if str(pad[1]).isdigit()}
    contact_pads = {int(pad[1]): global_pad(contact, pad)
                    for pad in find(contact, "pad") if str(pad[1]).isdigit()}
    by_net = {}
    for pin, name in contact_map.items():
        by_net.setdefault(name, []).append(contact_pads[pin])
    ffc_by_net = {}
    for pin, name in enumerate(ffc_sequence, 1):
        ffc_by_net.setdefault(name, []).append(ffc_pads[pin])

    # Non-ground conductors escape above the spring connector, cross the
    # module on B.Cu, and return to F.Cu immediately before the FFC.  This
    # avoids passing through the ground pad in the other connector row.
    for name in names:
        if name == "GND":
            continue
        starts = by_net[name]
        ends = ffc_by_net[name]
        anchor_x = sum(point[0] for point in starts) / len(starts)
        anchor = (anchor_x, 2.6)
        for start in starts:
            polyline(board, [start, (start[0], 2.6), anchor], name)
        board.append(via(anchor, name))
        end = ends[0]
        landing = (end[0], 10.3)
        polyline(board, [anchor, landing], name, "B.Cu")
        board.append(via(landing, name))
        polyline(board, [landing, end], name)

    # GND leaves the spring pads on a lower F.Cu bus and leaves the FFC pads
    # through an upper B.Cu bus.  A single edge spine joins those buses, safely
    # outside the ordered B.Cu signal fanout.
    ground_id = "GND"
    lower = []
    for pad in by_net["GND"]:
        escape = (pad[0], 8.0)
        polyline(board, [pad, escape], ground_id)
        lower.append(escape)
    upper = []
    for pad in ffc_by_net["GND"]:
        escape = (pad[0], 11.8)
        polyline(board, [pad, escape], ground_id)
        board.append(via(escape, ground_id))
        upper.append(escape)
    lower = sorted(lower)
    upper = sorted(upper)
    polyline(board, lower, ground_id, "F.Cu")
    polyline(board, upper, ground_id, "B.Cu")
    edge_low = (1.5, 8.0)
    edge_high = (1.5, 11.8)
    polyline(board, [lower[0], edge_low], ground_id)
    board.append(via(edge_low, ground_id))
    polyline(board, [edge_low, edge_high], ground_id, "B.Cu")
    polyline(board, [edge_high, upper[0]], ground_id, "B.Cu")

    add_note(board, f"{side.upper()} {kind.upper()}", (5.0, 1.0))
    path = OUT / f"Symm60HE-Neo-{side}-{kind}Module.kicad_pcb"
    path.write_text(dumps(board) + "\n")
    return path


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    controller = OUT / "Symm60HE-Neo-Controller.kicad_pcb"
    shutil.copy2(ROOT / "pcb/Symm60HE-Daughterboard.kicad_pcb", controller)
    shutil.copy2(ROOT / "pcb/Symm60HE-Daughterboard.kicad_pro",
                 controller.with_suffix(".kicad_pro"))
    halves_and_maps = [build_direct_target_half(side)
                       for side in ("Left", "Right")]
    modules = [build_module(side, pin_map)
               for side, (_, pin_map) in zip(("Left", "Right"), halves_and_maps)]
    for stale in OUT.glob("Symm60HE-Neo-*-TargetModule*"):
        stale.unlink()
    shutil.copy2(ROOT / "pcb/variants/pogo/fp-lib-table", OUT / "fp-lib-table")
    shutil.copy2(ROOT / "pcb/fp-lib-table", OUT / "source-fp-lib-table")
    stale_pinout = OUT / "Symm60HE-neo-pogo16-pinout.csv"
    if stale_pinout.exists():
        stale_pinout.unlink()
    with (OUT / "Symm60HE-neo-pogo12-pinout.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Mill-Max pin", "Left net", "Right net", "Policy"])
        maps = {side: pin_map for side, (_, pin_map) in
                zip(("Left", "Right"), halves_and_maps)}
        for pin in range(1, 13):
            writer.writerow([pin, maps["Left"][pin], maps["Right"][pin],
                             "Power-off only"])
    print(controller.relative_to(ROOT))
    for path in modules:
        print(path.relative_to(ROOT))
    for path, _ in halves_and_maps:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
