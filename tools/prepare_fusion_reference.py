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
                     axis_mm, HALF_SPREAD, DB_USB_OVERHANG)
from sexp import find, loads

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


def modeled_references(board_path, excluded=()):
    """Return fitted references that have a real KiCad 3D model assignment."""
    board = loads(board_path.read_text())
    refs = []
    for footprint in find(board, "footprint"):
        if not find(footprint, "model"):
            continue
        properties = {item[1]: item[2] for item in find(footprint, "property")
                      if len(item) > 2}
        reference = properties.get("Reference")
        if reference and reference not in excluded:
            refs.append(reference)
    return sorted(refs)


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
                   "half_spread_mm": HALF_SPREAD,
                   # Mechanical datums supplied by the project owner:
                   # DOE-style lateral tent is 3 degrees per half and the
                   # FN40 front-to-back typing angle is 7 degrees.
                   "tent_deg": 3.0, "typing_deg": 7.0,
                   "plate_z": 10.0, "pcb_z": 3.5,
                   "visual_layout": visual_layout})
    (OUT / "reference-layout.json").write_text(json.dumps(layout, indent=2) + "\n")

    # The case reference uses the active Neo-style pogo architecture. Export
    # all five rigid boards so the downstream assembly has their real outlines.
    neo = ROOT / "pcb" / "variants" / "pogo-neo"
    board_sources = (
        ("LeftPCB", neo / "Symm60HE-Neo-Left-Half.kicad_pcb"),
        ("RightPCB", neo / "Symm60HE-Neo-Right-Half.kicad_pcb"),
        ("DaughterboardPCB", neo / "Symm60HE-Neo-Controller.kicad_pcb"),
        ("LeftSpringPCB", neo / "Symm60HE-Neo-Left-SpringModule.kicad_pcb"),
        ("RightSpringPCB", neo / "Symm60HE-Neo-Right-SpringModule.kicad_pcb"),
    )
    for name, source in board_sources:
        subprocess.run([cli, "pcb", "export", "step", "--board-only",
                        "--force", "-o", str(OUT / f"{name}.step"),
                        str(source)], check=True)

    # Bring the real package bodies into the enclosure reference as separate
    # component groups. Exact enclosure-critical connectors remain separate
    # editable components below; the remaining assigned models are KiCad's
    # maintained package references and must not be described as manufacturer
    # CAD. Spring boards have no additional modeled parts once their FFC and
    # pogo connectors are handled explicitly.
    component_exports = (
        ("LeftPCBComponents", dict(board_sources)["LeftPCB"], ()),
        ("RightPCBComponents", dict(board_sources)["RightPCB"], ()),
        ("DaughterboardComponents", dict(board_sources)["DaughterboardPCB"],
         ("J1", "J2", "J3")),
    )
    model_dir = ROOT / "case/fusion360/models"
    for name, source, excluded in component_exports:
        references = modeled_references(source, excluded)
        if not references:
            raise RuntimeError(f"{source.name}: no component models to export")
        subprocess.run([
            cli, "pcb", "export", "step", "--no-board-body", "--no-dnp",
            "--component-filter", ",".join(references), "--force",
            "-D", f"SYMM60HE_3DMODEL_DIR={model_dir}",
            "-o", str(OUT / f"{name}.step"), str(source),
        ], check=True)

    # The actual HRO TYPE-C-31-M-12 receptacle is imported directly from the
    # source-locked vendor STEP by export_fusion_reference.py.  Do not ask
    # KiCad for a component-only wrapper here: routed board saves can omit the
    # optional footprint-model record, and the wrapper is unnecessary because
    # the downstream exporter applies and verifies the exact J1 datum itself.
    controller_source = dict((name, source) for name, source in board_sources)[
        "DaughterboardPCB"]

    layout["mechanism"] = {
        "board_thickness": 1.2,
        # Exact 854/856 supplier geometry provides 5.2578 mm of free reach.
        # Use a 5.0 mm working separation for 0.2578 mm contact preload and
        # 0.7582 mm remaining spring travel.
        "board_to_board": 5.0,
        "controller_centre": [axis_mm, 56.0],
        # Keep the controller in its native left-to-right orientation.  J1 is
        # authored on the rear edge of the PCB; rotating the board 90 degrees
        # incorrectly aimed USB-C into the right keyboard half.
        "controller_rotation_deg": 0.0,
        "controller_bottom_z": -6.5,
        "left_target": [148.0, 56.0],
        "right_target": [154.418, 56.0],
        "left_target_rotation_deg": -90.0,
        "right_target_rotation_deg": 90.0,
        "spring_board_size": [20.0, 6.0],
        "spring_board_source_centre": [10.0, 3.0],
        "spring_board_rotation_deg": 90.0,
        "controller_source_centre": centre(DB),
        "controller_left_ffc": [157.509, 9.2367],
        "controller_right_ffc": [208.909, 9.2367],
        "controller_left_ffc_rotation_deg": -90.0,
        "controller_right_ffc_rotation_deg": 90.0,
        "controller_usb": [192.209, -4.1133],
        "controller_usb_rotation_deg": 180.0,
        # The HRO distributor STEP's native mating mouth faces +Y. The keyboard
        # rear is minimum Y, so rotate only the vendor B-rep 180 degrees and
        # align its mouth to the minimum-Y rear edge.
        "controller_usb_model_rotation_deg": 180.0,
        "controller_usb_overhang": DB_USB_OVERHANG,
    }
    # Rewrite after adding the mechanism datums.
    (OUT / "reference-layout.json").write_text(
        json.dumps(layout, indent=2) + "\n")

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
