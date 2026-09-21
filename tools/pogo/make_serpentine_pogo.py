#!/usr/bin/env python3
"""Generate the cable-free, static-flex FR-4 pogo prototype board set.

The proven FFC boards remain untouched.  This variant replaces their 12-pin
connectors with matched 16-contact Mill-Max 855/857 interfaces and gives the
controller board two symmetric routed compliant arms.  The arms contain only
explicit F.Cu traces: no zones, vias, pads, or components occur in their
moving spans.
"""
from copy import deepcopy
from pathlib import Path
import csv
import math
import shutil
import sys

from shapely.geometry import LineString, box
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
from route import read  # noqa: E402
from sexp import Sym, dumps, find, first, loads, newuuid, set_uuids  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "pcb/variants/pogo-serpentine"
LIB = ROOT / "Symm60HE_Project.pretty"
TRACE_W = 0.18
LANE_PITCH = 0.52
ARM_HALF_WIDTH = 5.15
CENTRE_Y = 9.2367

# The original FFC order is deliberately retained.  Three extra grounds and
# one extra analog-supply contact are inserted beside the related conductors.
LEFT_ORDER = [
    "ADC_L4", "ADC_L3", "GND", "GND", "ADC_L2", "GND", "GND",
    "ADC_L1", "GND", "GND", "MUX_A2", "MUX_A1", "MUX_A0", "GND",
    "+3V3A", "+3V3A",
]
RIGHT_ORDER = [
    "+3V3A", "+3V3A", "GND", "MUX_A0", "MUX_A1", "MUX_A2", "GND",
    "GND", "ADC_R1", "GND", "GND", "ADC_R2", "GND", "GND",
    "ADC_R3", "ADC_R4",
]


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


def swap_front_back(node):
    swaps = {
        "F.Cu": "B.Cu", "F.Mask": "B.Mask", "F.Paste": "B.Paste",
        "F.SilkS": "B.SilkS", "F.Fab": "B.Fab", "F.CrtYd": "B.CrtYd",
    }
    if isinstance(node, list):
        for child in node:
            swap_front_back(child)
    elif isinstance(node, str) and node in swaps:
        # Strings are immutable; handled by the parent traversal below.
        return
    if isinstance(node, list):
        for index, child in enumerate(node):
            if isinstance(child, str) and child in swaps:
                node[index] = swaps[child]


def add_missing_uuids(node):
    """Give board-embedded footprint primitives stable identities."""
    if not isinstance(node, list) or not node:
        return
    for child in node[1:]:
        add_missing_uuids(child)
    if node[0] in ("footprint", "property", "fp_rect", "fp_line", "fp_circle",
                   "fp_arc", "fp_poly", "fp_text", "pad") and not first(node, "uuid"):
        node.append(newuuid())


def connector(board, footprint_name, ref, x, y, rotation, pin_nets, bottom=False):
    fp = loads((LIB / f"{footprint_name}.kicad_mod").read_text())
    fp = deepcopy(fp)
    fp[:] = [item for item in fp
             if not (isinstance(item, list) and item and
                     item[0] in ("version", "generator", "generator_version"))]
    fp.insert(2, [Sym("at"), x, y, rotation])
    for item in find(fp, "property"):
        if item[1] == "Reference":
            item[2] = ref
    if bottom:
        swap_front_back(fp)
    for pad in find(fp, "pad"):
        number = str(pad[1])
        if number.isdigit():
            pad.append([Sym("net"), pin_nets[int(number)]])
    set_uuids(fp)
    add_missing_uuids(fp)
    board.append(fp)
    return fp


def remove_footprint(board, ref):
    kept = []
    removed = None
    for item in board:
        if (isinstance(item, list) and item and item[0] == "footprint" and
                prop(item, "Reference") == ref):
            removed = item
        else:
            kept.append(item)
    if removed is None:
        raise RuntimeError(f"missing footprint {ref}")
    board[:] = kept
    return removed


def segment(a, b, net, layer="F.Cu", width=TRACE_W):
    return [Sym("segment"), [Sym("start"), round(a[0], 5), round(a[1], 5)],
            [Sym("end"), round(b[0], 5), round(b[1], 5)],
            [Sym("width"), width], [Sym("layer"), layer],
            [Sym("net"), net], newuuid()]


