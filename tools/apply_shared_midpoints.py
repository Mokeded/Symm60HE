#!/usr/bin/env python3
"""Replace close universal-layout Hall pairs with one midpoint sensor.

The two bottom-row close pairs and the normal/stepped Caps Lock pair are only
4.7625 mm apart.  Each pair therefore keeps both mechanical switch positions,
but has one MT9102ET at the midpoint and one RC/decoupling capacitor pair.
Wider alternatives remain separate populate-one sensor positions.

The transformation is deliberately idempotent and operates only on the named
footprints.  Existing routed pad escapes are retained: short 0.2 mm 45/straight
bridges connect the midpoint sensor pads to the former primary sensor pads.
"""
from copy import deepcopy
from pathlib import Path
import argparse
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import Sym, dumps, find, first, loads, newuuid, set_uuids  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PITCH_QUARTER = 19.05 / 4.0
TRACE_WIDTH = 0.20

PAIRS = {
    "Left": (
        # primary, alternate, midpoint, mechanical references, removed caps
        ("HEL27", "HEL28", (10.9535, 85.725),
         "KML27N", "KML27A", ("CL28A", "CL28B")),
    ),
    "Right": (
        ("HER30", "HER31", (255.7460, 85.725),
         "KMR30N", "KMR30A", ("CR31A", "CR31B")),
    ),
}


def reference(fp):
    return next((str(item[2]) for item in find(fp, "property")
                 if len(item) > 2 and item[1] == "Reference"), "")


def set_reference(fp, value):
    for item in find(fp, "property"):
        if len(item) > 2 and item[1] == "Reference":
            item[2] = value


def point(item, key):
    value = first(item, key)
    return round(float(value[1]), 4), round(float(value[2]), 4)


def layer_of(item):
    layer = first(item, "layer")
    return str(layer[1]) if layer else ""


def pad_global(fp, pad):
    origin = first(fp, "at")
    local = first(pad, "at")
    x, y = float(origin[1]), float(origin[2])
    px, py = float(local[1]), float(local[2])
    angle = math.radians(-(float(origin[3]) if len(origin) > 3 else 0.0))
    return (round(x + px * math.cos(angle) - py * math.sin(angle), 4),
            round(y + px * math.sin(angle) + py * math.cos(angle), 4))


def numbered_pads(fp):
    return {str(pad[1]): pad for pad in find(fp, "pad")
            if str(pad[1]).isdigit()}


def segment(start, end, net, layer="B.Cu"):
    return [Sym("segment"), [Sym("start"), *start], [Sym("end"), *end],
            [Sym("width"), TRACE_WIDTH], [Sym("layer"), layer],
            [Sym("net"), net], newuuid()]


def polyline(points, net, layer="B.Cu"):
    return [segment(start, end, net, layer)
            for start, end in zip(points, points[1:]) if start != end]


def rip_local(board, bounds, nets):
    x0, x1, y0, y1 = bounds
    def inside(p):
        return x0 <= p[0] <= x1 and y0 <= p[1] <= y1
    board[:] = [item for item in board if not (
        isinstance(item, list) and item and item[0] == "segment" and
        layer_of(item) == "B.Cu" and str(first(item, "net")[1]) in nets and
        inside(point(item, "start")) and inside(point(item, "end")))]


def remove_vias_at(board, positions, net="GND"):
    targets = {(round(x, 4), round(y, 4)) for x, y in positions}
    board[:] = [item for item in board if not (
        isinstance(item, list) and item and item[0] == "via" and
        str(first(item, "net")[1]) == net and point(item, "at") in targets)]


def place(fp, x, y, angle=0.0):
    at = first(fp, "at")
    at[1], at[2] = x, y
    if len(at) > 3:
        at[3] = angle
    elif angle:
        at.append(angle)


def make_sensor(primary, midpoint):
    sensor = deepcopy(primary)
    sensor[1] = "HE_SHARED_MIDPOINT"
    at = first(sensor, "at")
    at[1], at[2] = midpoint
    if len(at) > 3:
        at[3] = 90.0
    else:
        at.append(90.0)
    # Keep only the SOT-23 copper/courtyard/fab and the sensor 3D model.
    sensor[:] = [item for item in sensor if not (
        isinstance(item, list) and item and
        ((item[0] == "pad" and not str(item[1]).isdigit()) or
         (str(item[0]).startswith("fp_") and
          layer_of(item) in {"Dwgs.User", "Eco1.User"})))]
    set_uuids(sensor)
    return sensor


