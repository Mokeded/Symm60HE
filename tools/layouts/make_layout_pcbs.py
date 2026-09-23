#!/usr/bin/env python3
"""Generate every physically layout-specific PCB pair from the universal master.

The universal boards keep every Hall position independently observable.  These
derived boards instead remove every inactive Hall footprint (including its two
local capacitors), layout-only stabilizers, and layout-only RGB footprints.
The close bottom-row switch-alignment drills are returned to their ordinary
horizontal axis without disturbing the proven Hall-pad routing.  The nearby
Shift stabilizers are turned 180 degrees so their smaller retention holes face
the bottom-row LEDs, allowing every retained bottom-row LED to use the ordinary
+5.35 mm south-pocket key-relative offset.

The WKL bottom row has one fewer key on each half.  Its otherwise-unused RGB
chain stage is removed by merging its input/output nets and adding a short
same-layer copper bypass across the former LED site.  This keeps the remaining
addressable LEDs in one continuous chain without retaining a hidden LED.

The universal source files are read only.  Outputs are placed below
pcb/variants/layouts/<layout>/.
"""
from __future__ import annotations

import argparse
import csv
from copy import deepcopy
import math
from pathlib import Path
import shutil
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from sexp import Sym, dumps, find, first, loads  # noqa: E402


# Three independent binary choices produce eight physical permutations:
#
# * two 1.5u keys or three 1u keys on the left bottom row;
# * the ordinary right bottom row or the right arrow cluster; and
# * split (1u + 1u) or 2u Backspace.
#
# Keep the four historical names stable, then add the four mixed-half layouts
# that were previously impossible because the left and right bottom-row choices
# were coupled by the layout name.
LAYOUT_SPECS = {
    "wkl": ("wkl", "wkl", "split"),
    "wklarrows": ("three-key", "arrows", "split"),
    "wklbs2": ("wkl", "wkl", "2u"),
    "wklbs2arrows": ("three-key", "arrows", "2u"),
    "wkl-left-arrows-right": ("wkl", "arrows", "split"),
    "three-key-left-wkl-right": ("three-key", "wkl", "split"),
    "wkl-left-arrows-right-bs2": ("wkl", "arrows", "2u"),
    "three-key-left-wkl-right-bs2": ("three-key", "wkl", "2u"),
}
LAYOUTS = tuple(LAYOUT_SPECS)


def source_layout(layout, side):
    """Return the legacy switch-map key for one half of a permutation."""
    left_bottom, right_bottom, backspace = LAYOUT_SPECS[layout]
    if side == "Left":
        return "wklarrows" if left_bottom == "three-key" else "wkl"
    suffix = "arrows" if right_bottom == "arrows" else ""
    return ("wklbs2" if backspace == "2u" else "wkl") + suffix


def has_arrow_bottom(layout, side):
    left_bottom, right_bottom, _ = LAYOUT_SPECS[layout]
    return ((side == "Left" and left_bottom == "three-key") or
            (side == "Right" and right_bottom == "arrows"))

# LEDs that exist only for one of the alternative physical positions.  The
# close-pair shared LEDs are moved below and therefore do not appear here.
LAYOUT_ONLY_LEDS = {
    "Left": {
        # The arrow bottom row has a third key at HEL29.  WKL uses two wider
        # keys, so its RGB stage is bypassed rather than left hidden.
        "DL33": {"wklarrows", "wklbs2arrows"},
    },
    "Right": {
        # Top-row 1u + 1u versus 2u Backspace.
        "DR4": {"wkl", "wklarrows"},
        "DR5": {"wkl", "wklarrows"},
        "DR33": {"wklbs2", "wklbs2arrows"},
        # 2.25u Shift versus 1u Up + 1.25u Shift.
        "DR21": {"wkl", "wklbs2"},
        "DR22": {"wklarrows", "wklbs2arrows"},
        "DR34": {"wklarrows", "wklbs2arrows"},
        # The arrow bottom row has a third key at HER32.
        "DR36": {"wklarrows", "wklbs2arrows"},
    },
}

LAYOUT_ONLY_STABILIZERS = {
    "Right": {
        "SR1": {"wklbs2", "wklbs2arrows"},
        "SR2": {"wkl", "wklbs2"},
    },
}

# These stabilizers remain centred on their keys.  Only their north/south
# orientation changes: the smaller 3.048 mm retention holes face the adjacent
# bottom-row LED apertures, leaving more material and clearance than the
# 3.9878 mm holes used by the universal compromise.
FIXED_STABILIZER_ROTATIONS = {
    "Left": {
        "SL1": {layout: 180.0 for layout in LAYOUTS},
    },
    "Right": {
        "SR2": {"wkl": 180.0, "wklbs2": 180.0},
    },
}

