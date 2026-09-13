#!/usr/bin/env python3
"""Generate the fixed 3-degree pogo/controller tenting module for Fusion 360."""
from pathlib import Path
import json
import hashlib
import math

import FreeCAD as App
import Import
import Mesh
import Part

from pogo_connector_models import (BODY_DEPTH, BODY_LENGTH, CONTACTS, PITCH,
                                   SPRING_INITIAL_HEIGHT, SPRING_STROKE,
                                   SPRING_WORKING_HEIGHT, TARGET_PROJECTION,
                                   spring_connector, spring_motion_envelope,
                                   target_connector)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "case/fusion360/tenting-solution"
GEN = OUT / "generated"

TENT_DEG = 3.0
PCB_T = 1.2
FLOOR_T = 1.2
BOARD_SPACING = 6.0
CENTRE_PCB = (28.0, 57.0)
WING_PCB = (20.0, 20.0)
WING_X = 40.0


def cbox(w, d, h, z=0):
    return Part.makeBox(w, d, h, App.Vector(-w / 2, -d / 2, z))


def moved(shape, x=0, y=0, z=0):
    result = shape.copy()
    result.translate(App.Vector(x, y, z))
    return result


def side_place(shape, side):
    result = shape.copy()
    # Viewed from the front, raise both inner/centre-facing edges: the left
    # wing rotates clockwise and the right wing rotates counter-clockwise.
    angle = -TENT_DEG if side == "Left" else TENT_DEG
    x = -WING_X if side == "Left" else WING_X
    result.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), angle)
    result.translate(App.Vector(x, 0, 0))
    return result


def drilled_bar(width, depth, height, hole_x):
    bar = cbox(width, depth, height)
    for x in hole_x:
        bar = bar.cut(Part.makeCylinder(1.1, height + 0.4,
                                        App.Vector(x, 0, -0.2)))
    return bar


def tray(outer_w, outer_d, pocket_w, pocket_d, height=3.2):
    outer = cbox(outer_w, outer_d, height)
    pocket = cbox(pocket_w, pocket_d, height - FLOOR_T + 0.2, FLOOR_T)
    return outer.cut(pocket)


def add(doc, group, name, label, shape, role, material, dnp=False):
    obj = doc.addObject("PartDesign::Feature", name)
    obj.Label = label
    obj.Shape = shape.removeSplitter()
    obj.addProperty("App::PropertyString", "Role", "Design")
    obj.Role = role
    obj.addProperty("App::PropertyString", "Material", "Design")
    obj.Material = material
    obj.addProperty("App::PropertyBool", "DNP_Until_Hall_Test", "Design")
    obj.DNP_Until_Hall_Test = dnp
    group.addObject(obj)
    return obj


