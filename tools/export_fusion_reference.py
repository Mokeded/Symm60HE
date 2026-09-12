#!/usr/bin/env python3
"""Create a Fusion-ready PCB, plate, switch and keycap reference assembly.

Run with FreeCAD's bundled ``freecadcmd`` after prepare_fusion_reference.py.
The objects are intentionally separate named bodies and are positioned on the
same tented/typed planes they occupy in the future enclosure.
"""
from pathlib import Path
import json

import FreeCAD as App
import Import
import Mesh
import Part

from geom import KEYS, U

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "case/fusion360"
GEN = OUT / "generated"


def import_step_shape(path):
    temp = App.newDocument("ImportTemp")
    Import.insert(str(path), temp.Name)
    shapes = [obj.Shape for obj in temp.Objects
              if (hasattr(obj, "Shape") and not obj.Shape.isNull() and
                  obj.Shape.Solids and 1e-6 < abs(obj.Shape.Volume) < 1e12)]
    if not shapes:
        raise RuntimeError(f"STEP contained no shapes: {path}")
    # KiCad's STEP hierarchy exposes the same board solid through both its
    # product and child object; keep one physical solid, not both duplicates or
    # FreeCAD's infinite origin planes.
    result = max(shapes, key=lambda shape: abs(shape.Volume)).copy()
    App.closeDocument(temp.Name)
    return result


def solid_from_stl(path):
    mesh = Mesh.Mesh(str(path))
    shape = Part.Shape()
    shape.makeShapeFromMesh(mesh.Topology, 0.02)
    solids = []
    for shell in shape.Shells:
        solid = Part.makeSolid(shell)
        if not solid.isNull() and solid.Volume > 1e-5:
            solids.append(solid)
    if not solids:
        raise RuntimeError(f"STL conversion produced no solid: {path}")
    return Part.makeCompound(solids).removeSplitter()


def align_xy(shape, desired_centre, mirror_y=False):
    result = shape.copy()
    if mirror_y:
        # KiCad STEP uses conventional Y-up coordinates while the board/DXF
        # sources use KiCad's screen-space Y-down coordinates. A 180 degree
        # rigid rotation about X corrects Y without the invalid negative-scale
        # transform that corrupts analytic STEP surfaces.
        result.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 180)
    bb = result.BoundBox
    result.translate(App.Vector(desired_centre[0] - (bb.XMin + bb.XMax)/2,
                                desired_centre[1] - (bb.YMin + bb.YMax)/2, 0))
    return result


def place(shape, layout, side, z):
    result = shape.copy()
    pivot = App.Vector(layout["axis_x"], layout["front_y"], 0)
    result.rotate(pivot, App.Vector(1, 0, 0), layout["typing_deg"])
    result.rotate(pivot, App.Vector(0, 1, 0),
                  -layout["tent_deg"] if side == "left" else layout["tent_deg"])
    result.translate(App.Vector(0, 0, z))
    return result


def centred_box(width, depth, height, z):
    return Part.makeBox(width, depth, height,
                        App.Vector(-width / 2, -depth / 2, z))


def at_key(shape, key):
    """Place a local solid at a key centre in the un-tented plate plane."""
    result = shape.copy()
    result.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), key["rot"])
    result.translate(App.Vector(key["cx"] * U, key["cy"] * U, 0))
    return result


def switch_shape(key):
    """Simplified MX-compatible Hall switch clearance solid."""
    housing = centred_box(13.8, 13.8, 5.8, -2.2)
    stem_a = centred_box(4.2, 1.3, 4.2, 3.6)
    stem_b = centred_box(1.3, 4.2, 4.2, 3.6)
    return at_key(Part.makeCompound([housing, stem_a, stem_b]), key)


def rectangle_wire(width, depth, z):
    points = [
        App.Vector(-width / 2, -depth / 2, z),
        App.Vector(width / 2, -depth / 2, z),
        App.Vector(width / 2, depth / 2, z),
        App.Vector(-width / 2, depth / 2, z),
        App.Vector(-width / 2, -depth / 2, z),
    ]
    return Part.makePolygon(points)


def keycap_shape(key):
    """Simplified OEM-height tapered keycap envelope for case visualization."""
    lower_w = max(12.0, key["w"] * U - 1.0)
    lower_d = U - 1.0
    upper_w = max(10.0, lower_w - 3.0)
    upper_d = lower_d - 3.0
    cap = Part.makeLoft([rectangle_wire(lower_w, lower_d, 6.4),
                         rectangle_wire(upper_w, upper_d, 15.4)], True)
    return at_key(cap, key)