# Reverse-mount LEDs sit in the KS-20 RGB pocket on the south side of every
# key: +5.35 mm along the key's local Y (KiCad +Y is south).
LED_DY = 5.350
BOTTOM_LED_OFFSET = LED_DY

SHARED_LED_TARGETS = {
    "Left": {
        "DL27": {"wkl": "HEL28", "wklarrows": "HEL27",
                 "wklbs2": "HEL28", "wklbs2arrows": "HEL27"},
        "DL29": {"wkl": "HEL30", "wklarrows": "HEL31",
                 "wklbs2": "HEL30", "wklbs2arrows": "HEL31"},
    },
    "Right": {
        "DR29": {"wkl": "HER31", "wklarrows": "HER30",
                 "wklbs2": "HER31", "wklbs2arrows": "HER30"},
        "DR31": {"wkl": "HER33", "wklarrows": "HER34",
                 "wklbs2": "HER33", "wklbs2arrows": "HER34"},
    },
}

# Other LEDs that were displaced on the universal right half so mutually
# exclusive key footprints could coexist.  A fixed-layout board has only one
# of those switch choices, so put its retained LED back on the ordinary row
# centreline and restore the normal horizontal package orientation.
#
# Entries are: layout -> (Hall reference, local X offset, local Y offset).
# The offsets are expressed in the key's local coordinates and rotate with the
# key, just like the shared bottom-row placements above.
FIXED_LED_TARGETS = {
    "Left": {
        # The third arrow-cluster key is layout-only rather than shared, but
        # it belongs on the same south-pocket LED line as its two neighbours.
        "DL33": {
            "wklarrows": ("HEL29", 0.0, LED_DY),
            "wklbs2arrows": ("HEL29", 0.0, LED_DY),
        },
    },
    "Right": {
        # Split Backspace LEDs were pulled toward the centre on the universal
        # PCB to coexist with the 2U option.  Fixed split-Backspace boards can
        # centre each LED directly above its own Hall sensor.
        "DR4": {
            "wkl": ("HER3", 0.0, LED_DY),
            "wklarrows": ("HER3", 0.0, LED_DY),
        },
        "DR5": {
            "wkl": ("HER5", 0.0, LED_DY),
            "wklarrows": ("HER5", 0.0, LED_DY),
        },
        # The universal 2U Backspace LED is vertical and tucked between the
        # competing 1U alignment holes.  On either 2U-only derivative it can
        # sit horizontally on the same Y line as the other number-row LEDs.
        "DR33": {
            "wklbs2": ("HER4", 0.0, LED_DY),
            "wklbs2arrows": ("HER4", 0.0, LED_DY),
        },
        # Universal Shift alternatives are shifted sideways to preserve all
        # three mutually exclusive apertures.  Fixed variants centre the
        # selected LEDs under their own switches on the ordinary row line.
        "DR21": {
            "wkl": ("HER25", 0.0, LED_DY),
            "wklbs2": ("HER25", 0.0, LED_DY),
        },
        "DR22": {
            "wklarrows": ("HER24", 0.0, LED_DY),
            "wklbs2arrows": ("HER24", 0.0, LED_DY),
        },
        "DR34": {
            "wklarrows": ("HER26", 0.0, LED_DY),
            "wklbs2arrows": ("HER26", 0.0, LED_DY),
        },
        # As on the left, the centre arrow key uses the same normal offset as
        # the two shared bottom-row LED stages.
        "DR36": {
            "wklarrows": ("HER32", 0.0, LED_DY),
            "wklbs2arrows": ("HER32", 0.0, LED_DY),
        },
    },
}

# Removing these LEDs shortens the serial RGB chain by one stage.
BYPASS_LEDS = {"Left": {"DL33"}, "Right": {"DR36"}}

# The universal right half uses one routed NPTH slot for each pair of
# intersecting alignment holes.  Fixed-layout derivatives restore the normal
# two 1.75 mm circular holes on whichever mutually exclusive sensor remains.
SLOTTED_UNIVERSAL_SENSORS = {
    "Left": set(),
    "Right": {"HER3", "HER4", "HER5", "HER24", "HER25", "HER26"},
}


def reference(fp):
    for prop in find(fp, "property"):
        if len(prop) > 2 and str(prop[1]) == "Reference":
            return str(prop[2])
    return None


def fnum(value):
    return float(value)