def bridge_shape(side):
    """Two fixed-angle ribs joining the flat centre tray to an angled wing."""
    sign = -1 if side == "Left" else 1
    x_inner = sign * 14.5
    x_outer = sign * 32.0
    if x_inner > x_outer:
        x_inner, x_outer = x_outer, x_inner
    rise = math.tan(math.radians(TENT_DEG)) * (x_outer - x_inner)
    # Cross-section in X/Z, extruded along Y.  The rise direction mirrors.
    if side == "Left":
        pts = [(x_inner, 0), (x_outer, rise), (x_outer, rise + 2.4),
               (x_inner, 2.4)]
    else:
        pts = [(x_inner, rise), (x_outer, 0), (x_outer, 2.4),
               (x_inner, rise + 2.4)]
    wire = Part.makePolygon([App.Vector(x, 0, z) for x, z in pts] +
                            [App.Vector(pts[0][0], 0, pts[0][1])])
    rib = Part.Face(wire).extrude(App.Vector(0, 4.0, 0))
    return Part.makeCompound([moved(rib, y=-12.0), moved(rib, y=8.0)])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    GEN.mkdir(parents=True, exist_ok=True)
    # Do not let removed bodies survive in regenerated previews.
    for stale_mesh in GEN.glob("*.stl"):
        stale_mesh.unlink()
    doc = App.newDocument("Symm60HE_Fixed_Tent_Pogo_Module")
    root = doc.addObject("App::Part", "FixedTentPogoModule")
    root.Label = "Symm60HE fixed 3 degree tenting and pogo module"
    objects = []

    centre_group = doc.addObject("App::Part", "CentralControllerCradle")
    centre_group.Label = "Central controller cradle"
    root.addObject(centre_group)
    centre_tray = tray(32.0, 61.0, 28.4, 57.4)
    # M2 heat-set insert pilots for the four controller edge clamps.
    for x, y in ((-14.4, -24), (14.4, -24), (-14.4, 24), (14.4, 24)):
        centre_tray = centre_tray.cut(
            Part.makeCylinder(1.5, 3.6, App.Vector(x, y, -0.2)))
    # Strain-relieved harness exits; the two bridge ribs leave the centre open.
    centre_tray = centre_tray.cut(moved(cbox(3.0, 10.0, 2.5), x=-15.5, z=1.0))
    centre_tray = centre_tray.cut(moved(cbox(3.0, 10.0, 2.5), x=15.5, z=1.0))
    objects.append(add(doc, centre_group, "CentralTray", "Central printed tray",
                       centre_tray, "Flat controller support and structural spine",
                       "PA12-CF or PETG"))
    controller = moved(cbox(*CENTRE_PCB, PCB_T), z=FLOOR_T + 0.2)
    objects.append(add(doc, centre_group, "ControllerPCB", "Controller PCB reference",
                       controller, "Existing controller rotated lengthwise on kernel centreline", "FR4"))

    # Four board-retaining clamp blocks.  They press only the PCB perimeter.
    clamps = Part.makeCompound([
        moved(drilled_bar(8.0, 3.0, 1.5, (0,)), x=x, y=y,
              z=FLOOR_T + PCB_T + 0.2)
        for x, y in ((-14.4, -24), (14.4, -24), (-14.4, 24), (14.4, 24))
    ])
    objects.append(add(doc, centre_group, "ControllerClamps", "Controller edge clamps",
                       clamps, "Four removable M2 edge clamps", "PA12-CF or PETG"))

    for side in ("Left", "Right"):
        group = doc.addObject("App::Part", side + "Interface")
        group.Label = side + " tented pogo interface"
        root.addObject(group)

        # 20.8 mm pocket gives the 20 mm spring head 0.4 mm controlled X/Y
        # freedom per side, while lips below retain it in the kernel aperture.
        raw_carrier = tray(24.0, 24.0, 20.8, 20.8)
        for x in (-5.0, 5.0):
            for y in (-10.2, 10.2):
                raw_carrier = raw_carrier.cut(
                    Part.makeCylinder(1.5, 3.6, App.Vector(x, y, -0.2)))
        # Open both short sidewalls so the mirrored part can be printed once
        # and the fixed harness can exit toward the controller on either side.
        raw_carrier = raw_carrier.cut(moved(cbox(3.0, 10.0, 2.5), x=-10.5, z=1.0))
        raw_carrier = raw_carrier.cut(moved(cbox(3.0, 10.0, 2.5), x=10.5, z=1.0))
        carrier = side_place(raw_carrier, side)
        objects.append(add(doc, group, side + "WingCarrier", side + " wing carrier",
                           carrier, "Captured 3 degree floating-head aperture", "PA12-CF or PETG"))
        wing = side_place(moved(cbox(*WING_PCB, PCB_T), z=FLOOR_T + 0.2), side)
        objects.append(add(doc, group, side + "WingPCB", side + " spring wing PCB",
                           wing, "Floating 1.2 mm FFC-to-spring module PCB", "FR4"))

        spring_surface = FLOOR_T + 0.2 + PCB_T
        target_surface = spring_surface + BOARD_SPACING
        target_height = TARGET_PROJECTION
        spring = side_place(spring_connector(
            spring_surface, SPRING_WORKING_HEIGHT), side)
        objects.append(add(doc, group, side + "SpringConnector",
                           side + " Mill-Max 854 spring connector",
                           spring, "854-22-012-30-004101 dimensioned working model", "Nylon/brass"))
        objects.append(add(
            doc, group, side + "SpringTravelEnvelope",
            side + " pogo maximum-extension envelope",
            side_place(spring_motion_envelope(spring_surface), side),
            "Reserve the complete 4.216 mm initial-height swept volume",
            "Mechanical keep-out"))

        spring_ffc = side_place(moved(cbox(14.1, 4.9, 2.8), y=5.0,
                                      z=spring_surface), side)
        objects.append(add(doc, group, side + "SpringFFC",
                           side + " controller-to-spring FFC connector",
                           spring_ffc, "12-way flexible link to rigid controller",
                           "LCP/copper"))

        target_model = side_place(target_connector(
            target_surface - target_height, target_height), side)
        objects.append(add(doc, group, side + "TargetConnector",
                           side + " Hall-PCB target interface",
                           target_model, "856-10-012-30-051000 dimensioned target model",
                           "Thermoplastic/brass"))

        guides = Part.makeCompound([
            moved(cbox(1.0, 5.0, BOARD_SPACING), x=-10.5, y=-9.0,
                  z=spring_surface),
            moved(cbox(1.0, 5.0, BOARD_SPACING), x=10.5, y=-9.0,
                  z=spring_surface),
            moved(cbox(1.5, 7.0, BOARD_SPACING), x=10.75, y=8.0,
                  z=spring_surface),
        ])
        objects.append(add(doc, group, side + "GuidePins",
                           side + " asymmetric perimeter keys",
                           side_place(guides, side),
                           "Carrier-wall datum and anti-rotation key; no PCB holes",
                           "POM or printed carrier"))

        stops = Part.makeCompound([
            moved(cbox(2.4, 2.4, BOARD_SPACING), x=x, y=y,
                  z=spring_surface)
            for x, y in ((-8.4, -6.4), (8.4, -6.4),
                         (-8.4, 6.4), (8.4, 6.4))
        ])
        objects.append(add(doc, group, side + "CompressionStops",
                           side + " compression hard stops",
                           side_place(stops, side),
                           "Defines 6.0 mm PCB spacing and prevents bottoming", "POM"))

        capture_lips = Part.makeCompound([
            moved(cbox(6.0, 2.0, 1.0), x=x, y=y,
                  z=FLOOR_T + PCB_T + 0.8)
            for x in (-7.0, 7.0) for y in (-10.5, 10.5)
        ])
        objects.append(add(doc, group, side + "FloatingCaptureLips",
                           side + " floating-head capture lips",
                           side_place(capture_lips, side),
                           "Retains head without clamping; permits gasket-following motion",
                           "PA12-CF or PETG"))

        poron = Part.makeCompound([
            moved(cbox(4.0, 4.0, 0.8), x=x, y=y, z=FLOOR_T - 0.6)
            for x, y in ((-7.0, -6.0), (7.0, -6.0),
                         (-7.0, 6.0), (7.0, 6.0))
        ])
        objects.append(add(doc, group, side + "PoronPads", side + " Poron supports",
                           side_place(poron, side), "0.8 mm compliant wing support",
                           "Poron 4701-30"))

        magnets = Part.makeCompound([
            Part.makeCylinder(2.0, 2.0, App.Vector(0, y, -0.8))
            for y in (-5.5, 5.5)
        ])
        objects.append(add(doc, group, side + "OptionalMagnets",
                           side + " optional magnet envelopes",
                           side_place(magnets, side),
                           "DNP 4x2 N35; retention experiment only", "NdFeB", dnp=True))

        bridge = bridge_shape(side)
        objects.append(add(doc, root, side + "FixedAngleBridge",
                           side + " fixed-angle bridge ribs", bridge,
                           "Printed structural link between controller and wing trays",
                           "PA12-CF or PETG"))

    doc.recompute()
    fcstd = OUT / "Symm60HE-fixed-tent-pogo-module.FCStd"
    if fcstd.exists():
        fcstd.unlink()
    doc.saveAs(str(fcstd))
    Import.export(objects, str(OUT / "Symm60HE-fixed-tent-pogo-module.step"))
    for obj in objects:
        Mesh.export([obj], str(GEN / f"{obj.Name}.stl"))
    manifest = {
        "tent_angle_deg": TENT_DEG,
        "tent_direction": "centre_edges_high",
        "controller_pcb_mm": [*CENTRE_PCB, PCB_T],
        "spring_wing_pcb_mm": [*WING_PCB, PCB_T],
        "board_to_board_mm": BOARD_SPACING,
        "nominal_spring_compression_mm": 0.5,
        "pogo_spring_mpn": "854-22-012-30-004101",
        "pogo_target_mpn": "856-10-012-30-051000",
        "pogo_contacts": CONTACTS,
        "pogo_pitch_mm": PITCH,
        "pogo_body_mm": [BODY_LENGTH, BODY_DEPTH],
        "pogo_spring_initial_height_mm": SPRING_INITIAL_HEIGHT,
        "pogo_spring_stroke_mm": SPRING_STROKE,
        "pogo_spring_working_height_mm": SPRING_WORKING_HEIGHT,
        "pogo_target_projection_mm": TARGET_PROJECTION,
        "pogo_model_note": "dimensioned case-design reference, not vendor-certified CAD",
        "printed_floor_mm": FLOOR_T,
        "primary_retention": "0.4 mm-per-side floating apertures with capture lips",
        "keyboard_suspension": "eight plate-only side pads; no PCB gasket load",
        "target_retention": "12-contact targets mounted directly on Hall PCBs",
        "interconnect": "one short 12-way controller-to-floating-spring FFC per side",
        "optional_magnets": "4x2 mm N35 axial, DNP until Hall test",
        "separate_bodies": [obj.Name for obj in objects],
    }
    dimensions = OUT / "dimensions.json"
    dimensions.write_text(json.dumps(manifest, indent=2) + "\n")
    critical = [fcstd, OUT / "Symm60HE-fixed-tent-pogo-module.step", dimensions]
    (OUT / "SHA256SUMS.txt").write_text("".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
        for path in critical))
    print(fcstd.relative_to(ROOT))
    print((OUT / "Symm60HE-fixed-tent-pogo-module.step").relative_to(ROOT))
    print(len(objects), "separate bodies")


main()
