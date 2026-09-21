#!/usr/bin/env python3
"""Give every universal-layout Hall position an independent mux channel.

The original 12-way interface scans four SN74LV4051A muxes per half and has
only 32 independently observable positions.  The universal mechanical layout
contains 33 Hall sensors on the left and 36 on the right, so several alternate
positions were electrically tied together.  Populating both sensors in one of
those pairs makes it impossible for firmware to suppress the inactive one.

This candidate-stage transformation adds AML5/AMR5, reassigns the six formerly
shared sensor outputs, and uses one of the two ground conductors in each FFC for
ADC_L5/ADC_R5.  The remaining ground conductor stays between the existing ADC
groups.  On the controller, PA2 (pin 16) and PA1 (pin 15) are the two new ADC
inputs.  Existing switch, Hall, LED, stabilizer, connector, and outline
positions are not changed.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import math
import sys

from shapely.geometry import box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from outline import LEFT_PCB_ENCLOSURE, RIGHT_PCB_ENCLOSURE  # noqa: E402
from rebuild_unrouted_keycap_inset import (  # noqa: E402
    EDGE_CLEARANCE, SEARCH_STEP, at_state, drill_obstacles, mux_signal_cost,
    mux_signal_targets, pad_position, placed_extent, reference, set_at,
)
from sexp import Sym, dumps, find, first, loads, set_uuids  # noqa: E402


HALVES = {
    "Left": {
        "mux": "AML", "cap": "CML", "connector": "JL1",
        "adc": "ADC_L5", "outline": LEFT_PCB_ENCLOSURE,
        "pairs": (("HEL28", "CL28B", "HE_L32"),
                  ("HEL30", "CL30B", "HE_L33")),
        "channels": ("HE_L32", "HE_L33"),
        "ffc_pin": "11",
    },
    "Right": {
        "mux": "AMR", "cap": "CMR", "connector": "JR1",
        "adc": "ADC_R5", "outline": RIGHT_PCB_ENCLOSURE,
        "pairs": (("HER4", "CR4B", "HE_R33"),
                  ("HER26", "CR26B", "HE_R34"),
                  ("HER31", "CR31B", "HE_R35"),
                  ("HER33", "CR33B", "HE_R36")),
        "channels": ("HE_R33", "HE_R34", "HE_R35", "HE_R36"),
        "ffc_pin": "2",
    },
}

CHANNEL_PINS = ("13", "14", "15", "12", "1", "5", "2", "4")


def set_reference(footprint, value):
    for prop in find(footprint, "property"):
        if len(prop) > 2 and prop[1] == "Reference":
            prop[2] = value
            return
    raise RuntimeError("footprint has no Reference property")


def set_pad_net(footprint, number, net_name):
    pads = [pad for pad in find(footprint, "pad") if str(pad[1]) == str(number)]
    if not pads:
        raise RuntimeError(f"{reference(footprint)} has no pad {number}")
    for pad in pads:
        net = next((item for item in pad
                    if isinstance(item, list) and item and item[0] == "net"), None)
        if net is None:
            pad.append([Sym("net"), net_name])
        else:
            net[1:] = [net_name]


def replace_net_on_footprint(footprint, old_name, new_name):
    changed = 0
    for pad in find(footprint, "pad"):
        net = next((item for item in pad
                    if isinstance(item, list) and item and item[0] == "net"), None)
        if net is not None and len(net) > 1 and str(net[1]) == old_name:
            net[1:] = [new_name]
            changed += 1
    return changed


def insert_footprints(board, footprints):
    index = next((i for i in range(len(board) - 1, 0, -1)
                  if isinstance(board[i], list) and board[i] and
                  board[i][0] == "embedded_fonts"), len(board))
    board[index:index] = footprints


def place_new_pair(footprints, outline, mux, cap, connector_ref):
    moving = {reference(mux), reference(cap)}
    fixed = []
    for fp in footprints:
        if reference(fp) in moving:
            continue
        layer = first(fp, "layer")
        if layer and str(layer[1]) == "B.Cu":
            fixed.append(placed_extent(fp).buffer(0.15, join_style=1))
    fixed.extend(drill_obstacles(footprints, moving))
    occupied = unary_union(fixed)
    usable = outline.buffer(-EDGE_CLEARANCE, join_style=1)
    x0, y0, x1, y1 = usable.bounds
    connector = next(fp for fp in footprints if reference(fp) == connector_ref)
    connector_x, connector_y, _ = at_state(connector)
    targets = mux_signal_targets(mux, footprints)
    candidates = []
    x = math.ceil((x0 + 3.0) / SEARCH_STEP) * SEARCH_STEP
    while x <= x1 - 3.0:
        y = math.ceil((max(y0 + 3.0, 25.0)) / SEARCH_STEP) * SEARCH_STEP
        while y <= y1 - 3.0:
            for rotation in (90.0, 270.0):
                pin16 = next(pad for pad in find(mux, "pad")
                             if str(pad[1]) == "16")
                pin_x, pin_y = pad_position(mux, pin16, rotation, x, y)
                vx, vy = pin_x - x, pin_y - y
                length = math.hypot(vx, vy)
                vx, vy = vx / length, vy / length
                for cap_index, direction in enumerate((1.0, -1.0)):
                    cap_x = x + direction * vx * 7.5
                    cap_y = y + direction * vy * 7.5
                    pair = unary_union((
                        placed_extent(mux, x, y, rotation),
                        placed_extent(cap, cap_x, cap_y, 0.0),
                    ))
                    if (usable.contains(pair) and not occupied.intersects(
                            pair.buffer(0.15, join_style=1))):
                        signal_cost = mux_signal_cost(
                            mux, targets, x, y, rotation)
                        bus_cost = 0.30 * math.hypot(
                            x - connector_x, y - connector_y)
                        candidates.append((signal_cost + bus_cost + 8.0 * cap_index,
                                           x, y, cap_x, cap_y, rotation))
            y += SEARCH_STEP
        x += SEARCH_STEP
    if not candidates:
        raise RuntimeError(f"no legal placement for {reference(mux)}")
    _, x, y, cap_x, cap_y, rotation = min(candidates)
    set_at(mux, x, y, rotation)
    set_at(cap, cap_x, cap_y, 0.0)
    return x, y, rotation, cap_x, cap_y


def transform_half(path, side):
    cfg = HALVES[side]
    board = loads(path.read_text())
    footprints = find(board, "footprint")
    by_ref = {reference(fp): fp for fp in footprints}
    if f"{cfg['mux']}5" in by_ref:
        raise RuntimeError(f"{path.name} already contains {cfg['mux']}5")

    for sensor_ref, cap_ref, new_net in cfg["pairs"]:
        sensor = by_ref[sensor_ref]
        cap = by_ref[cap_ref]
        old_net = next(str(item[1]) for pad in find(sensor, "pad")
                       if str(pad[1]) == "3" for item in pad
                       if isinstance(item, list) and item and item[0] == "net")
        set_pad_net(sensor, "3", new_net)
        if replace_net_on_footprint(cap, old_net, new_net) != 1:
            raise RuntimeError(f"expected one {old_net} pad on {cap_ref}")

    mux = deepcopy(by_ref[f"{cfg['mux']}4"])
    cap = deepcopy(by_ref[f"{cfg['cap']}4"])
    set_reference(mux, f"{cfg['mux']}5")
    set_reference(cap, f"{cfg['cap']}5")
    set_uuids(mux)
    set_uuids(cap)
    set_at(mux, 0.0, 0.0, 90.0)
    set_at(cap, 0.0, 0.0, 0.0)

    fixed = {"3": cfg["adc"], "6": "GND", "7": "GND", "8": "GND",
             "9": "MUX_A2", "10": "MUX_A1", "11": "MUX_A0",
             "16": "+3V3A"}
    channel_nets = list(cfg["channels"]) + ["GND"] * (8 - len(cfg["channels"]))
    fixed.update(dict(zip(CHANNEL_PINS, channel_nets)))
    for number, net_name in fixed.items():
        set_pad_net(mux, number, net_name)

    set_pad_net(by_ref[cfg["connector"]], cfg["ffc_pin"], cfg["adc"])
    insert_footprints(board, [mux, cap])
    footprints.extend((mux, cap))
    placement = place_new_pair(
        footprints, cfg["outline"], mux, cap, cfg["connector"])
    path.write_text(dumps(board) + "\n")
    print(f"{path.name}: {cfg['mux']}5 at {placement[0]:.1f},{placement[1]:.1f} "
          f"rot {placement[2]:.0f}; {cfg['cap']}5 at "
          f"{placement[3]:.1f},{placement[4]:.1f}")


def transform_controller(path):
    board = loads(path.read_text())
    by_ref = {reference(fp): fp for fp in find(board, "footprint")}
    # J2 is the left-half cable.  Its numbering is reversed end-to-end, so
    # half-board JL1 pin 11 arrives at J2 pin 2.  J3/JR1 use pin 2 directly.
    set_pad_net(by_ref["J2"], "2", "ADC_L5")
    set_pad_net(by_ref["J3"], "2", "ADC_R5")
    set_pad_net(by_ref["U1"], "16", "ADC_L5")  # PA2 / ADC1_IN2
    set_pad_net(by_ref["U1"], "15", "ADC_R5")  # PA1 / ADC1_IN1
    path.write_text(dumps(board) + "\n")
    print(f"{path.name}: J2.2/U1.16 ADC_L5; J3.2/U1.15 ADC_R5")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    transform_half(args.candidate / "Symm60HE-Left.kicad_pcb", "Left")
    transform_half(args.candidate / "Symm60HE-Right.kicad_pcb", "Right")
    transform_controller(args.candidate / "Symm60HE-Daughterboard.kicad_pcb")


if __name__ == "__main__":
    main()