def at_state(fp):
    at = first(fp, "at")
    return (fnum(at[1]), fnum(at[2]), fnum(at[3]) if len(at) > 3 else 0.0)


def aperture_center(fp):
    """Return the board-space centre of a footprint's Edge.Cuts opening."""
    x, y, rotation = at_state(fp)
    points = []
    for kind in ("fp_line", "fp_arc"):
        for item in find(fp, kind):
            layer = first(item, "layer")
            if not layer or str(layer[1]) != "Edge.Cuts":
                continue
            for name in ("start", "mid", "end"):
                point = first(item, name)
                if not point:
                    continue
                px, py = fnum(point[1]), fnum(point[2])
                angle = math.radians(-rotation)
                points.append((x + px * math.cos(angle) - py * math.sin(angle),
                               y + px * math.sin(angle) + py * math.cos(angle)))
    if not points:
        raise RuntimeError(f"{reference(fp)} has no Edge.Cuts aperture")
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)


def set_at(fp, x, y, rotation):
    at = first(fp, "at")
    at[1:3] = [Sym(f"{x:.6f}"), Sym(f"{y:.6f}")]
    if abs(rotation) < 1e-9:
        del at[3:]
    elif len(at) > 3:
        at[3] = Sym(f"{rotation:.6f}")
    else:
        at.append(Sym(f"{rotation:.6f}"))


def pad_position(fp, pad, state=None):
    x, y, rotation = state or at_state(fp)
    pat = first(pad, "at")
    px, py = fnum(pat[1]), fnum(pat[2])
    angle = math.radians(-rotation)
    return (x + px * math.cos(angle) - py * math.sin(angle),
            y + px * math.sin(angle) + py * math.cos(angle))


def pad_net(pad):
    net = first(pad, "net")
    return str(net[1]) if net and len(net) > 1 else None


def pad_layers(fp, pad):
    layers = first(pad, "layers")
    if layers:
        result = set()
        for value in layers[1:]:
            value = str(value)
            if value == "*.Cu":
                result.update(("F.Cu", "B.Cu"))
            elif value.endswith(".Cu"):
                result.add(value)
        if result:
            return result
    layer = str(first(fp, "layer")[1])
    return {layer} if layer.endswith(".Cu") else {"F.Cu", "B.Cu"}


def copper_items(board):
    return [item for item in board[1:] if isinstance(item, list) and item and
            str(item[0]) in ("segment", "via")]


def point_close(a, b, tolerance=0.002):
    return math.dist(a, b) <= tolerance


def point_on_segment(point, a, b, tolerance=0.002):
    px, py = point
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    if length2 < 1e-12:
        return point_close(point, a, tolerance)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    nearest = (ax + t * dx, ay + t * dy)
    return point_close(point, nearest, tolerance)


def stretch_footprint_connections(board, fp, old_state, new_state):
    """Move copper endpoints that land exactly on an electrical pad."""
    moves = []
    for pad in find(fp, "pad"):
        net = pad_net(pad)
        if not net:
            continue
        old = pad_position(fp, pad, old_state)
        new = pad_position(fp, pad, new_state)
        if not point_close(old, new, 1e-6):
            moves.append((net, pad_layers(fp, pad), old, new))

    for item in copper_items(board):
        net_item = first(item, "net")
        if not net_item:
            continue
        net = str(net_item[1])
        layer_item = first(item, "layer")
        layers = {str(layer_item[1])} if layer_item else {"F.Cu", "B.Cu"}
        for move_net, move_layers, old, new in moves:
            if net != move_net or not layers.intersection(move_layers):
                continue
            if str(item[0]) == "segment":
                for key in ("start", "end"):
                    endpoint = first(item, key)
                    if point_close((fnum(endpoint[1]), fnum(endpoint[2])), old):
                        endpoint[1:3] = [Sym(f"{new[0]:.6f}"),
                                         Sym(f"{new[1]:.6f}")]
            else:
                pos = first(item, "at")
                if point_close((fnum(pos[1]), fnum(pos[2])), old):
                    pos[1:3] = [Sym(f"{new[0]:.6f}"), Sym(f"{new[1]:.6f}")]


def move_footprint(board, fp, x, y, rotation, stretch=True):
    old = at_state(fp)
    new = (x, y, rotation)
    if stretch:
        stretch_footprint_connections(board, fp, old, new)
    set_at(fp, *new)


PLACEMENT_CLEARANCE = 0.25


