#!/usr/bin/env python3
"""Build the magnetic-pogo variant of the split link.

Same architecture as ``pogo-neo`` -- rigid controller, one floating module per
side, target soldered straight to the Hall PCB -- but the Mill-Max 854/856
pair is replaced by a 12-contact magnetic pogo pair in two rows of six on a
2.54 mm grid, built to the interface control drawing in
``pcb/variants/pogo-magnetic/README.md``. The magnets live in the connector
housing and pull the joint into alignment, which is the whole point: the
854/856 pair self-aligns only within 0.0596 mm radial.

The footprints are dimensioned to that ICD, not to a supplier drawing. Confirm
every dimension against the drawing that comes back before ordering stencils.
"""
from copy import deepcopy
from itertools import combinations, product
from pathlib import Path
import csv
import math
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_serpentine_pogo import (add_missing_uuids, global_pad, prop,
                                  swap_front_back)  # noqa: E402
from make_neo_pogo import (FFC_NETS, TRACE_W, VIA_DRILL, VIA_SIZE,  # noqa: E402
                           add_note, place_footprint, polyline, renamed,
                           segment, skeleton, via)
from shapely.geometry import LineString, Point  # noqa: E402

from sexp import Sym, dumps, find, first, loads, set_uuids  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "pcb/variants/pogo-magnetic"
LIB = ROOT / "Symm60HE_Project.pretty"

# --- interface control drawing MAGPOGO-2x6-P254 -----------------------------
PITCH = 2.54          # along a row
ROW_GAP = 2.54        # between the two rows
PER_ROW = 6
BODY = (25.0, 9.0)    # connector housing envelope

# --- module -----------------------------------------------------------------
MODULE_W = 32.0
MODULE_H = 18.0
CONTACT_X = MODULE_W / 2
CONTACT_Y = 5.6       # connector centre; rows land at +/- 1.27 of this
FFC_Y = 15.0          # ZIF centre, on B.Cu behind the connector
ESCAPE_Y = 9.6        # single row of escape vias below the connector
HANDOFF_VIA_SETBACK = 0.3  # keep layer changes off the crowded anchor line
OUTER_TURN = 2.5           # where the far column turns toward its anchor

SPRING_FP = "MagPogo_2x6_P254_Spring.kicad_mod"
TARGET_FP = "MagPogo_2x6_P254_Target.kicad_mod"

# Footprint pins 1-6 are the far row (away from the ZIF), 7-12 the near row.
# Each far-row contact escapes through the gap between two near-row pads, one
# half pitch further out, so the twelve escape vias land in a single row.
FAR = tuple(range(1, PER_ROW + 1))
NEAR = tuple(range(PER_ROW + 1, 2 * PER_ROW + 1))

# The eight signals in the order the controller's ZIF presents them. Ground is
# not in this list: it has four contacts and four ZIF pads, and ground crossing
# ground costs nothing, so it fills whatever slots the signals leave.
SIGNAL_ORDER = tuple(net for net in FFC_NETS if net != "GND")


