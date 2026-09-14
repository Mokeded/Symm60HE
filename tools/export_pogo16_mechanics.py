#!/usr/bin/env python3
"""Generate editable Fusion/FreeCAD reference bodies for the pogo16 tent cradle."""
from pathlib import Path

import FreeCAD as App
import Import
import Mesh
import Part

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "case/fusion360/pogo-variant"

TENT_DEG = 3.0
BOARD_SPACING = 6.0
WING_W = 18.0
WING_D = 28.0
PCB_T = 1.2


def local_box(w, d, h, z=0):
    return Part.makeBox(w, d, h, App.Vector(-w / 2, -d / 2, z))


def cylinder(d, h, x, y, z=0):
    return Part.makeCylinder(d / 2, h, App.Vector(x, y, z))


def place(shape, x, angle):
    result = shape.copy()
    result.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), angle)
    result.translate(App.Vector(x, 0, 0))
    return result


def add(doc, group, name, label, shape, role, dnp=False):
    obj = doc.addObject("PartDesign::Feature", name)
    obj.Label = label
    obj.Shape = shape
    obj.addProperty("App::PropertyString", "Role", "Engineering")
    obj.Role = role
    obj.addProperty("App::PropertyBool", "DNP_Until_Hall_Test", "Engineering")
    obj.DNP_Until_Hall_Test = dnp
    group.addObject(obj)
    return obj


def side_objects(doc, root, side, x, angle):
    group = doc.addObject("App::Part", side + "PogoInterface")
    group.Label = side + " independently compliant pogo wing"
    root.addObject(group)
    objects = []

    # The carrier surrounds the wing PCB while leaving its component face open.
    outer = local_box(22, 32, 2.4, -2.4)
    pocket = local_box(18.4, 28.4, 2.5, -1.8)
    carrier = outer.cut(pocket)
    objects.append(add(doc, group, side + "Carrier", side + " wing carrier",
                       place(carrier, x, angle),
                       "Nonmagnetic carrier; permits local Z compliance"))

    wing = local_box(WING_W, WING_D, PCB_T, 0)
    objects.append(add(doc, group, side + "SpringWingPCB", side + " spring wing PCB",
                       place(wing, x, angle),
                       "1.2 mm rigid PCB carrying Mill-Max 855 spring connector"))

    connector = local_box(10.54, 2.54, 4.2, PCB_T)
    objects.append(add(doc, group, side + "SpringConnector",
                       side + " Mill-Max 855 spring connector",
                       place(connector, x, angle),
                       "855-22-016-30-004101 envelope"))

    target = local_box(WING_W, WING_D, PCB_T, BOARD_SPACING)
    objects.append(add(doc, group, side + "TargetPCBReference",
                       side + " keyboard target-plane reference",
                       place(target, x, angle),
                       "Reference only; interface is parallel at 6.0 mm spacing"))

    # Two round guides plus an asymmetric larger key establish XY/theta.
    guide_shape = Part.makeCompound([
        cylinder(2.0, BOARD_SPACING, -6.5, 0),
        cylinder(2.0, BOARD_SPACING, 6.5, 0),
        cylinder(2.6, BOARD_SPACING, 6.5, 6.5),
    ])
    objects.append(add(doc, group, side + "AlignmentPins", side + " alignment and key pins",
                       place(guide_shape, x, angle),
                       "2.0 mm guides plus asymmetric 2.6 mm key"))

    stops = Part.makeCompound([
        local_box(2.0, 2.0, BOARD_SPACING, 0).translated(App.Vector(dx, dy, 0))
        for dx, dy in ((-7.5, -11.5), (7.5, -11.5), (-7.5, 11.5), (7.5, 11.5))
    ])
    objects.append(add(doc, group, side + "HardStops", side + " 6.0 mm hard stops",
                       place(stops, x, angle),
                       "Defines 0.5 mm nominal connector compression"))

    poron = Part.makeCompound([
        local_box(4.0, 4.0, 0.8, -0.8).translated(App.Vector(dx, dy, 0))
        for dx, dy in ((-6.5, -10.5), (6.5, -10.5), (-6.5, 10.5), (6.5, 10.5))
    ])
    objects.append(add(doc, group, side + "PoronPads", side + " 0.8 mm Poron pads",
                       place(poron, x, angle), "Wing support and local compliance"))

    magnets = Part.makeCompound([
        cylinder(4.0, 2.0, 0, -8.5, -2.0),
        cylinder(4.0, 2.0, 0, 8.5, -2.0),
    ])
    objects.append(add(doc, group, side + "MagnetEnvelopes",
                       side + " provisional 4x2 N35 magnet envelopes",
                       place(magnets, x, angle),
                       "Retention only; use steel backing; replace with screws if Hall test fails",
                       dnp=True))

    return objects


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = App.newDocument("Symm60HE_Pogo16_Tent_Cradle")
    root = doc.addObject("App::Part", "Pogo16TentCradle")
    root.Label = "Symm60HE 16-contact tented pogo reference"
    objects = []
    centre = local_box(57, 27, 1.2, 0)
    objects.append(add(doc, root, "ControllerPCBReference", "57x27 controller PCB reference",
                       centre, "Existing central controller envelope; fixed in case"))
    objects += side_objects(doc, root, "Left", -40.0, TENT_DEG)
    objects += side_objects(doc, root, "Right", 40.0, -TENT_DEG)
    doc.recompute()

    source = OUT / "Symm60HE-pogo16-tent-cradle.FCStd"
    if source.exists():
        source.unlink()
    doc.saveAs(str(source))
    Import.export(objects, str(OUT / "Symm60HE-pogo16-tent-cradle.step"))
    Mesh.export(objects, str(OUT / "Symm60HE-pogo16-tent-cradle.stl"))
    print(source.relative_to(ROOT))
    print((OUT / "Symm60HE-pogo16-tent-cradle.step").relative_to(ROOT))


main()