def pad_boxes(fp, state=None):
    """Axis-aligned board-space box per pad, and one for the LED aperture."""
    state = state or at_state(fp)
    x, y, rotation = state
    angle = math.radians(-rotation)
    boxes = []
    for pad in find(fp, "pad"):
        px, py = pad_position(fp, pad, state)
        size = first(pad, "size")
        half_x = fnum(size[1]) / 2 if size else 0.3
        half_y = fnum(size[2]) / 2 if size else 0.3
        if abs(math.sin(angle)) > 0.5:          # 90/270 degrees: axes swap
            half_x, half_y = half_y, half_x
        drill = first(pad, "drill")
        if drill and len(drill) > 1 and not isinstance(drill[1], list):
            try:
                radius = fnum(drill[1]) / 2
                half_x, half_y = max(half_x, radius), max(half_y, radius)
            except (TypeError, ValueError):
                pass
        boxes.append((px - half_x, py - half_y, px + half_x, py + half_y))
    aperture = []
    for kind in ("fp_line", "fp_arc"):
        for item in find(fp, kind):
            layer = first(item, "layer")
            if not layer or str(layer[1]) != "Edge.Cuts":
                continue
            for name in ("start", "mid", "end"):
                point = first(item, name)
                if not point:
                    continue
                lx, ly = fnum(point[1]), fnum(point[2])
                aperture.append(
                    (x + lx * math.cos(angle) - ly * math.sin(angle),
                     y + lx * math.sin(angle) + ly * math.cos(angle)))
    if aperture:
        boxes.append((min(p[0] for p in aperture), min(p[1] for p in aperture),
                      max(p[0] for p in aperture), max(p[1] for p in aperture)))
    return boxes


def placement_fits(board, fp, state, margin=PLACEMENT_CLEARANCE):
    """True when fp at `state` clears every other footprint's pads and holes.

    The universal board offsets a few LEDs sideways to share a pocket with a
    mutually exclusive position.  A derivative that drops the competitor can
    usually return the LED to the ordinary south-pocket offset -- but not when
    its own decoupling capacitor or a neighbouring drill occupies that space,
    so the move is checked pad by pad before it is made rather than assumed.
    """
    mine = pad_boxes(fp, state)
    if not mine:
        return True
    for other in find(board, "footprint"):
        if other is fp:
            continue
        for box in pad_boxes(other):
            for own in mine:
                if (own[0] - margin < box[2] and box[0] - margin < own[2] and
                        own[1] - margin < box[3] and box[1] - margin < own[3]):
                    return False
    return True


def key_relative_position(sensor, dx, dy, rotation):
    """Return a local key-relative offset in board coordinates."""
    sx, sy, _ = at_state(sensor)
    angle = math.radians(-rotation)
    return (sx + dx * math.cos(angle) - dy * math.sin(angle),
            sy + dx * math.sin(angle) + dy * math.cos(angle))


def append_item(board, item):
    index = next((i for i in range(len(board) - 1, 0, -1)
                  if isinstance(board[i], list) and board[i] and
                  str(board[i][0]) == "embedded_fonts"), len(board))
    board.insert(index, item)


def make_segment(a, b, net, layer="B.Cu", width=0.20):
    return [Sym("segment"),
            [Sym("start"), Sym(f"{a[0]:.6f}"), Sym(f"{a[1]:.6f}")],
            [Sym("end"), Sym(f"{b[0]:.6f}"), Sym(f"{b[1]:.6f}")],
            [Sym("width"), Sym(f"{width:.3f}")],
            [Sym("layer"), layer],
            [Sym("net"), net],
            [Sym("uuid"), str(uuid.uuid4())]]


def make_via(point, net, size=0.60, drill=0.30):
    return [Sym("via"),
            [Sym("at"), Sym(f"{point[0]:.6f}"), Sym(f"{point[1]:.6f}")],
            [Sym("size"), Sym(f"{size:.3f}")],
            [Sym("drill"), Sym(f"{drill:.3f}")],
            [Sym("layers"), "F.Cu", "B.Cu"],
            [Sym("net"), net],
            [Sym("uuid"), str(uuid.uuid4())]]


def remove_segment(board, net, layer, a, b, required=True):
    matches = []
    for item in copper_items(board):
        if str(item[0]) != "segment":
            continue
        item_net, item_layer = first(item, "net"), first(item, "layer")
        if (not item_net or str(item_net[1]) != net or not item_layer
                or str(item_layer[1]) != layer):
            continue
        start, end = first(item, "start"), first(item, "end")
        start = (fnum(start[1]), fnum(start[2]))
        end = (fnum(end[1]), fnum(end[2]))
        if ((point_close(start, a) and point_close(end, b)) or
                (point_close(start, b) and point_close(end, a))):
            matches.append(item)
    if not matches and not required:
        return False
    if len(matches) != 1:
        raise RuntimeError(f"expected one {net} segment {a}->{b}, got {len(matches)}")
    board.remove(matches[0])
    return True