def add_reference(doc, root, internal, label, shape, role, colour,
                  transparency=0):
    obj = doc.addObject("PartDesign::Feature", internal)
    obj.Label = label
    obj.Shape = shape
    obj.addProperty("App::PropertyString", "Role", "Reference")
    obj.Role = role
    # freecadcmd has no GUI ViewObject. Preserve intended display metadata as
    # ordinary properties so Fusion/FreeCAD users can style the groups after
    # import without making headless release generation depend on a GUI.
    obj.addProperty("App::PropertyString", "SuggestedColour", "Reference")
    obj.SuggestedColour = "%.3f, %.3f, %.3f" % colour
    obj.addProperty("App::PropertyInteger", "SuggestedTransparency",
                    "Reference")
    obj.SuggestedTransparency = transparency
    root.addObject(obj)
    return obj


def main():
    layout = json.loads((GEN / "reference-layout.json").read_text())
    doc = App.newDocument("Symm60HE_Reference_Assembly")
    root = doc.addObject("App::Part", "Symm60HEReferenceAssembly")
    root.Label = "Symm60HE case-design reference assembly"
    specs = [
        ("LeftPCB", "Left PCB", "LeftPCB.step", "left", layout["pcb_z"], True),
        ("RightPCB", "Right PCB", "RightPCB.step", "right", layout["pcb_z"], True),
        ("DaughterboardPCB", "Daughterboard PCB", "DaughterboardPCB.step",
         "right", layout["pcb_z"], True),
        ("LeftPlate", "Left universal plate", "LeftPlate.stl", "left",
         layout["plate_z"], False),
        ("RightPlate", "Right universal plate", "RightPlate.stl", "right",
         layout["plate_z"], False),
    ]
    objects = []
    for internal, label, filename, side, z, is_step in specs:
        raw = (import_step_shape(GEN / filename) if is_step
               else solid_from_stl(GEN / filename))
        aligned = align_xy(raw, layout[internal]["centre"], mirror_y=is_step)
        colour = ((0.10, 0.34, 0.17) if "PCB" in internal
                  else (0.68, 0.70, 0.73))
        obj = add_reference(
            doc, root, internal, label, place(aligned, layout, side, z),
            "PCB reference" if "PCB" in internal else "plate reference",
            colour, 0 if "PCB" in internal else 25)
        objects.append(obj)
        Import.export([obj], str(OUT / f"Symm60HE-{internal}.step"))
        Mesh.export([obj], str(GEN / f"{internal}-placed.stl"))
        print(label, "volume", round(obj.Shape.Volume, 2), "mm^3")

    selected = [key for key in KEYS
                if layout["visual_layout"] in key["builds"]]
    for side_name, side_code in (("Left", "L"), ("Right", "R")):
        keys = [key for key in selected if key["half"] == side_code]
        side = side_name.lower()
        switches = Part.makeCompound([switch_shape(key) for key in keys])
        keycaps = Part.makeCompound([keycap_shape(key) for key in keys])
        switch_obj = add_reference(
            doc, root, side_name + "Switches", side_name + " switches",
            place(switches, layout, side, layout["plate_z"]),
            "simplified switch visualization", (0.18, 0.18, 0.20))
        keycap_obj = add_reference(
            doc, root, side_name + "Keycaps", side_name + " keycaps",
            place(keycaps, layout, side, layout["plate_z"]),
            "simplified keycap envelope", (0.83, 0.84, 0.80), 8)
        objects.extend((switch_obj, keycap_obj))
        Import.export([switch_obj],
                      str(OUT / f"Symm60HE-{side_name}Switches.step"))
        Import.export([keycap_obj],
                      str(OUT / f"Symm60HE-{side_name}Keycaps.step"))
        Mesh.export([switch_obj],
                    str(GEN / f"{side_name}Switches-placed.stl"))
        Mesh.export([keycap_obj],
                    str(GEN / f"{side_name}Keycaps-placed.stl"))
        print(side_name, "visualization", len(keys), "switches and keycaps")
    doc.recompute()
    Import.export(objects, str(OUT / "Symm60HE-reference-assembly.step"))
    source = OUT / "Symm60HE-reference-assembly.FCStd"
    # This is a generated handoff, so replace it cleanly instead of asking
    # FreeCAD to create timestamped .FCBak files in the active case directory.
    if source.exists():
        source.unlink()
    doc.saveAs(str(source))
    print("wrote", OUT / "Symm60HE-reference-assembly.step")
    print("wrote", OUT / "Symm60HE-reference-assembly.FCStd")


main()
