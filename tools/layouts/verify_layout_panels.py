#!/usr/bin/env python3
"""Verify that each fixed-layout manufacturing panel is an exact two-half copy."""
from __future__ import annotations

from pathlib import Path
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from layouts.catalog import LAYOUTS  # noqa: E402
from generators.mkschematics import components, symbol_name  # noqa: E402
from pcb.panelize import edge_polygon  # noqa: E402
from schematic_parity import symbol_map  # noqa: E402
from sexp import find, first, loads  # noqa: E402

LAYOUT_ROOT = ROOT / "pcb/variants/layouts"


def reference(footprint):
    for prop in find(footprint, "property"):
        if len(prop) > 2 and str(prop[1]) == "Reference":
            return str(prop[2])
    return None


def references(board):
    return {reference(fp) for fp in find(board, "footprint") if reference(fp)}


def hall_keepout_problems(board):
    """Audit the exact circular F.Cu/B.Cu rule copied from FN40HE."""
    halls = {}
    for footprint in find(board, "footprint"):
        ref = reference(footprint) or ""
        if not ref.startswith(("L-HEL", "R-HER")):
            continue
        at = first(footprint, "at")
        halls[ref] = (float(at[1]), float(at[2]))

    keepouts = {}
    problems = []
    for zone in find(board, "zone"):
        name = first(zone, "name")
        if not name or not str(name[1]).startswith("MAGNET_"):
            continue
        ref = str(name[1])[len("MAGNET_"):]
        if ref in keepouts:
            problems.append(f"duplicate MAGNET_{ref} keepout")
            continue
        keepouts[ref] = zone

    if set(keepouts) != set(halls):
        missing = sorted(set(halls) - set(keepouts))
        extra = sorted(set(keepouts) - set(halls))
        if missing:
            problems.append(f"missing Hall keepouts: {', '.join(missing)}")
        if extra:
            problems.append(f"orphan Hall keepouts: {', '.join(extra)}")

    expected_rules = {
        "tracks": "allowed",
        "vias": "not_allowed",
        "pads": "allowed",
        "copperpour": "not_allowed",
        "footprints": "allowed",
    }
    centres = []
    for ref, zone in keepouts.items():
        layers = first(zone, "layers")
        if not layers or set(map(str, layers[1:])) != {"F.Cu", "B.Cu"}:
            problems.append(f"MAGNET_{ref} is not on F.Cu and B.Cu")
        rules = first(zone, "keepout")
        actual = {}
        if rules:
            for item in rules[1:]:
                if isinstance(item, list) and len(item) >= 2:
                    actual[str(item[0])] = str(item[1])
        if actual != expected_rules:
            problems.append(f"MAGNET_{ref} rule differs from FN40HE")
        polygon = first(zone, "polygon")
        points = first(polygon, "pts") if polygon else None
        arc = first(points, "arc") if points else None
        if not arc:
            problems.append(f"MAGNET_{ref} is not circular")
            continue
        start, middle = first(arc, "start"), first(arc, "mid")
        a = (float(start[1]), float(start[2]))
        b = (float(middle[1]), float(middle[2]))
        centre = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        radius = math.dist(a, centre)
        centres.append((ref, centre, radius))
        if abs(radius - 1.8) > 1e-6:
            problems.append(f"MAGNET_{ref} radius is {radius:.6f} mm")
        if ref in halls and math.dist(centre, halls[ref]) > 1e-6:
            problems.append(f"MAGNET_{ref} is not centred on its Hall sensor")

    # A no-via keepout applies to the via annulus, not only its drill centre.
    for via in find(board, "via"):
        at = first(via, "at")
        size = first(via, "size")
        point = (float(at[1]), float(at[2]))
        via_radius = float(size[1]) / 2 if size else 0.30
        for ref, centre, radius in centres:
            if math.dist(point, centre) < radius + via_radius - 1e-6:
                problems.append(f"via annulus intersects MAGNET_{ref}")
                break
    return problems


def nested_net_names(node):
    names = set()
    if not isinstance(node, list):
        return names
    if node and node[0] == "net" and len(node) == 2 and str(node[1]):
        names.add(str(node[1]))
    for child in node[1:]:
        names.update(nested_net_names(child))
    return names