def replace_net(node, old, new):
    if not isinstance(node, list):
        return
    if node and str(node[0]) in ("net", "net_name"):
        for i in range(1, len(node)):
            if str(node[i]) == old:
                node[i] = new
    for child in node:
        replace_net(child, old, new)


def remove_footprints(board, refs):
    removed = []
    keep = [board[0]]
    for item in board[1:]:
        if isinstance(item, list) and item and str(item[0]) == "footprint":
            ref = reference(item)
            if ref in refs:
                removed.append(item)
                continue
        keep.append(item)
    board[:] = keep
    missing = refs - {reference(fp) for fp in removed}
    if missing:
        raise RuntimeError("missing footprints: " + ", ".join(sorted(missing)))
    return removed


def remove_obsolete_zone_aperture_holes(board, active_centers, tolerance=0.08):
    """Remove zone-outline holes that do not match a retained LED aperture.

    The universal planes were created from KiCad's complete board polygon, so
    each LED aperture exists twice in every zone: as footprint Edge.Cuts and
    as a hole polygon cloned into the zone outline.  Later LED moves left a
    few historical holes that no longer match even the current universal
    footprint positions.  Retain only small hole polygons whose centre still
    matches an active LED's actual Edge.Cuts centre; leave the large outer
    board polygon untouched.
    """
    removed = 0
    for zone in find(board, "zone"):
        keep = []
        for item in zone:
            if not (isinstance(item, list) and item and
                    str(item[0]) == "polygon"):
                keep.append(item)
                continue
            pts = first(item, "pts")
            xy = find(pts, "xy") if pts else []
            if not xy:
                keep.append(item)
                continue
            xs = [fnum(value[1]) for value in xy]
            ys = [fnum(value[2]) for value in xy]
            center = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
            width = max(xs) - min(xs)
            height = max(ys) - min(ys)
            is_small_hole = width < 10.0 and height < 10.0
            matches_active = any(point_close(center, target, tolerance)
                                 for target in active_centers)
            if is_small_hole and not matches_active:
                removed += 1
                continue
            keep.append(item)
        zone[:] = keep
    return removed


def remaining_pad_records(board):
    records = []
    for fp in find(board, "footprint"):
        for pad in find(fp, "pad"):
            net = pad_net(pad)
            if net:
                records.append((net, pad_layers(fp, pad), pad_position(fp, pad)))
    return records


def prune_dangling_copper(board):
    """Iteratively remove track/via leaves no longer reaching a real pad."""
    removed = 0
    while True:
        pads = remaining_pad_records(board)
        items = copper_items(board)
        # Most KiCad joints are exact segment endpoints.  Index those first so
        # the common case is linear; only a possible T joint needs a geometric
        # scan of the same net and layer.
        joints = {}
        segments_by_net_layer = {}
        for item in items:
            net_item = first(item, "net")
            if not net_item:
                continue
            net = str(net_item[1])
            layer_item = first(item, "layer")
            layers = ({str(layer_item[1])} if layer_item else
                      {"F.Cu", "B.Cu"})
            item_points = []
            if str(item[0]) == "segment":
                for key in ("start", "end"):
                    p = first(item, key)
                    item_points.append((fnum(p[1]), fnum(p[2])))
                for layer in layers:
                    segments_by_net_layer.setdefault((net, layer), []).append(item)
            else:
                p = first(item, "at")
                item_points.append((fnum(p[1]), fnum(p[2])))
            for point in item_points:
                rounded = (round(point[0], 3), round(point[1], 3))
                for layer in layers:
                    key = (net, layer, rounded)
                    joints[key] = joints.get(key, 0) + 1

        pad_points = set()
        for net, layers, point in pads:
            rounded = (round(point[0], 3), round(point[1], 3))
            for layer in layers:
                pad_points.add((net, layer, rounded))

        doomed = []
        for item in items:
            net_item = first(item, "net")
            if not net_item:
                continue
            net = str(net_item[1])
            layer_item = first(item, "layer")
            layers = {str(layer_item[1])} if layer_item else {"F.Cu", "B.Cu"}
            points = []
            if str(item[0]) == "segment":
                for key in ("start", "end"):
                    p = first(item, key)
                    points.append((fnum(p[1]), fnum(p[2])))
            else:
                p = first(item, "at")
                points.append((fnum(p[1]), fnum(p[2])))

            connected = []
            for point in points:
                rounded = (round(point[0], 3), round(point[1], 3))
                hit = any((net, layer, rounded) in pad_points or
                          joints.get((net, layer, rounded), 0) > 1
                          for layer in layers)
                if not hit:
                    for layer in layers:
                        for other in segments_by_net_layer.get((net, layer), []):
                            if other is item:
                                continue
                            sa, sb = first(other, "start"), first(other, "end")
                            if point_on_segment(point,
                                                (fnum(sa[1]), fnum(sa[2])),
                                                (fnum(sb[1]), fnum(sb[2]))):
                                hit = True
                                break
                        if hit:
                            break
                connected.append(hit)
            if not all(connected):
                doomed.append(item)
        if not doomed:
            return removed
        for item in doomed:
            board.remove(item)
        removed += len(doomed)