def solve_contact_map(column_of, half_y, anchor_rank, group_of):
    """Pick which contact carries which signal.

    Two orderings have to hold at once and neither is ours to choose:

      * on the module, the escape lanes run left to right in the ZIF's net
        order, so the B.Cu fan is a set of parallel doglegs;
      * on the half, each contact column reaches its handoff anchors without
        crossing, so the signals in a column must climb in the same order as
        the anchors they are heading for.

    Both are monotonicity constraints, so fixing which eight of the twelve
    contacts carry signals fixes everything else. There are only 495 such
    choices; take the first that satisfies both.
    """
    # The module's lane order should be the ZIF's net order, but allowing one
    # adjacent pair to arrive swapped buys a lot of freedom here and costs one
    # short hop to the other layer on a board that has room for it.
    orders = [SIGNAL_ORDER]
    for i in range(len(SIGNAL_ORDER) - 1):
        swapped = list(SIGNAL_ORDER)
        swapped[i], swapped[i + 1] = swapped[i + 1], swapped[i]
        orders.append(tuple(swapped))

    best = None
    for flip in (False, True):
        pins = sorted(range(1, 2 * PER_ROW + 1),
                      key=lambda pin: escape_x(pin, flip))
        for order, chosen in product(orders, combinations(pins, len(SIGNAL_ORDER))):
            mapping = dict(zip(chosen, order))
            def monotonic(key):
                for bucket in (0, 1):
                    members = [pin for pin in chosen
                               if key(pin, mapping[pin]) == bucket]
                    ranks = [anchor_rank[mapping[pin]]
                             for pin in sorted(members, key=lambda p: half_y[p])]
                    if ranks != sorted(ranks):
                        return False
                return True

            # Contacts in a column must not cross each other. Nets sharing a
            # layer at the boundary should not either, but demanding both at
            # once leaves no assignment at all, so the layer grouping is only
            # a preference: see `cost` below.
            if not monotonic(lambda pin, net: column_of[pin]):
                continue
            layered = 0 if monotonic(
                lambda pin, net: group_of(column_of[pin], net)) else 1
            # Anchors are packed far tighter than contacts, so two nets whose
            # anchors are neighbours and whose contacts are in different
            # columns have to converge on the same few square millimetres from
            # opposite sides. Prefer the assignment that does that least.
            by_anchor = sorted(chosen, key=lambda pin: anchor_rank[mapping[pin]])
            swaps = sum(column_of[a] != column_of[b]
                        for a, b in zip(by_anchor, by_anchor[1:]))
            cost = (layered, orders.index(order), swaps)
            if best is None or cost < best[0]:
                best = (cost, {pin: mapping.get(pin, "GND")
                               for pin in range(1, 2 * PER_ROW + 1)}, flip)
    if best is None:
        raise RuntimeError("no contact assignment satisfies both orderings")
    return best[1], best[2]

DIRECT_TARGET = {
    "Left": {"old_ref": "JL1", "new_ref": "PTL1", "boundary": 144.4,
             "x": 148.0, "rotation": -90.0},
    "Right": {"old_ref": "JR1", "new_ref": "PTR1", "boundary": 157.4,
              "x": 154.418, "rotation": 90.0},
}


def contact_map(base, side_letter):
    return {pin: renamed(net, side_letter) for pin, net in base.items()}


def row_x(index):
    return CONTACT_X + (index - (PER_ROW - 1) / 2) * PITCH


def contact_point(pin, flip):
    """Where a contact pad lands on the module, for either spring orientation."""
    index = (pin - 1) % PER_ROW
    x, y = row_x(index), CONTACT_Y + (ROW_GAP / 2 if pin in NEAR else -ROW_GAP / 2)
    return (2 * CONTACT_X - x, 2 * CONTACT_Y - y) if flip else (x, y)


def escape_x(pin, flip=False):
    """Where a contact drops to B.Cu: near row straight down, far row offset.

    A far-row contact steps half a pitch outboard so it can pass through the
    gap between two near-row pads; the near row goes straight down.
    """
    x, y = contact_point(pin, flip)
    if y > CONTACT_Y:
        return x
    return x + (-PITCH / 2 if x < CONTACT_X else PITCH / 2)


def add_outline(board, width, height):
    corners = [(0, 0), (width, 0), (width, height), (0, height), (0, 0)]
    for start, end in zip(corners, corners[1:]):
        board.append([
            Sym("gr_line"), [Sym("start"), *start], [Sym("end"), *end],
            [Sym("stroke"), [Sym("width"), 0.1], [Sym("type"), Sym("solid")]],
            [Sym("layer"), "Edge.Cuts"], __import__("sexp").newuuid(),
        ])


