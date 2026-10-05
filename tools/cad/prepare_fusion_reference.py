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
from outline import LEFT_PLATE, RIGHT_PLATE, axis_mm

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "case/fusion360/generated"
OUT.mkdir(parents=True, exist_ok=True)
# The checked-in pcb/ files are the authoritative routed boards.  The older
# work/ candidate remains useful forensic history, but must not silently feed
# stale outlines or mounting-hole coordinates into the Fusion reference.
CURRENT_PCB_DIR = ROOT / "pcb"

# Gateron DS-02-001-A0 defines 5.00 +/- 0.05 mm from the KS-20 plate
# seating plane to the PCB top. The specified 1.50 mm plate therefore spans
# downward from that seating plane and leaves 3.50 mm nominally between its
# underside and the PCB top. Keep these as explicit datums so a plate-solid
# origin cannot accidentally be mistaken for the seating surface again.
PLATE_SEATING_Z_MM = 10.0
PLATE_THICKNESS_MM = 1.5
PLATE_TO_PCB_TOP_MM = 5.0
PCB_TOP_Z_MM = PLATE_SEATING_Z_MM - PLATE_TO_PCB_TOP_MM
PLATE_BOTTOM_Z_MM = PLATE_SEATING_Z_MM - PLATE_THICKNESS_MM
DAUGHTERBOARD_BELOW_HALL_PCB_MM = 7.0
DAUGHTERBOARD_TOP_Z_MM = PCB_TOP_Z_MM - DAUGHTERBOARD_BELOW_HALL_PCB_MM


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


def find_kicad_python():
    """KiCad's own interpreter, which is the one that can import pcbnew."""
    override = os.environ.get("SYMM60_KICAD_PYTHON")
    if override:
        return override
    candidates = sorted(glob.glob(
        "/opt/homebrew/Caskroom/kicad/*/KiCad/KiCad.app/Contents/Frameworks/"
        "Python.framework/Versions/*/bin/python3.*"), reverse=True)
    candidates = [path for path in candidates
                  if Path(path).name.removeprefix("python3.").isdigit()]
    # Windows and Linux keep it beside kicad-cli instead.  Sort on the version
    # numerically: as text, "9.0" sorts above "10.0".
    def version_key(path):
        name = Path(path).parents[1].name
        return tuple(int(part) if part.isdigit() else -1
                     for part in name.split("."))

    candidates += sorted(glob.glob("C:/Program Files/KiCad/*/bin/python.exe"),
                         key=version_key, reverse=True)
    candidates += [path for path in (shutil.which("kicad-python"),) if path]
    if not candidates:
        raise RuntimeError("KiCad bundled Python not found")
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
                by_layer.get("STAB_CLEARANCE", []) +
                by_layer.get("STANDOFF_HOLES", []))
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
    # The plate solids need OpenSCAD.  The boards do not, so a machine without
    # it still gets the PCB and component STEPs rather than nothing at all.
    openscad = shutil.which("openscad")
    board_sources = {
        # The completed manufacturing designs use the repository's canonical
        # filenames.  Case references must follow those files so they cannot
        # silently drift back to an obsolete routing iteration.
        "LeftPCB": CURRENT_PCB_DIR / "Symm60HE-Left.kicad_pcb",
        "RightPCB": CURRENT_PCB_DIR / "Symm60HE-Right.kicad_pcb",
        "DaughterboardPCB": CURRENT_PCB_DIR / "Symm60HE-Daughterboard.kicad_pcb",
    }
    missing = [str(path) for path in board_sources.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing current routed PCB: " + ", ".join(missing))
    geometry_json = OUT / "pcb-reference-geometry.json"
    subprocess.run([
        find_kicad_python(), str(Path(__file__).with_name(
            "extract_pcb_reference_geometry.py")),
        "--output", str(geometry_json),
        *[f"{name}={path}" for name, path in board_sources.items()],
    ], check=True)
    pcb_layout = json.loads(geometry_json.read_text())
    shapes = {
        "LeftPlate": LEFT_PLATE,
        "RightPlate": RIGHT_PLATE,
    }
    layout = dict(pcb_layout)
    layout.update({
        name: {"centre": centre(poly), "bounds": list(poly.bounds)}
        for name, poly in shapes.items()
    })
    visual_layout = os.environ.get("SYMM60HE_VISUAL_LAYOUT", "doe-wkl")
    if visual_layout not in BUILDS:
        raise ValueError("SYMM60HE_VISUAL_LAYOUT must be one of: %s" %
                         ", ".join(BUILDS))
    layout.update({"axis_x": axis_mm, "front_y": 100.0,
                   "tent_deg": 3.0, "typing_deg": 7.0,
                   "typing_rotation_deg": -7.0,
                   "plate_seating_z": PLATE_SEATING_Z_MM,
                   "plate_z": PLATE_BOTTOM_Z_MM,
                   "plate_thickness_mm": PLATE_THICKNESS_MM,
                   "plate_to_pcb_top_mm": PLATE_TO_PCB_TOP_MM,
                   "plate_underside_to_pcb_top_mm": (
                       PLATE_TO_PCB_TOP_MM - PLATE_THICKNESS_MM),
                   "pcb_z": PCB_TOP_Z_MM,
                   "daughterboard_below_hall_pcb_mm": (
                       DAUGHTERBOARD_BELOW_HALL_PCB_MM),
                   "daughterboard_z": DAUGHTERBOARD_TOP_Z_MM,
                   "visual_layout": visual_layout})
    # The routed daughterboard uses its own convenient KiCad drawing origin.
    # In the enclosure it is centered on the split axis at the rear and lies
    # flat across the lateral tent, seven millimetres below the Hall PCBs.
    layout["DaughterboardPCB"]["assembly_centre"] = [
        axis_mm, layout["DaughterboardPCB"]["centre"][1]
    ]
    (OUT / "reference-layout.json").write_text(json.dumps(layout, indent=2) + "\n")

    for name, source in board_sources.items():
        # Keep the dielectric board independent from the exact fitted-component
        # body assembled later by FreeCAD.  Do not export KiCad's generic
        # package models here: using both would double every component.
        subprocess.run([
            cli, "pcb", "export", "step", "--board-only", "--force",
            "-o", str(OUT / f"{name}.step"), str(source),
        ], check=True)

    if not openscad:
        print("OpenSCAD not found: skipping the plate solids")
    for name, side in (() if not openscad else
                       (("LeftPlate", "left"), ("RightPlate", "right"))):
        dxf = ROOT / "plate" / f"Symm60HE-plate-universal-{side}.dxf"
        scad = OUT / f"{name}.scad"
        plate = fused_plate_polygon(dxf)
        scad.write_text(
            "$fn=48;\n"
            f"linear_extrude(height={PLATE_THICKNESS_MM}, convexity=10)\n"
            f"  {scad_polygon(plate)}\n")
        subprocess.run([openscad, "-o", str(OUT / f"{name}.stl"), str(scad)],
                       check=True)
    print("prepared Fusion reference solids in", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