def switch_rows():
    with (ROOT / "Symm60HE-switch-map.csv").open(newline="") as handle:
        return list(csv.DictReader(handle))


def selected_switches(layout, side):
    letter = side[0]
    build = source_layout(layout, side)
    return [row for row in switch_rows()
            if row["half"] == letter and build in row["in_builds"].split()]


def restore_alignment_holes(fp):
    """Return the close-pair switch-alignment holes to the normal X axis.

    The Hall package and its electrical pads stay exactly where the proven
    universal route expects them.  Only the two unplated switch-alignment
    drills are layout mechanics, so rotating those drills avoids needlessly
    disturbing sensor copper.
    """
    # A universal NPTH slot may live partly in this footprint or in the
    # mutually exclusive neighbour.  Reconstruct both fixed-layout holes
    # rather than trying to reshape whichever universal pad happened to own
    # the shared slot.
    fp[:] = [item for item in fp
             if not (isinstance(item, list) and len(item) > 3 and
                     str(item[0]) == "pad" and
                     str(item[2]) == "np_thru_hole")]
    insert_at = next((index for index, item in enumerate(fp)
                      if isinstance(item, list) and item and
                      str(item[0]) == "pad"), len(fp))
    holes = []
    for x in (-5.08, 5.08):
        holes.append([
            Sym("pad"), "", Sym("np_thru_hole"), Sym("circle"),
            [Sym("at"), Sym(f"{x:.3f}"), Sym("0")],
            [Sym("size"), Sym("1.75"), Sym("1.75")],
            [Sym("drill"), Sym("1.75")],
            [Sym("layers"), "*.Cu"],
            [Sym("uuid"), str(uuid.uuid4())],
        ])
    fp[insert_at:insert_at] = holes


def inactive_sensor_refs(layout, side):
    letter = side[0]
    build = source_layout(layout, side)
    result = set()
    for row in switch_rows():
        if row["half"] != letter or build in row["in_builds"].split():
            continue
        index = row["ref"][3:]
        result.add(f"HE{letter}{index}")
        result.add(f"C{letter}{index}A")
        result.add(f"C{letter}{index}B")
    return result


def capacitor_for_led(ref):
    return "CRGB" + ref[1:]


def bypass_led(board, fp):
    pads = {str(pad[1]): pad for pad in find(fp, "pad")}
    input_net = pad_net(pads["2"])
    output_net = pad_net(pads["4"])
    start = pad_position(fp, pads["2"])
    end = pad_position(fp, pads["4"])
    replace_net(board, output_net, input_net)
    append_item(board, make_segment(start, end, input_net))
    return input_net, output_net