def build_module(side, base_map, flip):
    side_letter = "L" if side == "Left" else "R"
    ffc_sequence = [renamed(name, side_letter) for name in FFC_NETS]
    board = skeleton()
    ffc = place_footprint(board, "FFC_12P_1.00mm_TopContact.kicad_mod", "JF1",
                          CONTACT_X, FFC_Y,
                          {pin: name for pin, name in enumerate(ffc_sequence, 1)})
    swap_front_back(ffc)
    ffc[:] = [item for item in ffc if not (
        isinstance(item, list) and item and item[0] == "fp_text")]
    for item in find(ffc, "property"):
        if first(item, "hide") is None:
            item.append([Sym("hide"), Sym("yes")])

    pins = contact_map(base_map, side_letter)
    contact = place_footprint(board, SPRING_FP, "PS1", CONTACT_X, CONTACT_Y, pins)
    if flip:
        # Turning the spring half end for end is the spare degree of freedom
        # that lets one contact map satisfy the module and the half at once.
        first(contact, "at").append(180)
    add_outline(board, MODULE_W, MODULE_H)
    add_note(board, "MAGPOGO-2x6-P254 spring half; magnets in housing",
             (CONTACT_X, MODULE_H - 1.0))

    contact_pads = {int(pad[1]): global_pad(contact, pad)
                    for pad in find(contact, "pad") if str(pad[1]).isdigit()}
    ffc_pads = {int(pad[1]): global_pad(ffc, pad) for pad in find(ffc, "pad")
                if str(pad[1]).isdigit()}
    ffc_by_net = {}
    for pin, name in enumerate(ffc_sequence, 1):
        ffc_by_net.setdefault(name, []).append(ffc_pads[pin])

    # Signals drop to B.Cu in one lane row and fan to the ZIF. Ground never
    # joins that fan: it stays on F.Cu, meets a bus, and the ZIF's four ground
    # pads come up to the same bus. Ground crossing ground is free; ground
    # crossing the signal fan is not, and this keeps them apart.
    BUS_Y = 12.0
    lanes, ground = {}, []
    for pin, point in sorted(contact_pads.items()):
        net = pins[pin]
        far = point[1] < CONTACT_Y
        shift = (-PITCH / 2 if point[0] < CONTACT_X else PITCH / 2) if far else 0.0
        lane_x = point[0] + shift
        path = [point]
        if far:
            # Step sideways in the clear band between the two rows, then pass
            # through the gap between two near-row pads.
            path += [(point[0], point[1] + 0.55), (lane_x, point[1] + ROW_GAP / 2)]
        if net == "GND":
            path.append((lane_x, BUS_Y))
            polyline(board, path, net, "F.Cu")
            ground.append((lane_x, BUS_Y))
        else:
            lane = (lane_x, ESCAPE_Y)
            path.append(lane)
            polyline(board, path, net, "F.Cu")
            board.append(via(lane, net))
            lanes[pin] = lane

    signal_fan = sorted(lanes.items(), key=lambda item: item[1][0])
    used = {}
    runs = []
    for pin, lane in signal_fan:
        net = pins[pin]
        index = used.setdefault(net, 0)
        used[net] += 1
        runs.append((lane, sorted(ffc_by_net[net])[index], net))
    # If the solver had to swap one adjacent pair to satisfy the half, the two
    # runs cross exactly once. Lift the left-hand one onto F.Cu for the middle
    # of its run and drop it back; the ground bus sits below that band.
    hop = {index for index in range(len(runs) - 1)
           if runs[index][1][0] > runs[index + 1][1][0]}
    for index, (lane, end, net) in enumerate(runs):
        knee = (end[0], FFC_Y - 2.6)
        if index in hop:
            up = (lane[0] + (knee[0] - lane[0]) * 0.2, ESCAPE_Y + 0.5)
            down = (lane[0] + (knee[0] - lane[0]) * 0.8, ESCAPE_Y + 1.9)
            polyline(board, [lane, up], net, "B.Cu")
            board.append(via(up, net))
            polyline(board, [up, down], net, "F.Cu")
            board.append(via(down, net))
            polyline(board, [down, knee, end], net, "B.Cu")
        else:
            polyline(board, [lane, knee, end], net, "B.Cu")

    for end in sorted(ffc_by_net["GND"]):
        transfer = (end[0], FFC_Y - 2.2)
        polyline(board, [transfer, end], "GND", "B.Cu")
        board.append(via(transfer, "GND"))
        polyline(board, [transfer, (end[0], BUS_Y)], "GND", "F.Cu")
        ground.append((end[0], BUS_Y))
    polyline(board, sorted(set(ground)), "GND", "F.Cu")

    path = OUT / f"Symm60HE-Mag-{side}-SpringModule.kicad_pcb"
    path.write_text(dumps(board) + "\n")
    return path


