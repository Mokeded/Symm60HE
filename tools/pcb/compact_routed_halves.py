#!/usr/bin/env python3
"""Compact the routed all-layout Hall PCBs without discarding their routing.

Every Hall sensor and switch position remains fixed.  Only the north-perimeter
reverse-mount RGB LEDs and their bypass capacitors move toward the nearest Hall
sensor.  Copper endpoints attached to those pads move with them, the mirrored
compact Edge.Cuts replace the old silhouette, and the two full-board GND zones
are regenerated against the smaller outline.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import re
import sys

from shapely.affinity import translate as stran
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.polygon import orient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from outline import LEFT_PCB_ENCLOSURE, RIGHT_PCB_ENCLOSURE  # noqa: E402
from rebuild_unrouted_keycap_inset import (  # noqa: E402
    at_state, edge_line, edgecut_points, reference, set_at,
)
from route import read  # noqa: E402
from sexp import Sym, dumps, find, first, loads  # noqa: E402


TOP_ROW_Y = 15.0
COPPER_EDGE_CLEARANCE = 0.50
APERTURE_EDGE_CLEARANCE = 0.20
SEARCH_STEP = 0.05


def pad_records(path):
    """Return the route module's exact placed pad geometry by footprint."""
    _, pads, _, _ = read(str(path))
    by_ref = {}
    for pad in pads:
        by_ref.setdefault(str(pad["ref"]), []).append(pad)
    return by_ref


def detach_and_prune_copper(board, moving_pads, deltas, outline):
    """Remove moved-pad stubs and copper that no longer fits the outline.

    The remaining route stays protected during the subsequent Freerouting
    repair pass.  Removing these small local runs is safer than elastically
    swinging them through nearby VBUS/RGB copper.
    """
    candidates = []
    moved_pad_geometries = []
    for ref, delta in deltas.items():
        for pad in moving_pads.get(ref, ()):  # exact rotated pad geometry
            candidates.append((str(pad["net"]), pad["geom"], delta, ref))
            moved_pad_geometries.append((
                str(pad["net"]),
                stran(pad["geom"], xoff=delta[0], yoff=delta[1])))

    def shift_for(net, x, y):
        point = Point(x, y)
        hits = []
        for pad_net, geometry, delta, ref in candidates:
            if pad_net != str(net) or not geometry.buffer(0.01).covers(point):
                continue
            hits.append((geometry.centroid.distance(point), delta, ref))
        return min(hits, key=lambda item: item[0]) if hits else None

    safe = outline.buffer(-0.05, join_style=1)
    removed = []
    kept = [board[0]]
    for item in board[1:]:
        if not isinstance(item, list) or not item:
            kept.append(item)
            continue
        kind = str(item[0])
        if kind == "segment":
            net = str(first(item, "net")[1])
            start, end = first(item, "start"), first(item, "end")
            a = (float(start[1]), float(start[2]))
            b = (float(end[1]), float(end[2]))
            width = float(first(item, "width")[1])
            touches = shift_for(net, *a) or shift_for(net, *b)
            geometry = LineString((a, b)).buffer(width / 2)
            fits = safe.contains(geometry)
            collides = any(
                pad_net != net and pad.buffer(0.20).intersects(geometry)
                for pad_net, pad in moved_pad_geometries)
            if touches or not fits or collides:
                removed.append((kind, net, a, b))
                continue
        elif kind == "via":
            net = str(first(item, "net")[1])
            at = first(item, "at")
            location = (float(at[1]), float(at[2]))
            size = float(first(item, "size")[1])
            touches = shift_for(net, *location)
            geometry = Point(*location).buffer(size / 2)
            fits = safe.contains(geometry)
            collides = any(
                pad_net != net and pad.buffer(0.20).intersects(geometry)
                for pad_net, pad in moved_pad_geometries)
            if touches or not fits or collides:
                removed.append((kind, net, location, location))
                continue
        kept.append(item)
    board[:] = kept
    repair_nets = sorted({net for _, net, _, _ in removed if net != "GND"})
    return removed, repair_nets


