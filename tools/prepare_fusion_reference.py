#!/usr/bin/env python3
"""Prepare exact PCB and plate solids for the Fusion reference assembly."""
from pathlib import Path
import glob
import json
import os
import shutil
import subprocess

import ezdxf
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from geom import BUILDS
from outline import (LEFT_PCB, RIGHT_PCB, DB, LEFT_PLATE, RIGHT_PLATE,
                     axis_mm)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "case/fusion360/generated"
OUT.mkdir(parents=True, exist_ok=True)


def find_cli():
    found = shutil.which("kicad-cli")
    if found:
        return found
    candidates = sorted(glob.glob(
        "/opt/homebrew/Caskroom/kicad/*/KiCad/KiCad.app/Contents/MacOS/kicad-cli"),
        reverse=True)
    if not candidates:
        raise RuntimeError("kicad-cli not found")
    return candidates[0]


def centre(poly):
    return [poly.centroid.x, poly.centroid.y]


def fused_plate_polygon(dxf):
    """Resolve overlapping DXF cutouts before OpenSCAD extrusion.

    Importing every closed DXF loop directly makes OpenSCAD apply even/odd
    nesting to overlapping switch and stabilizer contours.  That can turn an
    overlap back into small 7 x 14 mm material islands.  Boolean-union all
    openings first, then subtract them once from the plate exterior.
    """
    doc = ezdxf.readfile(dxf)
    by_layer = {}
    for entity in doc.modelspace().query("LWPOLYLINE"):
        points = [(point[0], point[1]) for point in entity.get_points("xy")]
        if len(points) >= 3:
            by_layer.setdefault(entity.dxf.layer, []).append(Polygon(points))
    outlines = by_layer.get("PLATE_OUTLINE", [])
    if len(outlines) != 1:
        raise RuntimeError(f"{dxf.name}: expected one plate outline")
    openings = (by_layer.get("SWITCH_CUTOUTS", []) +
                by_layer.get("STAB_CLEARANCE", []))
    plate = outlines[0].difference(unary_union(openings)).buffer(0)
    if plate.geom_type != "Polygon" or not plate.is_valid:
        raise RuntimeError(f"{dxf.name}: cutout boolean did not produce one plate")
    return orient(plate, sign=1.0)


def scad_polygon(poly):
    rings = [list(poly.exterior.coords)[:-1]] + [list(r.coords)[:-1]
                                                    for r in poly.interiors]
    points = []
    paths = []
    for ring in rings:
        start = len(points)
        points.extend(ring)
        paths.append(list(range(start, start + len(ring))))
    point_text = ",".join(f"[{x:.6f},{y:.6f}]" for x, y in points)
    path_text = ",".join("[" + ",".join(map(str, path)) + "]"
                         for path in paths)
    return f"polygon(points=[{point_text}], paths=[{path_text}], convexity=10);"


def main():
    cli = find_cli()
    openscad = shutil.which("openscad")
    if not openscad:
        raise RuntimeError("OpenSCAD not found")
    shapes = {
        "LeftPCB": LEFT_PCB,
        "RightPCB": RIGHT_PCB,
        "DaughterboardPCB": DB,
        "LeftPlate": LEFT_PLATE,
        "RightPlate": RIGHT_PLATE,
    }
    layout = {name: {"centre": centre(poly), "bounds": list(poly.bounds)}
              for name, poly in shapes.items()}
    visual_layout = os.environ.get("SYMM60HE_VISUAL_LAYOUT", "doe-wkl")
    if visual_layout not in BUILDS:
        raise ValueError("SYMM60HE_VISUAL_LAYOUT must be one of: %s" %
                         ", ".join(BUILDS))
    layout.update({"axis_x": axis_mm, "front_y": 100.0,
                   "tent_deg": 6.0, "typing_deg": 11.0,
                   "plate_z": 10.0, "pcb_z": 3.5,
                   "visual_layout": visual_layout})
    (OUT / "reference-layout.json").write_text(json.dumps(layout, indent=2) + "\n")

    for name, stem in (("LeftPCB", "Symm60HE-Left"),
                       ("RightPCB", "Symm60HE-Right"),
                       ("DaughterboardPCB", "Symm60HE-Daughterboard")):
        subprocess.run([cli, "pcb", "export", "step", "--board-only",
                        "--force", "-o", str(OUT / f"{name}.step"),
                        str(ROOT / "pcb" / f"{stem}.kicad_pcb")], check=True)

    for name, side in (("LeftPlate", "left"), ("RightPlate", "right")):
        dxf = ROOT / "plate" / f"Symm60HE-plate-universal-{side}.dxf"
        scad = OUT / f"{name}.scad"
        plate = fused_plate_polygon(dxf)
        scad.write_text(
            "$fn=48;\n"
            "linear_extrude(height=1.5, convexity=10)\n"
            f"  {scad_polygon(plate)}\n")
        subprocess.run([openscad, "-o", str(OUT / f"{name}.stl"), str(scad)],
                       check=True)
    print("prepared Fusion reference solids in", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