def build_half(side):
    cfg = DIRECT_TARGET[side]
    side_letter = "L" if side == "Left" else "R"
    source = ROOT / f"pcb/Symm60HE-{side}.kicad_pcb"
    board = loads(source.read_text())
    old = next(fp for fp in find(board, "footprint")
               if prop(fp, "Reference") == cfg["old_ref"])
    connector_nets = {first(pad, "net")[1] for pad in find(old, "pad")
                      if first(pad, "net")}
    boundary = cfg["boundary"]
    is_left = side == "Left"
    anchors, kept = [], []
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
        start_in = start[0] >= boundary if is_left else start[0] <= boundary
        end_in = end[0] >= boundary if is_left else end[0] <= boundary
        if start_in and end_in:
            continue
        if not start_in and not end_in:
            kept.append(item)
            continue
        if abs(end[0] - start[0]) < 1e-9:
            continue
        ratio = (boundary - start[0]) / (end[0] - start[0])
        handoff = (boundary, start[1] + ratio * (end[1] - start[1]))
        outside = start if not start_in else end
        kept.append(segment(outside, handoff, first(item, "net")[1],
                            first(item, "layer")[1],
                            float(first(item, "width")[1])))
        anchors.append((first(item, "net")[1], handoff,
                        first(item, "layer")[1], outside))
    board[:] = kept
    board[:] = [item for item in board if item is not old and not (
        isinstance(item, list) and item and item[0] == "via" and
        first(item, "net")[1] in connector_nets and
        44 <= float(first(item, "at")[2]) <= 68 and
        ((float(first(item, "at")[1]) >= boundary) if is_left else
         (float(first(item, "at")[1]) <= boundary)))]

    signal_anchors = {}
    for net, point, layer, outside in anchors:
        if net != "GND":
            signal_anchors.setdefault(net, []).append((point, layer, outside))
    signal_anchors = {net: values[len(values) // 2]
                      for net, values in signal_anchors.items()}

    def placed_target(rotation):
        fp = deepcopy(loads((LIB / TARGET_FP).read_text()))
        fp[:] = [item for item in fp if not (
            isinstance(item, list) and item and item[0] in
            ("version", "generator", "generator_version"))]
        fp.insert(2, [Sym("at"), cfg["x"], 56.0, rotation])
        for item in find(fp, "property"):
            if item[1] == "Reference":
                item[2] = cfg["new_ref"]
        swap_front_back(fp)
        set_uuids(fp)
        add_missing_uuids(fp)
        return fp

    fp = placed_target(cfg["rotation"])
    board.append(fp)
    placed = {int(pad[1]): pad for pad in find(fp, "pad")
              if str(pad[1]).isdigit()}
    pads = {number: global_pad(fp, pad) for number, pad in placed.items()}

    # Which side of the connector centreline each contact landed on, and the
    # order the anchors want to be met in.
    columns = sorted({round(point[0], 3) for point in pads.values()})
    assert len(columns) == 2, columns
    column_of = {number: int(point[0] > cfg["x"]) for number, point in pads.items()}
    half_y = {number: point[1] for number, point in pads.items()}
    ordered = sorted(signal_anchors, key=lambda net: signal_anchors[net][0][1])
    anchor_rank = {net: rank for rank, net in enumerate(ordered)}
    inner_column = int(min(columns) > cfg["x"]) if is_left else int(max(columns) > cfg["x"])
    layer_of = {(net.replace(side_letter, "", 1)
                 if net.startswith(f"ADC_{side_letter}") else net):
                signal_anchors[net][1] for net in signal_anchors}

    def group_of(column, net):
        return 0 if (column == inner_column and layer_of[net] == "B.Cu") else 1

    ranks = {net.replace(side_letter, "", 1)
             if net.startswith(f"ADC_{side_letter}") else net: rank
             for net, rank in anchor_rank.items()}
    try:
        base_map, flip = solve_contact_map(column_of, half_y, ranks, group_of)
    except RuntimeError:
        # Turning the target end for end swaps which contact column faces the
        # handoff line, which is the last degree of freedom available here.
        board.remove(fp)
        fp = placed_target(cfg["rotation"] + 180)
        board.append(fp)
        placed = {int(pad[1]): pad for pad in find(fp, "pad")
                  if str(pad[1]).isdigit()}
        pads = {number: global_pad(fp, pad) for number, pad in placed.items()}
        column_of = {number: int(point[0] > cfg["x"])
                     for number, point in pads.items()}
        half_y = {number: point[1] for number, point in pads.items()}
        base_map, flip = solve_contact_map(column_of, half_y, ranks, group_of)
    pins = contact_map(base_map, side_letter)
    for number, pad in placed.items():
        pad.append([Sym("net"), pins[number]])

    # The target sits on B.Cu, so the column nearer the handoff line simply
    # runs out on B.Cu. The far column cannot: its runs would cross the near
    # column's pads. It hops to F.Cu through a via tucked between two of its
    # own pads, and crosses over on the other layer. With the contact map
    # solved for monotonic order, every run is then a single straight segment.
    inner_x = min(columns) if is_left else max(columns)
    approach = {}
    for number, point in sorted(pads.items()):
        net = pins[number]
        if net == "GND":
            continue
        if abs(point[0] - inner_x) < 0.01:
            approach[net] = point
        else:
            turn_x = boundary + (OUTER_TURN if is_left else -OUTER_TURN)
            approach[net] = (turn_x, point[1] + PITCH / 2)

    for number, point in sorted(pads.items()):
        net = pins[number]
        if net == "GND":
            continue
        handoff, layer, outward = signal_anchors[net]
        if abs(point[0] - inner_x) < 0.01:
            run, start = "B.Cu", point
        else:
            hop = (point[0], point[1] + PITCH / 2)
            polyline(board, [point, hop], net, "B.Cu")
            board.append(via(hop, net))
            # Hold the far column's runs at their own y until they are clear
            # of the near column, so they cross the crowded anchor band as
            # short diagonals rather than long ones.
            turn_x = boundary + (OUTER_TURN if is_left else -OUTER_TURN)
            elbow = (turn_x, hop[1])
            polyline(board, [hop, elbow], net, "F.Cu")
            run, start = "F.Cu", elbow
        if layer == run:
            polyline(board, [start, handoff], net, run)
        else:
            # Change layers before the handoff, at whichever setback puts the
            # via furthest from its neighbours. The anchors are packed much
            # tighter than the contacts, so a fixed setback that suits one net
            # drops another's via straight onto the trace next door.
            span = math.dist(start, handoff)
            def candidate(setback):
                ratio = 1 - min(setback, span * 0.8) / span
                return (start[0] + ratio * (handoff[0] - start[0]),
                        start[1] + ratio * (handoff[1] - start[1]))
            # Change layers before the handoff, at whichever setback puts the
            # via furthest from the neighbouring runs. The anchors are packed
            # far tighter than the contacts, so one fixed setback that suits
            # one net drops another's via straight onto the trace next door.
            neighbours = [LineString([q, signal_anchors[other][0]])
                          for other, q in approach.items() if other != net]
            turn = max((candidate(HANDOFF_VIA_SETBACK + step * 0.1)
                        for step in range(0, 26)),
                       key=lambda q: min(line.distance(Point(q))
                                         for line in neighbours))
            polyline(board, [start, turn], net, run)
            board.append(via(turn, net))
            polyline(board, [turn, handoff], net, layer)

    output = OUT / f"Symm60HE-Mag-{side}-Half.kicad_pcb"
    output.write_text(dumps(board) + "\n")
    shutil.copy2(source.with_suffix(".kicad_pro"), output.with_suffix(".kicad_pro"))
    return output, (base_map, flip)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    controller = OUT / "Symm60HE-Mag-Controller.kicad_pcb"
    shutil.copy2(ROOT / "pcb/Symm60HE-Daughterboard.kicad_pcb", controller)
    shutil.copy2(ROOT / "pcb/Symm60HE-Daughterboard.kicad_pro",
                 controller.with_suffix(".kicad_pro"))
    halves = [build_half(side) for side in ("Left", "Right")]
    maps = {side: base for side, (_, base) in zip(("Left", "Right"), halves)}
    paths = [path for path, _ in halves]
    paths += [build_module(side, *maps[side]) for side in ("Left", "Right")]
    shutil.copy2(ROOT / "pcb/variants/pogo/fp-lib-table", OUT / "fp-lib-table")
    with (OUT / "Symm60HE-mag-pogo12-pinout.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Contact", "Row", "Left net", "Right net", "Policy"])
        for pin in range(1, 2 * PER_ROW + 1):
            writer.writerow([pin, "far" if pin in FAR else "near",
                             renamed(maps["Left"][0][pin], "L"),
                             renamed(maps["Right"][0][pin], "R"),
                             "Power-off only"])
    print(controller.relative_to(ROOT))
    for path in paths:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