def make_mechanical(source, new_reference, stepped=False):
    mechanical = deepcopy(source)
    mechanical[1] = "HE_KEY_MECHANICAL_ONLY"
    set_reference(mechanical, new_reference)
    for item in find(mechanical, "property"):
        if len(item) > 2 and item[1] == "Value":
            item[2] = "MX_MECHANICAL_ONLY"
    # Retain only the keycap/switch drawings and the two MX alignment holes.
    mechanical[:] = [item for item in mechanical if not (
        isinstance(item, list) and item and
        ((item[0] == "pad" and str(item[1]).isdigit()) or
         (str(item[0]).startswith("fp_") and
          layer_of(item) not in {"Dwgs.User", "Eco1.User"}) or
         item[0] == "model"))]
    attr = first(mechanical, "attr")
    if attr:
        attr[:] = [Sym("attr"), Sym("board_only"),
                   Sym("exclude_from_pos_files"), Sym("exclude_from_bom")]
    else:
        mechanical.append([Sym("attr"), Sym("board_only"),
                           Sym("exclude_from_pos_files"), Sym("exclude_from_bom")])
    if stepped:
        # The 1.75u cap stays centred; only the MX switch geometry moves 0.25u
        # left.  Dwgs.User is the cap envelope, Eco1.User and NPTH pads are the
        # switch geometry.
        for item in mechanical:
            if not isinstance(item, list) or not item:
                continue
            shift = ((item[0] == "pad" and not str(item[1]).isdigit()) or
                     (str(item[0]).startswith("fp_") and
                      layer_of(item) == "Eco1.User"))
            if not shift:
                continue
            for key in ("at", "start", "end", "center", "mid"):
                coord = first(item, key)
                if coord and len(coord) > 2:
                    coord[1] = round(float(coord[1]) - PITCH_QUARTER, 4)
    set_uuids(mechanical)
    return mechanical


def remove_pad_branches(board, removed_points):
    """Remove copper stubs that terminated only at deleted SMT pads.

    Only the first segment touching each removed pad is removed.  The source
    routing fans these pads out with a private escape segment, so this leaves
    the shared trunks intact and makes accidental broad rerouting impossible.
    """
    points = {(round(x, 4), round(y, 4), net)
              for x, y, net in removed_points}
    kept = []
    removed = 0
    for item in board:
        if not (isinstance(item, list) and item and item[0] == "segment"):
            kept.append(item)
            continue
        net = str(first(item, "net")[1])
        a, b = point(item, "start"), point(item, "end")
        if (a[0], a[1], net) in points or (b[0], b[1], net) in points:
            removed += 1
        else:
            kept.append(item)
    board[:] = kept
    return removed


def insert_items(board, items):
    index = next((i for i in range(len(board) - 1, 0, -1)
                  if isinstance(board[i], list) and board[i] and
                  board[i][0] == "embedded_fonts"), len(board))
    board[index:index] = items