def via(point, net):
    return [Sym("via"), [Sym("at"), round(point[0], 5), round(point[1], 5)],
            [Sym("size"), 0.6], [Sym("drill"), 0.3],
            [Sym("layers"), "F.Cu", "B.Cu"], [Sym("net"), net], newuuid()]


def add_polyline(board, points, net, layer="F.Cu", width=TRACE_W):
    clean = []
    for point in points:
        point = (round(float(point[0]), 5), round(float(point[1]), 5))
        if not clean or point != clean[-1]:
            clean.append(point)
    for a, b in zip(clean, clean[1:]):
        if math.dist(a, b) > 1e-5:
            board.append(segment(a, b, net, layer, width))


def replace_outline(board, polygon):
    body = []
    for item in board:
        if (isinstance(item, list) and item and str(item[0]).startswith("gr_") and
                first(item, "layer") and first(item, "layer")[1] == "Edge.Cuts"):
            continue
        body.append(item)
    board[:] = body
    points = list(polygon.exterior.coords)
    for a, b in zip(points, points[1:]):
        board.append([
            Sym("gr_line"), [Sym("start"), round(a[0], 5), round(a[1], 5)],
            [Sym("end"), round(b[0], 5), round(b[1], 5)],
            [Sym("stroke"), [Sym("width"), 0.1], [Sym("type"), Sym("solid")]],
            [Sym("layer"), "Edge.Cuts"], newuuid(),
        ])


def pad_ports(board, old_fp, layer):
    """Remove each old connector's first escape segment and return its far end.

    Leaving the segment that terminated at the removed FFC pad made the wider
    2x8 target fanout cross stale copper.  The far endpoint is the correct
    handoff to the existing half-board routing.
    """
    tracks = [item for item in find(board, "segment")
              if first(item, "layer")[1] == layer]
    ports = []
    remove_ids = set()
    for pad in sorted((p for p in find(old_fp, "pad") if str(p[1]).isdigit()),
                      key=lambda p: int(p[1])):
        net = first(pad, "net")[1]
        centre = global_pad(old_fp, pad)
        candidates = []
        for track in tracks:
            if first(track, "net")[1] != net:
                continue
            start = tuple(map(float, first(track, "start")[1:3]))
            end = tuple(map(float, first(track, "end")[1:3]))
            if math.dist(centre, start) < 0.06:
                candidates.append((math.dist(centre, end), end, track))
            elif math.dist(centre, end) < 0.06:
                candidates.append((math.dist(centre, start), start, track))
        if candidates:
            _, port, track = max(candidates, key=lambda item: item[0])
            remove_ids.add(id(track))
        else:
            port = centre
        ports.append((net, port))
    board[:] = [item for item in board if id(item) not in remove_ids]
    return ports


def expanded_ports(ports, order):
    """Expand parallel contacts while preserving source-pad ordering."""
    by_net = {}
    for net, point in ports:
        by_net.setdefault(net, []).append(point)
    for points in by_net.values():
        points.sort(key=lambda point: (point[1], point[0]))
    used = {net: 0 for net in by_net}
    result = []
    previous = None
    selected = None
    for net in order:
        choices = by_net[net]
        if net != previous:
            index = min(used[net], len(choices) - 1)
            selected = choices[index]
            used[net] += 1
        result.append((net, selected))
        previous = net
    return result


def footprint_ports(fp):
    return [(first(pad, "net")[1], global_pad(fp, pad))
            for pad in sorted((p for p in find(fp, "pad")
                               if str(p[1]).isdigit()),
                              key=lambda p: int(p[1]))]


def make_transition_lands_only(fp):
    """Retain proven FFC copper as DNP/no-paste transition lands."""
    fp[1] = "DNP_TRANSITION_LANDS"
    attr = first(fp, "attr")
    if attr is None:
        attr = [Sym("attr"), Sym("smd")]
        fp.append(attr)
    for flag in (Sym("exclude_from_bom"), Sym("exclude_from_pos_files")):
        if flag not in attr:
            attr.append(flag)
    for item in find(fp, "property"):
        if item[1] == "Value":
            item[2] = "DNP_TRANSITION_LANDS"
    for pad in find(fp, "pad"):
        layers = first(pad, "layers")
        if layers:
            layers[:] = [entry for entry in layers if entry != "F.Paste"]


