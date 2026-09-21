#!/usr/bin/env python3
"""Audit all eight layout-specific PCB pairs against the switch map."""
from __future__ import annotations

import csv
import math
from pathlib import Path
import re
import sys

from shapely.geometry import Point, Polygon

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from make_layout_pcbs import (BOTTOM_LED_OFFSET, FIXED_LED_TARGETS,
                              FIXED_STABILIZER_ROTATIONS, LAYOUTS,
                              LAYOUT_ONLY_LEDS, LAYOUT_ONLY_STABILIZERS,
                              SHARED_LED_TARGETS, has_arrow_bottom,
                              key_relative_position, source_layout)
from pcb.relocate_half_mounts import MOUNTS
from sexp import find, first, loads


def reference(fp):
    for prop in find(fp, "property"):
        if len(prop) > 2 and str(prop[1]) == "Reference":
            return str(prop[2])
    return None


def at(fp):
    value = first(fp, "at")
    return (float(value[1]), float(value[2]),
            float(value[3]) if len(value) > 3 else 0.0)


def aperture_center(fp):
    """Return the board-space centre of the LED's milled opening."""
    x, y, rotation = at(fp)
    angle = math.radians(-rotation)
    points = []
    for kind in ("fp_line", "fp_arc"):
        for item in find(fp, kind):
            layer = first(item, "layer")
            if not layer or str(layer[1]) != "Edge.Cuts":
                continue
            for name in ("start", "mid", "end"):
                value = first(item, name)
                if not value:
                    continue
                px, py = float(value[1]), float(value[2])
                points.append((x + px * math.cos(angle) - py * math.sin(angle),
                               y + px * math.sin(angle) + py * math.cos(angle)))
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)


def polygon_geometry(node):
    points = find(first(node, "pts"), "xy") if first(node, "pts") else []
    if len(points) < 3:
        return None
    geometry = Polygon([(float(point[1]), float(point[2])) for point in points])
    return geometry if geometry.is_valid and not geometry.is_empty else None


with (ROOT / "Symm60HE-switch-map.csv").open(newline="") as handle:
    SWITCHES = list(csv.DictReader(handle))


def active_rows(layout, side):
    build = source_layout(layout, side)
    return [row for row in SWITCHES if row["half"] == side[0] and
            build in row["in_builds"].split()]