def rebuild_bottom_local(board, side, sensor, supply_cap, output_cap):
    """Rebuild the compact shared cell after a bounded three-net rip-up."""
    if side == "Left":
        bounds = (0.0, 24.0, 76.0, 95.0)
        signal = "HE_L27"
        place(supply_cap, 14.2, 87.0)
        place(output_cap, 14.2, 83.0)
        supply_anchor = (20.542, 80.7325)
        signal_anchor = (20.528, 84.0105)
        supply_path = [supply_anchor, (22.0, 82.1905), (22.0, 88.0),
                       (14.72, 88.0)]
        power_bridge = [(14.2393, 77.4318), (15.6325, 78.825),
                        (20.542, 78.825), supply_anchor]
        ground_vias = ((10.0035, 88.0), (15.5, 87.0), (13.72, 81.7))
    else:
        bounds = (244.0, 268.0, 76.0, 95.0)
        signal = "HE_R29"
        place(supply_cap, 259.8, 87.0)
        place(output_cap, 259.8, 83.0)
        supply_anchor = (265.335, 80.7325)
        signal_anchor = (261.3289, 83.6606)
        supply_path = [supply_anchor, (266.8, 82.1975), (266.8, 88.0),
                       (260.32, 88.0)]
        power_bridge = [(244.3666, 78.825), (245.0221, 78.1695),
                        (249.3572, 78.1695)]
        power_bridge_2 = [(264.6795, 78.1695), (265.335, 78.825),
                          supply_anchor]
        ground_vias = ((254.796, 88.0), (261.1, 87.0), (259.32, 81.7))
    rip_local(board, bounds, {"+3V3A", "GND", signal})
    remove_vias_at(board, (*ground_vias, (14.2, 81.7), (259.8, 81.7)))
    sensor_pads = numbered_pads(sensor)
    supply_pads = numbered_pads(supply_cap)
    output_pads = numbered_pads(output_cap)
    p1, _, p3 = (pad_global(sensor, sensor_pads[n]) for n in ("1", "2", "3"))
    ca1, _ = (pad_global(supply_cap, supply_pads[n]) for n in ("1", "2"))
    cb1, _ = (pad_global(output_cap, output_pads[n]) for n in ("1", "2"))
    items = []
    items += polyline(power_bridge, "+3V3A")
    if side == "Right":
        items += polyline(power_bridge_2, "+3V3A")
    items += polyline(supply_path + [ca1], "+3V3A")
    items += polyline([ca1, p1], "+3V3A")
    # Keep the footprint at its library orientation.  Escape from pad 1 below
    # the capacitor before heading toward the mux, so the trace never crosses
    # the adjacent ground pad and KiCad can verify the footprint exactly.
    approach = (round(p3[0] + 0.9425, 4), round(p3[1] - 0.9425, 4))
    if side == "Left":
        under = (cb1[0], 82.2)
        items += polyline([p3, approach, (cb1[0], approach[1]), cb1], signal)
        items += polyline([cb1, under, (18.7175, 82.2), signal_anchor], signal)
    else:
        under = (cb1[0], 81.8)
        items += polyline([p3, approach, (cb1[0], approach[1]), cb1], signal)
        items += polyline([cb1, under, (261.0, 81.8), (261.0, 83.3317),
                           signal_anchor], signal)
    # Pad 2 and both capacitor ground pads connect directly to the B.Cu GND
    # pour. No local ground escape or via is necessary.
    insert_items(board, items)


def rebuild_stepped_caps_local(board, sensor, supply_cap, output_cap):
    signal = "HE_L15"
    rip_local(board, (5.0, 30.0, 38.0, 60.0), {"+3V3A", "GND", signal})
    remove_vias_at(board, ((11.0, 47.0), (18.2, 49.0),
                           (17.0, 43.6), (16.52, 43.6)))
    place(supply_cap, 17.0, 49.0)
    place(output_cap, 17.0, 45.0)
    sensor_pads = numbered_pads(sensor)
    supply_pads = numbered_pads(supply_cap)
    output_pads = numbered_pads(output_cap)
    p1, _, p3 = (pad_global(sensor, sensor_pads[n]) for n in ("1", "2", "3"))
    ca1, _ = (pad_global(supply_cap, supply_pads[n]) for n in ("1", "2"))
    cb1, _ = (pad_global(output_cap, output_pads[n]) for n in ("1", "2"))
    items = []
    # Preserve the vertical +3V3A trunk, branch through the decoupler first,
    # then enter the sensor VCC pad.
    items += polyline([(8.636, 40.725), (8.636, 59.775)], "+3V3A")
    items += polyline([(8.636, 49.0), (9.636, 50.0),
                       (ca1[0], 50.0), ca1, p1], "+3V3A")
    approach = (round(p3[0] + 0.9875, 4), round(p3[1] - 0.9875, 4))
    items += polyline([p3, approach, (cb1[0], approach[1]), cb1], signal)
    items += polyline([cb1, (cb1[0], 44.2), (19.0, 44.2),
                       (19.0, 53.8658), (26.1593, 53.8658)], signal)
    # Sensor and capacitor grounds land directly in the B.Cu GND pour.
    insert_items(board, items)


