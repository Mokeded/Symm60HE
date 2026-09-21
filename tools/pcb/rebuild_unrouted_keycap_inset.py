#!/usr/bin/env python3
"""Rebuild the unrouted half-PCB placement around the DOE key envelope.

This is deliberately a placement-stage operation.  It removes every segment,
via and zone, replaces Edge.Cuts with the current 0.5 mm keycap-inset outline,
moves only the perimeter RGB LED/capacitor pairs inward, and
places the analogue mux/capacitor pairs in clearance-valid positions that
minimise total distance to the Hall nets they serve.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import re
import sys
import uuid

from shapely.affinity import rotate as srot, translate as stran
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from outline import (  # noqa: E402
    LEFT_PCB,
    RIGHT_PCB,
    LEFT_PCB_ENCLOSURE,
    RIGHT_PCB_ENCLOSURE,
)
from sexp import Sym, dumps, find, first, loads  # noqa: E402

DEFAULT_CANDIDATE = ROOT / "work/aperture-rgb69-two-layer-placement-candidate"
LED_EDGE_INWARD_SHIFT = 0.80
EDGE_CLEARANCE = 0.50
SEARCH_STEP = 0.50


def reference(fp):
    for prop in find(fp, "property"):
        if len(prop) > 2 and prop[1] == "Reference":
            return str(prop[2])
    return ""


def at_state(fp):
    at = first(fp, "at")
    return (float(at[1]), float(at[2]),
            float(at[3]) if len(at) > 3 else 0.0)


def set_at(fp, x, y, angle=None):
    at = first(fp, "at")
    at[1], at[2] = round(x, 4), round(y, 4)
    if angle is not None:
        if len(at) > 3:
            at[3] = round(angle, 4)
        else:
            at.append(round(angle, 4))


def local_extent(fp):
    """Conservative local pad/courtyard bounding box."""
    points = []
    for pad in find(fp, "pad"):
        at = first(pad, "at") or [None, 0, 0]
        size = first(pad, "size")
        if not size:
            continue
        x, y = float(at[1]), float(at[2])
        w, h = float(size[1]), float(size[2])
        points.extend(((x - w / 2, y - h / 2),
                       (x + w / 2, y + h / 2)))
    for line in find(fp, "fp_line"):
        layer = first(line, "layer")
        if not layer or not str(layer[1]).endswith("CrtYd"):
            continue
        for name in ("start", "end"):
            point = first(line, name)
            points.append((float(point[1]), float(point[2])))
    for rectangle in find(fp, "fp_rect"):
        layer = first(rectangle, "layer")
        if not layer or not str(layer[1]).endswith("CrtYd"):
            continue
        for name in ("start", "end"):
            point = first(rectangle, name)
            points.append((float(point[1]), float(point[2])))
    if not points:
        return box(-0.5, -0.5, 0.5, 0.5)
    xs, ys = zip(*points)
    return box(min(xs), min(ys), max(xs), max(ys))


def placed_extent(fp, x=None, y=None, angle=None):
    px, py, pa = at_state(fp)
    x, y = (px if x is None else x), (py if y is None else y)
    angle = pa if angle is None else angle
    return stran(srot(local_extent(fp), -angle, origin=(0, 0)), x, y)


def drill_obstacles(footprints, exclude_refs=None):
    exclude_refs = set(exclude_refs or ())
    shapes = []
    for fp in footprints:
        if reference(fp) in exclude_refs:
            continue
        fx, fy, fa = at_state(fp)
        radians = math.radians(-fa)
        c, s = math.cos(radians), math.sin(radians)
        for pad in find(fp, "pad"):
            drill = first(pad, "drill")
            if not drill:
                continue
            at = first(pad, "at") or [None, 0, 0]
            dx, dy = float(at[1]), float(at[2])
            x = fx + dx * c - dy * s
            y = fy + dx * s + dy * c
            values = [float(value) for value in drill[1:]
                      if isinstance(value, (str, Sym)) and
                      re.fullmatch(r"[-+0-9.]+", str(value))]
            radius = (max(values) if values else 1.0) / 2 + 0.30
            shapes.append(Point(x, y).buffer(radius, quad_segs=8))
    return shapes


def move_connector(footprints, outline, side):
    """Restore the FPC to its approved centre-edge tongue."""
    mount_prefix = "MHL" if side == "Left" else "MHR"
    connector_ref = "JL1" if side == "Left" else "JR1"
    connector_target = ((140.209, 58.0, 270.0) if side == "Left" else
                        (164.209, 58.0, 90.0))
    by_ref = {reference(fp): fp for fp in footprints}
    mount_refs = [f"{mount_prefix}{index}" for index in range(1, 5)]
    hardware_refs = set(mount_refs + [connector_ref])
    later_movers = {ref for ref in by_ref if re.fullmatch(
        r"(?:AM|CM)[LR][1-4]|RBP[LR]\d+", ref)}

    fixed = []
    for fp in footprints:
        ref = reference(fp)
        layer = first(fp, "layer")
        if ref in hardware_refs or ref in later_movers:
            continue
        if layer and str(layer[1]) == "B.Cu":
            fixed.append(placed_extent(fp).buffer(0.20, join_style=1))
    fixed.extend(drill_obstacles(footprints, hardware_refs))
    occupied = unary_union(fixed)
    usable = outline.buffer(-EDGE_CLEARANCE, join_style=1)
    x0, y0, x1, y1 = usable.bounds
    # Restore the former mirrored centre-edge positions.  outline.py provides
    # compact necked tongues sized around these complete courtyards.
    connector = by_ref[connector_ref]
    ox, oy, _ = at_state(connector)
    x, y, angle = connector_target
    shape = placed_extent(connector, x, y, angle)
    keepout = shape.buffer(EDGE_CLEARANCE, join_style=1)
    if not usable.contains(shape):
        raise RuntimeError(
            f"{side}: {connector_ref} edge tongue does not contain courtyard")
    if occupied.intersects(keepout):
        raise RuntimeError(
            f"{side}: restored {connector_ref} conflicts with fixed placement")
    set_at(connector, x, y, angle)
    return connector_ref, ox, oy, x, y, angle


def routing_corridors(footprints, side):
    """Approximate the high-value Hall/mux and mux/FFC routing lanes."""
    mux_prefix = "AML" if side == "Left" else "AMR"
    connector_ref = "JL1" if side == "Left" else "JR1"
    by_ref = {reference(fp): fp for fp in footprints}
    connector_xy = at_state(by_ref[connector_ref])[:2]
    lines = []
    for index in range(1, 5):
        mux = by_ref[f"{mux_prefix}{index}"]
        mux_xy = at_state(mux)[:2]
        lines.append(LineString((mux_xy, connector_xy)))
        lines.extend(LineString((mux_xy, peer))
                     for peer in hall_peers(mux, footprints))
    return unary_union(lines).buffer(0.65, join_style=1)


def move_standoffs(footprints, outline, side):
    """Place standoffs after the muxes, outside likely signal corridors."""
    mount_prefix = "MHL" if side == "Left" else "MHR"
    by_ref = {reference(fp): fp for fp in footprints}
    mount_refs = [f"{mount_prefix}{index}" for index in range(1, 5)]
    hardware_refs = set(mount_refs)
    fixed = []
    for fp in footprints:
        ref = reference(fp)
        layer = first(fp, "layer")
        if ref in hardware_refs:
            continue
        if layer and str(layer[1]) == "B.Cu":
            fixed.append(placed_extent(fp).buffer(0.20, join_style=1))
    fixed.extend(drill_obstacles(footprints, hardware_refs))
    occupied = unary_union(fixed)
    corridors = routing_corridors(footprints, side)
    usable = outline.buffer(-EDGE_CLEARANCE, join_style=1)
    x0, y0, x1, y1 = usable.bounds
    moves = []

    # Keep each hole in its original structural region, but prefer candidates
    # outside the direct Hall-to-mux and mux-to-FFC bundles.  Among equivalent
    # candidates, a roughly 4.5 mm centre-to-edge inset leaves useful case wall
    # material without consuming the middle of a routing bay.
    for ref in mount_refs:
        fp = by_ref[ref]
        ox, oy, _ = at_state(fp)
        candidates = []
        x = math.ceil(max(x0, ox - 30.0) / 0.25) * 0.25
        while x <= min(x1, ox + 30.0):
            y = math.ceil(max(y0, oy - 30.0) / 0.25) * 0.25
            while y <= min(y1, oy + 30.0):
                shape = placed_extent(fp, x, y, 0.0)
                keepout = shape.buffer(EDGE_CLEARANCE, join_style=1)
                if usable.contains(shape) and not occupied.intersects(keepout):
                    blocked = corridors.intersects(keepout)
                    edge_inset = outline.exterior.distance(Point(x, y))
                    score = (0.20 * math.hypot(x - ox, y - oy) +
                             abs(edge_inset - 4.5))
                    candidates.append((blocked, score, x, y, shape))
                y += 0.25
            x += 0.25
        if not candidates:
            raise RuntimeError(f"{side}: no routing-clear placement for {ref}")
        clear = [item for item in candidates if not item[0]]
        _, _, x, y, shape = min(clear or candidates,
                                key=lambda item: item[1])
        set_at(fp, x, y, 0.0)
        # The trimmed inner shoulder moves MHR2 beside SR3.  Put its reference
        # below the mounting pad so the text does not cross the stabilizer NPTH.
        if ref == "MHR2":
            reference_property = next(
                prop for prop in find(fp, "property")
                if len(prop) > 2 and prop[1] == "Reference")
            reference_at = first(reference_property, "at")
            reference_at[1], reference_at[2] = 0.0, 3.15
        occupied = unary_union((occupied,
                                shape.buffer(EDGE_CLEARANCE, join_style=1)))
        moves.append((ref, ox, oy, x, y))
    return moves


def edgecut_points(fp, x, y, angle):
    radians = math.radians(-angle)
    c, s = math.cos(radians), math.sin(radians)
    points = []
    for kind in ("fp_line", "fp_arc"):
        for item in find(fp, kind):
            layer = first(item, "layer")
            if not layer or str(layer[1]) != "Edge.Cuts":
                continue
            for name in ("start", "mid", "end"):
                point = first(item, name)
                if point:
                    dx, dy = float(point[1]), float(point[2])
                    points.append(Point(x + dx * c - dy * s,
                                        y + dx * s + dy * c))
    return points


def move_leds(footprints, side, outline):
    hall_prefix = "HEL" if side == "Left" else "HER"
    led_prefix = "DL" if side == "Left" else "DR"
    cap_prefix = "CRGBL" if side == "Left" else "CRGBR"
    halls = [fp for fp in footprints if reference(fp).startswith(hall_prefix)]
    by_ref = {reference(fp): fp for fp in footprints}
    moved = []
    for led in footprints:
        ref = reference(led)
        if not re.fullmatch(led_prefix + r"\d+", ref):
            continue
        x, y, _ = at_state(led)
        hall = min(halls, key=lambda fp: math.dist((x, y), at_state(fp)[:2]))
        hx, hy, _ = at_state(hall)
        distance = math.hypot(hx - x, hy - y)
        if distance < 1e-6:
            continue
        ux, uy = (hx - x) / distance, (hy - y) / distance
        # The outer row needs extra aperture-to-perimeter separation after the
        # board is pulled under the keycap envelope.  Any interior LED whose
        # aperture would cross a sculpted side step is moved only as far as
        # required to put the complete cutout 0.20 mm inside the perimeter.
        # Start at the current approved optical position.  Move only when the
        # actual aperture does not clear the newly generated outer perimeter;
        # this makes repeated placement passes idempotent.
        shift = 0.0
        safe = outline.buffer(-0.20, join_style=1)
        while shift <= 2.0:
            points = edgecut_points(led, x + ux * shift, y + uy * shift,
                                    at_state(led)[2])
            if points and all(safe.contains(point) for point in points):
                break
            shift += 0.10
        if shift > 2.0:
            raise RuntimeError(f"{ref}: aperture cannot clear the new perimeter")
        if shift < 0.01:
            continue
        dx, dy = shift * ux, shift * uy
        for component in (led, by_ref.get(cap_prefix + ref[len(led_prefix):])):
            if component is None:
                continue
            cx, cy, ca = at_state(component)
            set_at(component, cx + dx, cy + dy, ca)
        moved.append((ref, round(shift, 2)))
    return moved


def pad_position(fp, pad, angle=None, x=None, y=None):
    """Return a pad centre using the same y-down rotation as KiCad."""
    fx, fy, footprint_angle = at_state(fp)
    fx = fx if x is None else x
    fy = fy if y is None else y
    footprint_angle = footprint_angle if angle is None else angle
    at = first(pad, "at") or [None, 0, 0]
    radians = math.radians(-footprint_angle)
    c, s = math.cos(radians), math.sin(radians)
    dx, dy = float(at[1]), float(at[2])
    return fx + dx * c - dy * s, fy + dx * s + dy * c


def pad_net_names(fp):
    names = set()
    for pad in find(fp, "pad"):
        net = first(pad, "net")
        if net and len(net) > 1:
            names.add(str(net[1]))
    return names


def move_bypass_resistors(footprints, outline):
    """Pull alternate-layout RGB bypass links inside the smaller perimeter."""
    moving = [fp for fp in footprints if reference(fp).startswith("RBP")]
    moving_refs = {reference(fp) for fp in moving}
    usable = outline.buffer(-EDGE_CLEARANCE, join_style=1)
    fixed = [placed_extent(fp).buffer(0.20, join_style=1)
             for fp in footprints
             if reference(fp) not in moving_refs and
             first(fp, "layer") and str(first(fp, "layer")[1]) == "B.Cu"]
    fixed.extend(drill_obstacles(footprints))
    occupied = unary_union(fixed)
    x0, y0, x1, y1 = usable.bounds
    placements = []
    for resistor in moving:
        nets = pad_net_names(resistor)
        peers = [at_state(fp)[:2] for fp in footprints
                 if fp is not resistor and pad_net_names(fp) & nets]
        candidates = []
        x = math.ceil((x0 + 1.0) / SEARCH_STEP) * SEARCH_STEP
        while x <= x1 - 1.0:
            y = math.ceil((y0 + 1.0) / SEARCH_STEP) * SEARCH_STEP
            while y <= y1 - 1.0:
                shape = placed_extent(resistor, x, y, 0.0)
                if (usable.contains(shape) and
                        not occupied.intersects(shape.buffer(0.20, join_style=1))):
                    cost = sum(math.hypot(x - px, y - py) for px, py in peers)
                    candidates.append((cost, x, y, shape))
                y += SEARCH_STEP
            x += SEARCH_STEP
        if not candidates:
            raise RuntimeError(f"no placement for {reference(resistor)}")
        _, x, y, shape = min(candidates, key=lambda item: item[0])
        set_at(resistor, x, y, 0.0)
        occupied = unary_union((occupied, shape.buffer(0.20, join_style=1)))
        placements.append((reference(resistor), x, y))
    return placements


def hall_peers(mux, footprints):
    net_names = set()
    for pad in find(mux, "pad"):
        net = first(pad, "net")
        if net and len(net) > 1 and str(net[1]).startswith("HE_"):
            net_names.add(str(net[1]))
    peers = []
    for fp in footprints:
        if not reference(fp).startswith("HE"):
            continue
        if any(first(pad, "net") and len(first(pad, "net")) > 1 and
               str(first(pad, "net")[1]) in net_names
               for pad in find(fp, "pad")):
            peers.append(at_state(fp)[:2])
    return peers


def mux_signal_targets(mux, footprints):
    """Cache each analogue mux pad and its Hall-sensor destination."""
    targets = []
    for pad in find(mux, "pad"):
        net = first(pad, "net")
        if not net or len(net) < 2 or not str(net[1]).startswith("HE_"):
            continue
        net_name = str(net[1])
        peers = []
        for other in footprints:
            if other is mux or not reference(other).startswith("HE"):
                continue
            for other_pad in find(other, "pad"):
                other_net = first(other_pad, "net")
                if other_net and len(other_net) > 1 and str(other_net[1]) == net_name:
                    peers.append(pad_position(other, other_pad))
        if peers:
            targets.append((pad, min(peers, key=lambda peer:
                           math.dist(at_state(mux)[:2], peer))))
    return targets


def mux_signal_cost(mux, targets, x, y, rotation):
    """Pad-to-pad flyline length for cached analogue input destinations."""
    return sum(math.dist(pad_position(mux, pad, rotation, x, y), target)
               for pad, target in targets)


def move_muxes(footprints, outline, side):
    mux_prefix = "AML" if side == "Left" else "AMR"
    cap_prefix = "CML" if side == "Left" else "CMR"
    by_ref = {reference(fp): fp for fp in footprints}
    mux_indices = sorted(
        int(match.group(1))
        for ref in by_ref
        if (match := re.fullmatch(f"{mux_prefix}(\\d+)", ref))
    )
    moving_refs = {ref for ref in by_ref
                   if re.fullmatch(f"(?:{mux_prefix}|{cap_prefix})\\d+", ref)}
    mount_prefix = "MHL" if side == "Left" else "MHR"
    mount_refs = {f"{mount_prefix}{index}" for index in range(1, 5)}

    fixed_shapes = []
    for fp in footprints:
        ref = reference(fp)
        layer = first(fp, "layer")
        if ref in moving_refs:
            continue
        if layer and str(layer[1]) == "B.Cu":
            fixed_shapes.append(placed_extent(fp).buffer(0.15, join_style=1))
    # Standoffs are deliberately absent here.  They are placed after the muxes
    # so a legacy boss cannot consume the best signal breakout location.
    fixed_shapes.extend(drill_obstacles(footprints, mount_refs))
    occupied = unary_union(fixed_shapes)
    usable = outline.buffer(-EDGE_CLEARANCE, join_style=1)
    x0, y0, x1, y1 = usable.bounds
    connector_ref = "JL1" if side == "Left" else "JR1"
    connector_x, connector_y, _ = at_state(by_ref[connector_ref])
    placements = []

    # Start with the electrically closest-to-connector mux.  Once selected,
    # each rigid mux/cap pair becomes an obstacle for the remaining groups.
    for index in reversed(mux_indices):
        mux = by_ref[f"{mux_prefix}{index}"]
        cap = by_ref[f"{cap_prefix}{index}"]
        signal_targets = mux_signal_targets(mux, footprints)
        candidates = []
        x = math.ceil((x0 + 3.0) / SEARCH_STEP) * SEARCH_STEP
        while x <= x1 - 3.0:
            y = math.ceil((max(y0 + 3.0, 25.0)) / SEARCH_STEP) * SEARCH_STEP
            while y <= y1 - 3.0:
                # This project footprint carries placement-specific pad
                # rotations: 0/180 degrees turn the long pad axis into the
                # 1.27 mm pitch and fail DRC.  Both vertical orientations are
                # electrically and geometrically safe.
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
                            placed_extent(cap, cap_x, cap_y, 0.0)))
                        if (usable.contains(pair) and not occupied.intersects(
                                pair.buffer(0.15, join_style=1))):
                            signal_cost = mux_signal_cost(
                                mux, signal_targets, x, y, rotation)
                            bus_cost = 0.30 * math.hypot(x - connector_x,
                                                         y - connector_y)
                            penalty = 8.0 * cap_index
                            candidates.append((signal_cost + bus_cost + penalty,
                                               x, y, cap_x, cap_y, rotation,
                                               pair))
                y += SEARCH_STEP
            x += SEARCH_STEP
        if not candidates:
            raise RuntimeError(f"{side}: no clearance-valid placement for {mux_prefix}{index}")
        _, x, y, cap_x, cap_y, rotation, pair = min(
            candidates, key=lambda item: item[0])
        set_at(mux, x, y, rotation)
        set_at(cap, cap_x, cap_y, 0.0)
        occupied = unary_union((occupied, pair.buffer(0.15, join_style=1)))
        placements.append((reference(mux), x, y, rotation,
                           reference(cap), cap_x, cap_y))
    return placements


def edge_line(a, b):
    return [Sym("gr_line"),
            [Sym("start"), round(a[0], 4), round(a[1], 4)],
            [Sym("end"), round(b[0], 4), round(b[1], 4)],
            [Sym("stroke"), [Sym("width"), 0.1], [Sym("type"), Sym("solid")]],
            [Sym("layer"), "Edge.Cuts"],
            [Sym("uuid"), str(uuid.uuid4())]]


def flip_spacebar_stabilizer(footprints, side):
    """Put the large spacebar stabilizer holes toward the PCB interior."""
    ref = "SL2" if side == "Left" else "SR3"
    target = 171.0 if side == "Left" else 189.0
    footprint = next(fp for fp in footprints if reference(fp) == ref)
    x, y, old_angle = at_state(footprint)
    set_at(footprint, x, y, target)
    return ref, old_angle, target


def clear_flipped_spacebar_hardware(footprints, side):
    """Move the one filter capacitor exposed by the flipped left stabilizer."""
    if side != "Left":
        return None
    footprint = next(fp for fp in footprints if reference(fp) == "CL25B")
    ox, oy, _ = at_state(footprint)
    # This is closer to its associated HEL25 sensor than the prior placement
    # and clears the inward-facing 3.9878 mm SL2 hole plus all other B.Cu
    # courtyards and drilled-hole keepouts.
    set_at(footprint, 105.0, 76.0, 0.0)
    return "CL25B", ox, oy, 105.0, 76.0


def rebuild(path, side, outline):
    board = loads(path.read_text())
    footprints = find(board, "footprint")
    stabilizer_flip = flip_spacebar_stabilizer(footprints, side)
    stabilizer_clearance_move = clear_flipped_spacebar_hardware(
        footprints, side)
    connector = move_connector(footprints, outline, side)
    leds = move_leds(footprints, side, outline)
    # RGB centres and orientations are mechanically locked by the reviewed
    # aperture/alignment-hole placement.  Trial rotations shortened some
    # flylines but created pad-to-hole and pad-clearance DRC regressions.
    rgb_rotations = []
    bypasses = move_bypass_resistors(footprints, outline)
    muxes = move_muxes(footprints, outline, side)
    mounts = move_standoffs(footprints, outline, side)

    output = [board[0]]
    removed = {"segment": 0, "via": 0, "zone": 0, "edge": 0}
    for item in board[1:]:
        if not isinstance(item, list) or not item:
            output.append(item)
            continue
        kind = str(item[0])
        if kind in ("segment", "via", "zone"):
            removed[kind] += 1
            continue
        layer = first(item, "layer")
        if kind.startswith("gr_") and layer and str(layer[1]) == "Edge.Cuts":
            removed["edge"] += 1
            continue
        output.append(item)

    points = list(outline.exterior.coords)
    output.extend(edge_line(a, b) for a, b in zip(points, points[1:]))
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(dumps(output) + "\n")
    temporary.replace(path)
    print(f"{path.name}: removed {removed['segment']} segments, "
          f"{removed['via']} vias, {removed['zone']} zones; "
          f"replaced {removed['edge']} edges with {len(points) - 1}")
    print(f"  RGB: moved {len(leds)} perimeter LED/cap pairs: " +
          ", ".join(f"{ref} {shift:.2f} mm" for ref, shift in leds))
    print(f"  RGB routing: rotated {len(rgb_rotations)} fixed-centre LEDs: " +
          ", ".join(f"{ref} {angle:.0f} deg" for ref, angle in rgb_rotations))
    ref, old_angle, target = stabilizer_flip
    print(f"  stabilizer: {ref} {old_angle:.0f} -> {target:.0f} degrees")
    if stabilizer_clearance_move:
        ref, ox, oy, x, y = stabilizer_clearance_move
        print(f"  stabilizer clearance: {ref} {ox:.2f},{oy:.2f} -> "
              f"{x:.2f},{y:.2f}")
    for ref, ox, oy, x, y in mounts:
        print(f"  mount: {ref} {ox:.2f},{oy:.2f} -> {x:.2f},{y:.2f}")
    ref, ox, oy, x, y, angle = connector
    print(f"  FPC: {ref} {ox:.2f},{oy:.2f} -> {x:.2f},{y:.2f} rot {angle:.0f}")
    for placement in muxes:
        print("  mux: %s %.1f,%.1f rot %.0f; %s %.1f,%.1f" % placement)
    for ref, x, y in bypasses:
        print(f"  RGB bypass: {ref} {x:.1f},{y:.1f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument(
        "--outline-style", choices=("keycap", "enclosure"), default="keycap",
        help="use the active keycap-following outline or the approval-only "
             "simplified enclosure silhouette")
    args = parser.parse_args()
    outlines = ({"Left": LEFT_PCB, "Right": RIGHT_PCB}
                if args.outline_style == "keycap" else
                {"Left": LEFT_PCB_ENCLOSURE, "Right": RIGHT_PCB_ENCLOSURE})
    for side, outline in outlines.items():
        path = args.candidate / f"Symm60HE-{side}.kicad_pcb"
        if not path.is_file():
            raise SystemExit(f"missing {path}")
        rebuild(path, side, outline)


if __name__ == "__main__":
    main()