def transform(path, side, layout):
    board = loads(path.read_text())
    build = source_layout(layout, side)
    by_ref = {reference(fp): fp for fp in find(board, "footprint")}
    universal_led_positions = {
        ref: aperture_center(fp) for ref, fp in by_ref.items()
        if ref and ref.startswith("D" + side[0])
    }
    active_rows = selected_switches(layout, side)
    row_by_sensor = {"HE" + side[0] + row["ref"][3:]: row
                     for row in active_rows}

    # Restore the close-pair alignment drills without moving the already
    # routed Hall package pads.
    close_sensors = ({target for targets in SHARED_LED_TARGETS[side].values()
                      for target in targets.values()} |
                     SLOTTED_UNIVERSAL_SENSORS[side])
    for sensor_ref in sorted(close_sensors.intersection(row_by_sensor)):
        restore_alignment_holes(by_ref[sensor_ref])

    # Put the two close-pair LEDs at the ordinary south-pocket offset under
    # the key that this layout actually populates.
    for led_ref, targets in SHARED_LED_TARGETS[side].items():
        sensor_ref = targets[build]
        sensor = by_ref[sensor_ref]
        sx, sy, _ = at_state(sensor)
        # The Hall package may be electrically rotated 180 degrees to keep its
        # pads routable.  LED placement follows the key angle from the switch
        # map, not that package-only rotation.
        rotation = float(row_by_sensor[sensor_ref]["rotation_deg"])
        # Local key offset (0, +LED_DY), rotated with the key: the south pocket.
        x, y = key_relative_position(sensor, 0.0, LED_DY, rotation)
        # Preserve the old routed endpoints as same-net anchors.  Stretching a
        # long final segment across the switch field creates shorts; the local
        # repair pass instead joins each moved pad to those anchors around the
        # now-layout-specific obstacles.
        move_footprint(board, by_ref[led_ref], x, y, rotation, stretch=False)

    # Return the remaining universal-compromise LEDs to their ordinary fixed
    # layout positions.  This also turns the 2U Backspace LED horizontal.
    kept_universal_leds = []
    for led_ref, targets in FIXED_LED_TARGETS.get(side, {}).items():
        target = targets.get(build)
        if not target:
            continue
        sensor_ref, dx, dy = target
        sensor = by_ref[sensor_ref]
        rotation = float(row_by_sensor[sensor_ref]["rotation_deg"])
        x, y = key_relative_position(sensor, dx, dy, rotation)
        led = by_ref[led_ref]
        if placement_fits(board, led, (x, y, rotation)):
            move_footprint(board, led, x, y, rotation, stretch=False)
        else:
            kept_universal_leds.append(led_ref)

    # Rotate only stabilizers that exist in this derivative.  The switch and
    # stabilizer centres do not move, so keycap alignment is unchanged.
    # These stabilizers were turned so their smaller retention holes faced the
    # LED apertures back when those sat north of the key.  The apertures are in
    # the switches' south pockets now, so the turn usually buys nothing -- and
    # it costs something, because the master routed around the holes where they
    # are.  Turn one only when leaving it alone would actually clash.
    kept_stabilizer_angles = []
    for stab_ref, targets in FIXED_STABILIZER_ROTATIONS.get(side, {}).items():
        if stab_ref not in by_ref or build not in targets:
            continue
        stabilizer = by_ref[stab_ref]
        x, y, angle = at_state(stabilizer)
        if placement_fits(board, stabilizer, (x, y, angle)):
            kept_stabilizer_angles.append(stab_ref)
            continue
        set_at(stabilizer, x, y, targets[build])

    # Keep RBPL29 at the universal board's position; the fixed-layout DL29
    # pocket position no longer overlaps it.

    # The south-pocket LED positions no longer collide with the zero-ohm RGB
    # links or need a hand-built RGB_L_26 trunk repair; the finish pass routes
    # every remaining open pair generically.

    inactive_leds = {ref for ref, layouts in LAYOUT_ONLY_LEDS[side].items()
                     if build not in layouts}
    active_led_refs = {
        ref for ref in universal_led_positions if ref not in inactive_leds
    }
    active_aperture_centers = [
        aperture_center(by_ref[ref]) for ref in sorted(active_led_refs)
    ]
    removed_zone_holes = remove_obsolete_zone_aperture_holes(
        board, active_aperture_centers)
    bypassed = []
    for ref in sorted(inactive_leds.intersection(BYPASS_LEDS[side])):
        bypassed.append((ref, *bypass_led(board, by_ref[ref])))

    remove_refs = inactive_sensor_refs(layout, side)
    inactive_halls = {ref for ref in remove_refs if ref.startswith("HE")}
    inactive_nets = set()
    for ref in inactive_halls:
        for pad in find(by_ref[ref], "pad"):
            if str(pad[1]) == "3" and pad_net(pad):
                inactive_nets.add(pad_net(pad))
    remove_refs.update(inactive_leds)
    remove_refs.update(capacitor_for_led(ref) for ref in inactive_leds)
    for ref, layouts in LAYOUT_ONLY_STABILIZERS.get(side, {}).items():
        if build not in layouts:
            remove_refs.add(ref)
    remove_footprints(board, remove_refs)
    # A layout-specific PCB has no reason to retain a routed analog branch for
    # a sensor that is physically absent.  Removing the entire point-to-point
    # Hall net also avoids a long chain of artificial dangling-track reports.
    board[:] = [board[0]] + [
        item for item in board[1:]
        if not (isinstance(item, list) and item and
                str(item[0]) in ("segment", "via") and
                first(item, "net") is not None and
                str(first(item, "net")[1]) in inactive_nets)
    ]
    # Do not guess which same-net stubs are zone-fed: KiCad accepts pad-entry
    # points anywhere inside a pad, not only at its centre.  Exact dangling
    # items are removed later from KiCad's own DRC report.
    pruned = 0
    path.write_text(dumps(board) + "\n")
    return {
        "active_keys": len(active_rows),
        "removed_footprints": len(remove_refs),
        "removed_leds": sorted(inactive_leds),
        "removed_zone_holes": removed_zone_holes,
        "bypassed": bypassed,
        "pruned_copper": pruned,
        "kept_universal_leds": kept_universal_leds,
        "kept_stabilizer_angles": kept_stabilizer_angles,
    }