def main():
    failed = 0
    for layout in LAYOUTS:
        for side in ("Left", "Right"):
            build = source_layout(layout, side)
            path = (ROOT / "pcb/variants/layouts" / layout /
                    f"Symm60HE-{layout}-{side}.kicad_pcb")
            board = loads(path.read_text())
            fps = find(board, "footprint")
            by_ref = {reference(fp): fp for fp in fps}
            active = active_rows(layout, side)
            expected_halls = {"HE" + side[0] + row["ref"][3:]
                              for row in active}
            actual_halls = {ref for ref in by_ref
                            if ref and ref.startswith("HE" + side[0])}
            leds = {ref for ref in by_ref
                    if ref and ref.startswith("D" + side[0])}

            problems = []
            if actual_halls != expected_halls:
                problems.append("Hall footprint set mismatch")
            if len(leds) != len(active):
                problems.append(f"{len(leds)} LEDs for {len(active)} keys")
            general = first(board, "general")
            thickness = first(general, "thickness")
            if not thickness or abs(float(thickness[1]) - 1.2) > 1e-6:
                problems.append("board thickness is not 1.2 mm")

            for ref, layouts in LAYOUT_ONLY_LEDS[side].items():
                if (build in layouts) != (ref in by_ref):
                    problems.append(f"layout LED selection wrong for {ref}")
            for ref, layouts in LAYOUT_ONLY_STABILIZERS.get(side, {}).items():
                if (build in layouts) != (ref in by_ref):
                    problems.append(f"stabilizer selection wrong for {ref}")
            for mount_ref, target in MOUNTS[side].items():
                mount = by_ref.get(mount_ref)
                if mount is None:
                    problems.append(f"missing common mount {mount_ref}")
                    continue
                mx, my, _ = at(mount)
                if math.dist((mx, my), target) > 0.002:
                    problems.append(f"{mount_ref} does not match plate pattern")
                pads = find(mount, "pad")
                if (len(pads) != 1 or str(pads[0][2]) != "np_thru_hole" or
                        abs(float(first(pads[0], "drill")[1]) - 2.2) > 1e-6):
                    problems.append(f"{mount_ref} is not an isolated 2.2 mm NPTH")

            for led_ref, targets in SHARED_LED_TARGETS[side].items():
                sensor_ref = targets[build]
                sx, sy, _ = at(by_ref[sensor_ref])
                row = next(row for row in active
                           if "HE" + side[0] + row["ref"][3:] == sensor_ref)
                rotation = float(row["rotation_deg"])
                lx, ly, led_rotation = at(by_ref[led_ref])
                if abs(rotation - led_rotation) > 1e-5:
                    problems.append(f"{led_ref} rotation mismatch")
                angle = math.radians(-rotation)
                ex = sx + BOTTOM_LED_OFFSET * math.sin(angle)
                ey = sy - BOTTOM_LED_OFFSET * math.cos(angle)
                if math.dist((lx, ly), (ex, ey)) > 0.002:
                    problems.append(
                        f"{led_ref} is not at {BOTTOM_LED_OFFSET:.2f} mm offset")
                holes = [pad for pad in find(by_ref[sensor_ref], "pad")
                         if len(pad) > 3 and str(pad[2]) == "np_thru_hole"]
                hole_xy = sorted((round(float(first(pad, "at")[1]), 3),
                                  round(float(first(pad, "at")[2]), 3))
                                 for pad in holes)
                if hole_xy != [(-5.08, 0.0), (5.08, 0.0)]:
                    problems.append(f"{sensor_ref} alignment holes not horizontal")

            for led_ref, targets in FIXED_LED_TARGETS.get(side, {}).items():
                target = targets.get(build)
                if not target:
                    continue
                sensor_ref, dx, dy = target
                sensor = by_ref[sensor_ref]
                row = next(row for row in active
                           if "HE" + side[0] + row["ref"][3:] == sensor_ref)
                rotation = float(row["rotation_deg"])
                ex, ey = key_relative_position(sensor, dx, dy, rotation)
                lx, ly, led_rotation = at(by_ref[led_ref])
                if math.dist((lx, ly), (ex, ey)) > 0.002:
                    problems.append(f"{led_ref} is not on its fixed-layout row")
                if abs(led_rotation - rotation) > 1e-5:
                    problems.append(f"{led_ref} is not in normal orientation")

            for stab_ref, targets in FIXED_STABILIZER_ROTATIONS.get(
                    side, {}).items():
                target_rotation = targets.get(layout)
                if target_rotation is None:
                    target_rotation = targets.get(build)
                if target_rotation is None:
                    continue
                if stab_ref not in by_ref:
                    problems.append(f"missing rotated stabilizer {stab_ref}")
                    continue
                actual_rotation = at(by_ref[stab_ref])[2] % 360.0
                if abs(actual_rotation - target_rotation % 360.0) > 1e-5:
                    problems.append(f"{stab_ref} orientation mismatch")

            # Every physical reverse-mount RGB footprint owns exactly one
            # board aperture.  Removing an unused LED must therefore remove
            # its aperture as part of the same footprint.
            for ref in leds:
                edge_items = [item for item in by_ref[ref][1:]
                              if isinstance(item, list) and item and
                              str(item[0]) in ("fp_line", "fp_arc") and
                              first(item, "layer") is not None and
                              str(first(item, "layer")[1]) == "Edge.Cuts"]
                if not edge_items:
                    problems.append(f"{ref} is missing its LED aperture")

            # The universal planes clone every original LED cutout as an
            # explicit zone-outline hole.  Fixed layouts must not retain a
            # hole for a removed or relocated aperture, and their saved zone
            # fills must contain no copper beneath any retained LED opening.
            aperture_centers = {
                ref: aperture_center(by_ref[ref]) for ref in leds
            }
            aperture_points = [center for center in aperture_centers.values()
                               if center is not None]
            for zone in find(board, "zone"):
                layer_node = first(zone, "layer") or first(zone, "layers")
                layer = str(layer_node[1]) if layer_node else "unknown"
                outline_polygons = [item for item in zone[1:]
                                    if isinstance(item, list) and item and
                                    str(item[0]) == "polygon"]
                for polygon in outline_polygons:
                    geometry = polygon_geometry(polygon)
                    if geometry is None:
                        continue
                    x0, y0, x1, y1 = geometry.bounds
                    if x1 - x0 >= 10.0 or y1 - y0 >= 10.0:
                        continue
                    center = ((x0 + x1) / 2, (y0 + y1) / 2)
                    if (not aperture_points or
                            min(math.dist(center, point)
                                for point in aperture_points) > 0.08):
                        problems.append(
                            f"{layer} has obsolete LED-aperture zone void")

                fills = [polygon_geometry(item)
                         for item in find(zone, "filled_polygon")]
                fills = [geometry for geometry in fills if geometry is not None]
                for ref, center in aperture_centers.items():
                    if center is None:
                        continue
                    point = Point(center)
                    if any(geometry.buffer(1e-6).covers(point)
                           for geometry in fills):
                        problems.append(
                            f"{layer} copper fill crosses {ref} aperture")

            report = path.with_name(path.stem + "-drc.rpt")
            routing_categories = {
                "clearance", "shorting_items", "tracks_crossing",
                "connection_width", "track_dangling", "via_dangling",
                "unconnected_items",
            }
            edge_warnings = 0
            if not report.is_file():
                problems.append("missing KiCad DRC report")
            else:
                for line in report.read_text().splitlines():
                    match = re.match(r"^\[([^]]+)\]", line)
                    if not match:
                        continue
                    if match.group(1) in routing_categories:
                        problems.append("KiCad DRC routing/connectivity error")
                    elif match.group(1) == "copper_edge_clearance":
                        edge_warnings += 1

            status = "CLEAN" if not problems else "FAILED"
            print(f"{layout:15s} {side:5s}: {len(active):2d} Hall / "
                  f"{len(leds):2d} RGB / {edge_warnings} inherited edge "
                  f"warning(s)  {status}")
            for problem in problems:
                print("  -", problem)
            failed += len(problems)
    if failed:
        raise SystemExit(f"{failed} layout PCB audit problem(s)")
    print("\nLAYOUT PCB AUDIT CLEAN")


if __name__ == "__main__":
    main()