def pad_pin_map(fp, order):
    pads = sorted((p for p in find(fp, "pad") if str(p[1]).isdigit()),
                  key=lambda p: (round(global_pad(fp, p)[1], 6),
                                 round(global_pad(fp, p)[0], 6)))
    if len(pads) != len(order):
        raise RuntimeError("16-contact footprint has unexpected pad count")
    return {int(pad[1]): net for pad, net in zip(pads, order)}


def offset_lanes(path, count=8, offsets=None):
    lanes = []
    distances = (offsets if offsets is not None else
                 [(index - (count - 1) / 2) * LANE_PITCH
                  for index in range(count)])
    for distance in distances:
        # A true normal-offset curve folds back when the offset approaches the
        # S-curve's local radius.  Translate the monotonic centreline in Y so
        # every conductor retains identical X stations and cannot cross a
        # neighbour near either rigid landing.
        coords = [(x, y + distance) for x, y in path.coords]
        lanes.append(coords)
    return sorted(lanes, key=lambda pts: pts[0][1])


def add_single_layer_arm(board, fp, path, ports, central_via_x):
    """Fan 16 signals through one uninterrupted B.Cu flexure bundle.

    The original FFC transition lands stay on F.Cu.  A via just inside the
    rigid controller island transfers each source to B.Cu; duplicate power
    contacts share that source via.  At the pogo landing every SMT pad gets a
    short F.Cu escape and a via outside the connector body.  No vias occur in
    the compliant span itself.
    """
    # Match the two conductors in every connector row before the bundle fans
    # toward the 1.00 mm-pitch legacy transition lands.
    connector_offsets = [row + spread
                         for row in (-4.445, -3.175, -1.905, -0.635,
                                     0.635, 1.905, 3.175, 4.445)
                         for spread in (-0.30, 0.30)]
    lanes = offset_lanes(path, 16, connector_offsets)
    pads = sorted((p for p in find(fp, "pad") if str(p[1]).isdigit()),
                  key=lambda p: (global_pad(fp, p)[1], global_pad(fp, p)[0]))
    source_vias = {}
    for index, (pad, lane, (port_net, port)) in enumerate(zip(pads, lanes, ports)):
        net = first(pad, "net")[1]
        if net != port_net:
            raise RuntimeError(f"{prop(fp, 'Reference')} pin/lane mismatch")
        source_key = (net, round(port[0], 5), round(port[1], 5))
        source_via = source_vias.get(source_key)
        if source_via is None:
            source_via = (central_via_x, port[1])
            source_vias[source_key] = source_via
            board.append(via(source_via, net))
            add_polyline(board, [port, source_via], net, "F.Cu")

        pad_xy = global_pad(fp, pad)
        in_row = index % 2
        requested_x = pad_xy[0] + (-1.20 if in_row == 0 else 1.20)
        # Join at the nearest X station instead of always using the nominal
        # centreline endpoint.  The outward via for one column lies beyond the
        # endpoint while the other lies before it; forcing both to the same
        # endpoint makes the inner escape double back across its neighbour.
        join_index = min(range(len(lane)),
                         key=lambda idx: abs(lane[idx][0] - requested_x))
        join_point = lane[join_index]
        lo_x, hi_x = sorted((lane[0][0], lane[-1][0]))
        landing_via = (join_point if lo_x <= requested_x <= hi_x else
                       (requested_x, join_point[1]))
        active_lane = lane[:join_index + 1]
        add_polyline(board, [source_via, active_lane[0]], net, "B.Cu")
        add_polyline(board, active_lane, net, "B.Cu")
        board.append(via(landing_via, net))
        add_polyline(board, [active_lane[-1], landing_via], net, "B.Cu")
        add_polyline(board, [landing_via, pad_xy], net, "F.Cu")


def pad_rows(fp):
    pads = sorted((p for p in find(fp, "pad") if str(p[1]).isdigit()),
                  key=lambda p: (global_pad(fp, p)[1], global_pad(fp, p)[0]))
    rows = [pads[index:index + 2] for index in range(0, 16, 2)]
    return rows