def compact_leds(board, side, pads, outline):
    footprints = find(board, "footprint")
    by_ref = {reference(fp): fp for fp in footprints}
    led_prefix = "DL" if side == "Left" else "DR"
    hall_prefix = "HEL" if side == "Left" else "HER"
    cap_prefix = "CRGBL" if side == "Left" else "CRGBR"
    halls = [fp for fp in footprints if reference(fp).startswith(hall_prefix)]
    deltas = {}
    zone_shifts = []
    report = []

    for led in footprints:
        ref = reference(led)
        if not re.fullmatch(led_prefix + r"\d+", ref):
            continue
        lx, ly, _ = at_state(led)
        if ly >= TOP_ROW_Y:
            continue
        hall = min(halls, key=lambda fp: math.dist(
            (lx, ly), at_state(fp)[:2]))
        hx, hy, _ = at_state(hall)
        distance = math.dist((lx, ly), (hx, hy))
        ux, uy = (hx - lx) / distance, (hy - ly) / distance
        copper_safe = outline.buffer(-COPPER_EDGE_CLEARANCE, join_style=1)
        aperture_safe = outline.buffer(-APERTURE_EDGE_CLEARANCE, join_style=1)
        cap_ref = cap_prefix + ref[len(led_prefix):]
        pair_refs = (ref, cap_ref) if cap_ref in by_ref else (ref,)
        shift = 0.0
        while shift <= 3.0:
            dx, dy = ux * shift, uy * shift
            copper_ok = all(
                copper_safe.covers(stran(pad["geom"], xoff=dx, yoff=dy))
                for pair_ref in pair_refs for pad in pads.get(pair_ref, ()))
            aperture = edgecut_points(led, lx + dx, ly + dy,
                                      at_state(led)[2])
            aperture_ok = (aperture and
                           all(aperture_safe.covers(point)
                               for point in aperture))
            if copper_ok and aperture_ok:
                break
            shift += SEARCH_STEP
        if shift > 3.0:
            raise RuntimeError(f"{ref}: cannot clear compact perimeter")
        if shift < SEARCH_STEP / 2:
            continue
        dx, dy = ux * shift, uy * shift
        deltas[ref] = (dx, dy)
        zone_shifts.append((ref, lx, ly, dx, dy))
        if cap_ref in by_ref:
            deltas[cap_ref] = (dx, dy)
        report.append((ref, reference(hall), distance, distance - shift,
                       dx, dy))

    removed, repair_nets = detach_and_prune_copper(
        board, pads, deltas, outline)
    for ref, (dx, dy) in deltas.items():
        footprint = by_ref[ref]
        x, y, angle = at_state(footprint)
        set_at(footprint, x + dx, y + dy, angle)
    return report, removed, repair_nets, zone_shifts


def replace_zone_outer_polygon(zone_expr, polygon, zone_shifts):
    """Resize only a GND zone's largest boundary and retain aperture holes."""
    polygons = find(zone_expr, "polygon")
    if not polygons:
        raise RuntimeError("GND zone has no polygon")

    def geometry(expr):
        pts = first(expr, "pts")
        return Polygon([(float(point[1]), float(point[2]))
                        for point in pts[1:] if str(point[0]) == "xy"])

    outer = max(polygons, key=lambda expr: abs(geometry(expr).area))
    # KiCad interprets the first zone contour as an outer boundary only when
    # it is counter-clockwise.  Shapely's mirrored right-half result can be
    # clockwise, which fills visually but leaves the zone electrically
    # disconnected in DRC.
    inset = orient(polygon.buffer(-0.30, join_style=1), sign=1.0)
    points = [[Sym("xy"), round(x, 4), round(y, 4)]
              for x, y in list(inset.exterior.coords)[:-1]]
    old_pts = first(outer, "pts")
    old_pts[:] = [Sym("pts")] + points

    # Aperture cutouts are stored as additional contours in each zone.  When
    # a reverse-mount LED moves, its matching contour must move with it;
    # otherwise the stale contour becomes an isolated copper island outside
    # the compact outline.
    holes = [expr for expr in polygons if expr is not outer]
    for ref, old_x, old_y, dx, dy in zone_shifts:
        if not holes:
            raise RuntimeError(f"{ref}: GND zone has no aperture contour")
        aperture = min(holes, key=lambda expr: math.dist(
            (geometry(expr).centroid.x, geometry(expr).centroid.y),
            (old_x, old_y)))
        centroid = geometry(aperture).centroid
        if math.dist((centroid.x, centroid.y), (old_x, old_y)) > 4.0:
            raise RuntimeError(f"{ref}: cannot identify GND-zone aperture")
        aperture_pts = first(aperture, "pts")
        for point in aperture_pts[1:]:
            if str(point[0]) == "xy":
                point[1] = round(float(point[1]) + dx, 4)
                point[2] = round(float(point[2]) + dy, 4)
        holes.remove(aperture)