def main():
    failed = False
    for layout in LAYOUTS:
        directory = LAYOUT_ROOT / layout
        stem = f"Symm60HE-{layout}"
        paths = {
            "P": directory / f"{stem}-Panel.kicad_pcb",
            "SCH": directory / f"{stem}-Panel.kicad_sch",
            "SYM": directory / f"{stem}-Panel.kicad_sym",
            "PRO": directory / f"{stem}-Panel.kicad_pro",
        }
        missing = [path for path in paths.values() if not path.exists()]
        if missing:
            print(f"{layout}: FAIL missing {', '.join(map(str, missing))}")
            failed = True
            continue
        panel = loads(paths["P"].read_text())
        panel_refs = references(panel)
        problems = []
        allowed_structural = ({f"MB{i}" for i in range(1, 66)} |
                              {f"FID{i}" for i in range(1, 4)} |
                              {f"TH{i}" for i in range(1, 5)})
        if not any(ref.startswith("L-") for ref in panel_refs):
            problems.append("missing left-half component namespace")
        if not any(ref.startswith("R-") for ref in panel_refs):
            problems.append("missing right-half component namespace")
        unexpected = {ref for ref in panel_refs
                      if not ref.startswith(("L-", "R-")) and
                      ref not in allowed_structural}
        if unexpected:
            problems.append("unexpected unnamespaced panel references")
        net_names = nested_net_names(panel)
        if any(name and not name.startswith(("/L/", "/R/")) for name in net_names):
            problems.append("unprefixed electrical net")
        if not any(name.startswith("/L/") for name in net_names):
            problems.append("missing left-half nets")
        if not any(name.startswith("/R/") for name in net_names):
            problems.append("missing right-half nets")
        expected_symbols = {
            symbol_name(part["ref"]): dict(part["pads"])
            for part in components(paths["P"])
        }
        if symbol_map(paths["SYM"]) != expected_symbols:
            problems.append("combined schematic symbol/pad/net parity mismatch")
        schematic_tree = loads(paths["SCH"].read_text())
        schematic_instances = [node for node in schematic_tree
                               if isinstance(node, list) and node and
                               node[0] == "symbol"]
        missing_footprints = []
        for symbol in schematic_instances:
            properties = {str(prop[1]): str(prop[2])
                          for prop in find(symbol, "property") if len(prop) > 2}
            if not properties.get("Footprint"):
                missing_footprints.append(properties.get("Reference", "?"))
        if missing_footprints:
            problems.append("combined schematic has unassigned footprints")
        project = json.loads(paths["PRO"].read_text())
        sheets = project.get("schematic", {}).get("top_level_sheets", [])
        if (len(sheets) != 1 or
                sheets[0].get("filename") != paths["SCH"].name):
            problems.append("project does not link its combined schematic")
        polygon = edge_polygon(panel)
        width = polygon.bounds[2] - polygon.bounds[0]
        height = polygon.bounds[3] - polygon.bounds[1]
        if abs(width - 162.29) > 0.01 or abs(height - 227.83) > 0.01:
            problems.append(f"panel is {width:.2f} x {height:.2f} mm")
        general = first(panel, "general")
        thickness = first(general, "thickness") if general else None
        if not thickness or abs(float(thickness[1]) - 1.2) > 1e-6:
            problems.append("panel thickness is not 1.2 mm")
        mouse = [fp for fp in find(panel, "footprint")
                 if (reference(fp) or "").startswith("MB")]
        if len(mouse) != 65:
            problems.append("panel does not have 65 mouse-bite drills")
        else:
            for fp in mouse:
                pads = find(fp, "pad")
                drill = first(pads[0], "drill") if len(pads) == 1 else None
                if (not drill or abs(float(drill[1]) - 0.5) > 1e-6 or
                        str(pads[0][2]) != "np_thru_hole"):
                    problems.append("mouse bites are not 0.5 mm NPTHs")
                    break
        problems.extend(hall_keepout_problems(panel))
        if problems:
            print(f"{layout}: FAIL " + "; ".join(problems))
            failed = True
        else:
            print(f"{layout}: ok - 162.29 x 227.83 mm, 65 bites, "
                  f"{len(expected_symbols)}-symbol self-contained design, "
                  "FN40HE Hall keepouts")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