def add_arm_fanout(board, fp, path, ports, inner_is_max_x):
    """Route eight conductors per side with vias only in rigid end lands."""
    lanes = offset_lanes(path)
    rows = pad_rows(fp)
    for index, (row, lane) in enumerate(zip(rows, lanes)):
        row = sorted(row, key=lambda p: global_pad(fp, p)[0])
        inner = row[-1] if inner_is_max_x else row[0]
        outer = row[0] if inner_is_max_x else row[-1]
        for pad, layer in ((inner, "F.Cu"), (outer, "B.Cu")):
            net = first(pad, "net")[1]
            occurrence = 2 * index + (0 if pad is row[0] else 1)
            port_net, port = ports[occurrence]
            if port_net != net:
                raise RuntimeError(f"{prop(fp, 'Reference')} pin/lane mismatch")
            if layer == "F.Cu":
                shoulder = ((153.1 if inner_is_max_x else 213.3), port[1])
                add_polyline(board, [port, shoulder, lane[0]], net, "F.Cu")
                add_polyline(board, lane, net, "F.Cu")
                add_polyline(board, [lane[-1], global_pad(fp, pad)], net, "F.Cu")
            else:
                shoulder = ((153.1 if inner_is_max_x else 213.3), port[1])
                pad_xy = global_pad(fp, pad)
                outside = -1.0 if inner_is_max_x else 1.0
                outer_via = (pad_xy[0] + outside * 1.25, pad_xy[1])
                board.append(via(shoulder, net))
                board.append(via(outer_via, net))
                add_polyline(board, [port, shoulder], net, "F.Cu")
                add_polyline(board, [shoulder, lane[0]], net, "B.Cu")
                add_polyline(board, lane, net, "B.Cu")
                add_polyline(board, [lane[-1], outer_via], net, "B.Cu")
                add_polyline(board, [outer_via, pad_xy], net, "F.Cu")


def add_target_fanout(board, fp, ports, inner_is_max_x):
    """Use the empty rigid tongue as a two-layer 8+8 connector fanout."""
    rows = pad_rows(fp)
    side = 1.0 if inner_is_max_x else -1.0
    for index, row in enumerate(rows):
        row = sorted(row, key=lambda p: global_pad(fp, p)[0])
        inner = row[-1] if inner_is_max_x else row[0]
        outer = row[0] if inner_is_max_x else row[-1]
        for pad, direct in ((inner, True), (outer, False)):
            net = first(pad, "net")[1]
            occurrence = 2 * index + (0 if pad is row[0] else 1)
            port_net, port = ports[occurrence]
            if port_net != net:
                raise RuntimeError(f"{prop(fp, 'Reference')} target mismatch")
            pad_xy = global_pad(fp, pad)
            if direct:
                add_polyline(board, [pad_xy, port], net, "B.Cu")
            else:
                outer_via = (pad_xy[0] - side * 1.15, pad_xy[1])
                inner_via = (port[0] + side * 0.75, port[1])
                board.append(via(outer_via, net))
                board.append(via(inner_via, net))
                add_polyline(board, [pad_xy, outer_via], net, "B.Cu")
                add_polyline(board, [outer_via, inner_via], net, "F.Cu")
                add_polyline(board, [inner_via, port], net, "B.Cu")


def add_note(board, text, x, y, layer="F.SilkS"):
    board.append([
        Sym("gr_text"), text, [Sym("at"), x, y], [Sym("layer"), layer],
        newuuid(), [Sym("effects"),
                    [Sym("font"), [Sym("size"), 0.8, 0.8],
                     [Sym("thickness"), 0.12]],
                    [Sym("justify"), Sym("left")]],
    ])


def serpentine(x0, x1, samples=40):
    """Monotonic, smooth S flexure with horizontal tangents at both ends."""
    points = []
    for index in range(samples + 1):
        t = index / samples
        x = x0 + (x1 - x0) * t
        y = CENTRE_Y + 5.6 * math.sin(2 * math.pi * t) ** 3
        points.append((x, y))
    return LineString(points)