def replace_outline_and_ground_zones(board, polygon, zone_shifts):
    output = [board[0]]
    removed_edges = 0
    resized_ground_zones = 0
    for item in board[1:]:
        if not isinstance(item, list) or not item:
            output.append(item)
            continue
        kind = str(item[0])
        layer = first(item, "layer")
        if (kind.startswith("gr_") and layer and
                str(layer[1]) == "Edge.Cuts"):
            removed_edges += 1
            continue
        if kind == "zone":
            net = first(item, "net")
            if net and str(net[1]) == "GND":
                replace_zone_outer_polygon(item, polygon, zone_shifts)
                resized_ground_zones += 1
        output.append(item)

    points = list(polygon.exterior.coords)
    additions = [edge_line(a, b) for a, b in zip(points, points[1:])]
    marker = next((index for index, item in enumerate(output)
                   if isinstance(item, list) and item and
                   str(item[0]) == "segment"), len(output) - 1)
    output[marker:marker] = additions
    return ([Sym("kicad_pcb")] + output[1:] if str(output[0]) != "kicad_pcb"
            else output), removed_edges, resized_ground_zones, len(points) - 1


def validate_led_clearance(path, side, polygon):
    _, pads, _, _ = read(str(path))
    prefix = "DL" if side == "Left" else "DR"
    safe = polygon.buffer(-COPPER_EDGE_CLEARANCE, join_style=1)
    failures = []
    for pad in pads:
        ref = str(pad["ref"])
        if (ref.startswith(prefix) and ref[len(prefix):].isdigit() and
                not safe.covers(pad["geom"])):
            failures.append(f"{ref}.{pad['num']}")
    if failures:
        raise RuntimeError("LED copper lacks 0.50 mm Edge.Cuts clearance: " +
                           ", ".join(failures))


def process(path, side, polygon):
    board = loads(path.read_text())
    pads = pad_records(path)
    report, removed, repair_nets, zone_shifts = compact_leds(
        board, side, pads, polygon)
    board, old_edges, resized_zones, edges = replace_outline_and_ground_zones(
        board, polygon, zone_shifts)
    temporary = path.with_suffix(path.suffix + ".compact-tmp")
    temporary.write_text(dumps(board) + "\n")
    validate_led_clearance(temporary, side, polygon)
    temporary.replace(path)
    print(f"{path.name}: {old_edges} -> {edges} compact Edge.Cuts; "
          f"resized {resized_zones} GND zones; removed {len(removed)} local "
          f"copper items")
    print("  repair nets: " + (", ".join(repair_nets) or "GND zones only"))
    for ref, hall, before, after, dx, dy in report:
        print(f"  {ref} toward {hall}: {before:.3f} -> {after:.3f} mm "
              f"(delta {dx:+.3f},{dy:+.3f})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--board-dir", type=Path,
        default=ROOT / "work/enclosure-style-hotswap-freerouting-candidate" /
                "routed-final")
    args = parser.parse_args()
    process(args.board_dir / "Symm60HE-Left.kicad_pcb", "Left",
            LEFT_PCB_ENCLOSURE)
    process(args.board_dir / "Symm60HE-Right.kicad_pcb", "Right",
            RIGHT_PCB_ENCLOSURE)


if __name__ == "__main__":
    main()