def apply_pair(board, primary_ref, alternate_ref, midpoint,
               mechanical_primary_ref, mechanical_alt_ref, removed_caps):
    by_ref = {reference(fp): fp for fp in find(board, "footprint")}
    if mechanical_primary_ref in by_ref:
        output_ref = ("CL" if primary_ref.startswith("HEL") else "CR") + \
            str(int(primary_ref[3:])) + "B"
        output = by_ref[output_ref]
        angle = float(first(output, "at")[3]) if len(first(output, "at")) > 3 else 0.0
        legacy_vias = ((10.0035, 88.0), (15.5, 87.0), (14.2, 81.7),
                       (13.72, 81.7), (254.796, 88.0), (261.1, 87.0),
                       (259.8, 81.7), (259.32, 81.7))
        has_legacy_vias = any(
            item[0] == "via" and point(item, "at") in legacy_vias
            for item in board if isinstance(item, list) and item)
        legacy_route_points = {(259.8683, 82.2)}
        has_legacy_route = any(
            item[0] == "segment" and
            (point(item, "start") in legacy_route_points or
             point(item, "end") in legacy_route_points)
            for item in board if isinstance(item, list) and item)
        if abs(angle) < 1e-6 and not has_legacy_vias and not has_legacy_route:
            return False
        rebuild_bottom_local(
            board, "Left" if primary_ref.startswith("HEL") else "Right",
            by_ref[primary_ref], by_ref[output_ref[:-1] + "A"], output)
        return True
    primary, alternate = by_ref[primary_ref], by_ref[alternate_ref]
    # Keep the alternate position's already clean three-lane fanout and its
    # capacitor pair. Rename those capacitors to the canonical primary index;
    # remove the now-redundant primary-position pair and primary pad escapes.
    prefix = "CL" if primary_ref.startswith("HEL") else "CR"
    primary_index = int(primary_ref[3:])
    primary_caps = (f"{prefix}{primary_index}A", f"{prefix}{primary_index}B")
    removed = [primary, *(by_ref[ref] for ref in primary_caps)]
    board[:] = [item for item in board if all(item is not fp for fp in removed)]
    for source_ref, target_ref in zip(removed_caps, primary_caps):
        set_reference(by_ref[source_ref], target_ref)

    mechanical_primary = make_mechanical(primary, mechanical_primary_ref)
    mechanical_alt = make_mechanical(alternate, mechanical_alt_ref)
    sensor = make_sensor(primary, midpoint)
    board[:] = [item for item in board if item is not alternate]
    insert_items(board, [mechanical_primary, mechanical_alt, sensor])
    rebuild_bottom_local(
        board, "Left" if primary_ref.startswith("HEL") else "Right", sensor,
        by_ref[removed_caps[0]], by_ref[removed_caps[1]])
    return True


def apply_stepped_caps(board):
    by_ref = {reference(fp): fp for fp in find(board, "footprint")}
    if "KML15N" in by_ref:
        output = by_ref["CL15B"]
        angle = float(first(output, "at")[3]) if len(first(output, "at")) > 3 else 0.0
        legacy_vias = ((11.0, 47.0), (18.2, 49.0),
                       (17.0, 43.6), (16.52, 43.6))
        has_legacy_vias = any(
            item[0] == "via" and point(item, "at") in legacy_vias
            for item in board if isinstance(item, list) and item)
        if abs(angle) < 1e-6 and not has_legacy_vias:
            return False
        rebuild_stepped_caps_local(board, by_ref["HEL15"], by_ref["CL15A"], output)
        return True
    primary = by_ref["HEL15"]
    midpoint = (15.716 - PITCH_QUARTER / 2.0, 47.625)
    standard = make_mechanical(primary, "KML15N")
    stepped = make_mechanical(primary, "KML15S", stepped=True)
    sensor = make_sensor(primary, midpoint)
    board[:] = [item for item in board if item is not primary]
    insert_items(board, [standard, stepped, sensor])
    rebuild_stepped_caps_local(board, sensor, by_ref["CL15A"], by_ref["CL15B"])
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pcb-dir", type=Path, default=ROOT / "pcb")
    args = parser.parse_args()
    for side in ("Left", "Right"):
        path = args.pcb_dir / f"Symm60HE-{side}.kicad_pcb"
        board = loads(path.read_text())
        changed = False
        if side == "Left":
            changed |= apply_stepped_caps(board)
        for spec in PAIRS[side]:
            changed |= apply_pair(board, *spec)
        if changed:
            path.write_text(dumps(board) + "\n")
        print(f"{path.name}: {'updated' if changed else 'already current'}")


if __name__ == "__main__":
    main()