def write_readme(directory, layout, reports):
    left, right = reports["Left"], reports["Right"]
    left_bottom, right_bottom, backspace = LAYOUT_SPECS[layout]
    text = f"""# Symm60HE {layout} layout-specific PCB pair

Generated from the universal routed master by `tools/layouts/make_layout_pcbs.py`.
The universal source boards are not modified.

- Left active Hall positions: {left['active_keys']}
- Right active Hall positions: {right['active_keys']}
- Left bottom row: {left_bottom}
- Right bottom row: {right_bottom}
- Backspace: {backspace}
- Removed left RGB footprints: {', '.join(left['removed_leds']) or 'none'}
- Removed right RGB footprints: {', '.join(right['removed_leds']) or 'none'}
- Board thickness remains 1.2 mm.
- The close bottom-row switch-alignment holes use their normal horizontal axis.
- Their LEDs use the standard +5.35 mm south-pocket key-relative offset.
- The adjacent Shift stabilizer is turned so its smaller retention holes face
  those LED apertures; its key centre is unchanged.
- Mutually exclusive universal-layout LED apertures are removed with their
  unused RGB footprints.
- The retained Backspace and Shift-choice LEDs return to their ordinary row
  alignment; the 2U Backspace LED is horizontal.
- All four isolated M2 mounting holes retain the universal board coordinates,
  exactly matching every plate variant and clearing all switch/stabilizer cuts.

The daughterboard is common to all eight pairs and remains in `pcb/`.
After generation, finish one representative of each of the six unique halves,
run `tools/layouts/materialize_layout_permutations.py`, and then run
`tools/layouts/verify_layout_pcbs.py`. The checked-in DRC reports have zero routing or
connectivity errors and zero copper-edge warnings.
"""
    (directory / "README.md").write_text(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=ROOT / "pcb/variants/layouts")
    parser.add_argument("--layout", choices=LAYOUTS, action="append")
    args = parser.parse_args()
    layouts = args.layout or list(LAYOUTS)

    for layout in layouts:
        directory = args.output / layout
        directory.mkdir(parents=True, exist_ok=True)
        reports = {}
        for side in ("Left", "Right"):
            source = ROOT / "pcb" / f"Symm60HE-{side}.kicad_pcb"
            target = directory / f"Symm60HE-{layout}-{side}.kicad_pcb"
            shutil.copy2(source, target)
            project_source = ROOT / "pcb" / f"Symm60HE-{side}.kicad_pro"
            shutil.copy2(project_source,
                         directory / f"Symm60HE-{layout}-{side}.kicad_pro")
            reports[side] = transform(target, side, layout)
            report = reports[side]
            print(f"{layout} {side}: {report['active_keys']} active keys; "
                  f"{report['removed_footprints']} footprints removed; "
                  f"{report['removed_zone_holes']} obsolete zone holes removed; "
                  f"{report['pruned_copper']} copper leaves pruned"
                  + (f"; kept universal LED position for "
                     f"{', '.join(report['kept_universal_leds'])}"
                     if report['kept_universal_leds'] else "")
                  + (f"; left {', '.join(report['kept_stabilizer_angles'])} "
                     f"unturned"
                     if report['kept_stabilizer_angles'] else ""))
        # KIPRJMOD is the individual layout directory here, four levels below
        # the repository root.  Copying pcb/fp-lib-table verbatim leaves the
        # project library unresolved when a generated variant is opened.
        fp_table = (ROOT / "pcb/fp-lib-table").read_text()
        fp_table = fp_table.replace(
            "${KIPRJMOD}/../Symm60HE_Project.pretty",
            "${KIPRJMOD}/../../../../Symm60HE_Project.pretty")
        (directory / "fp-lib-table").write_text(fp_table)
        write_readme(directory, layout, reports)


if __name__ == "__main__":
    main()