def build_daughterboard():
    source = ROOT / "pcb/Symm60HE-Daughterboard.kicad_pcb"
    board, _, central_outline, _ = read(str(source))
    first(first(board, "general"), "thickness")[1] = 0.8
    footprints = {prop(fp, "Reference"): fp for fp in find(board, "footprint")}
    left_old = footprints["J2"]
    right_old = footprints["J3"]
    make_transition_lands_only(left_old)
    make_transition_lands_only(right_old)

    left_path = serpentine(149.0, 112.0)
    right_path = serpentine(217.3, 254.3)
    landing_left = box(105.3, 2.1, 118.7, 16.4).buffer(1.6, join_style=1)
    landing_right = box(247.6, 2.1, 261.0, 16.4).buffer(1.6, join_style=1)
    outline = unary_union([
        central_outline,
        box(148.8, -2.0, 155.5, 16.0),
        box(210.9, -2.0, 217.6, 16.0),
        left_path.buffer(ARM_HALF_WIDTH, cap_style=2, join_style=1),
        right_path.buffer(ARM_HALF_WIDTH, cap_style=2, join_style=1),
        landing_left, landing_right,
    ]).buffer(0)
    if outline.geom_type != "Polygon":
        raise RuntimeError(f"daughterboard outline is {outline.geom_type}")
    replace_outline(board, outline)

    # First insert placeholders so their physical pad ordering can define the
    # side-specific pin map; then assign those maps to fresh footprints.
    blank = {pin: "GND" for pin in range(1, 17)}
    left_fp = connector(board, "MillMax_855-22-016-30-004101", "PSL1",
                        112.0, CENTRE_Y, 90, blank)
    board.remove(left_fp)
    left_map = pad_pin_map(left_fp, LEFT_ORDER)
    left_fp = connector(board, "MillMax_855-22-016-30-004101", "PSL1",
                        112.0, CENTRE_Y, 90, left_map)
    right_fp = connector(board, "MillMax_855-22-016-30-004101", "PSR1",
                         254.3, CENTRE_Y, -90, blank)
    board.remove(right_fp)
    right_map = pad_pin_map(right_fp, RIGHT_ORDER)
    right_fp = connector(board, "MillMax_855-22-016-30-004101", "PSR1",
                         254.3, CENTRE_Y, -90, right_map)

    left_ports = expanded_ports(footprint_ports(left_old), LEFT_ORDER)
    right_ports = expanded_ports(footprint_ports(right_old), RIGHT_ORDER)
    add_single_layer_arm(board, left_fp, left_path, left_ports, 159.00)
    add_single_layer_arm(board, right_fp, right_path, right_ports, 208.30)
    add_note(board, "STATIC-FLEX ONLY / NO VIAS OR POUR IN ARMS", 118.8, 19.0)
    add_note(board, "POWER OFF BEFORE MATING", 223.0, 19.0)
    target = OUT / "Symm60HE-Serpentine-Daughterboard.kicad_pcb"
    target.write_text(dumps(board) + "\n")
    shutil.copy2(ROOT / "pcb/Symm60HE-Daughterboard.kicad_pro",
                 target.with_suffix(".kicad_pro"))
    shutil.copy2(ROOT / "pcb/variants/pogo/fp-lib-table", OUT / "fp-lib-table")
    return left_map, right_map


def build_half(filename, old_ref, new_ref, x, rotation, order, pin_map):
    source = ROOT / f"pcb/{filename}.kicad_pcb"
    board = loads(source.read_text())
    old = remove_footprint(board, old_ref)
    source_ports = pad_ports(board, old, "B.Cu")
    fp = connector(board, "MillMax_857-10-016-30-051000", new_ref,
                   x, 56.0, rotation, pin_map, bottom=True)
    pads = sorted((p for p in find(fp, "pad") if str(p[1]).isdigit()),
                  key=lambda p: (global_pad(fp, p)[1], global_pad(fp, p)[0]))
    physical_order = [first(p, "net")[1] for p in pads]
    ports = expanded_ports(source_ports, physical_order)
    add_target_fanout(board, fp, ports, old_ref == "JL1")
    add_note(board, "POGO16 / POWER-OFF ONLY", x - 8.0, 67.0, "B.SilkS")
    target = OUT / f"{filename}-PogoTarget.kicad_pcb"
    target.write_text(dumps(board) + "\n")
    shutil.copy2(ROOT / f"pcb/{filename}.kicad_pro", target.with_suffix(".kicad_pro"))


def write_pinout(left_map, right_map):
    with (OUT / "Symm60HE-serpentine-pogo16-pinout.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Pin", "Left net", "Right net", "Policy"])
        for pin in range(1, 17):
            writer.writerow([pin, left_map[pin], right_map[pin], "Power-off only"])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    left_map, right_map = build_daughterboard()
    write_pinout(left_map, right_map)
    print(OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
