#!/usr/bin/env python3
"""Create a Fusion-ready example mount for the Neo pogo electronics.

Run with FreeCAD's bundled ``freecadcmd``.  The STEP output contains separate
named solids for the rigid controller, floating spring heads, direct target
datums, FFC route envelopes, tray, capture lips, compliant supports and hard
stops.  It is a case-design reference, not a printable finished enclosure.
"""
from pathlib import Path
import hashlib
import json
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
OUT = ROOT / "case/fusion360/pogo-neo-mounting-reference"
GEN = OUT / "generated"

TENT_DEG = 3.0
CONTROLLER = (28.0, 57.0, 1.2)
SPRING_BOARD = (20.0, 20.0, 1.2)
HALL_DATUM = (32.0, 32.0, 1.2)
TRAY_FLOOR = 1.2
PCB_CLEARANCE_XY = 0.4
BOARD_TO_BOARD = 6.0
WING_X = 40.0
SPRING_MPN = "854-22-012-30-004101"
TARGET_MPN = "856-10-012-30-051000"


def cbox(width, depth, height, z=0.0):
    return Part.makeBox(width, depth, height,
                        App.Vector(-width / 2, -depth / 2, z))


def moved(shape, x=0.0, y=0.0, z=0.0):
    result = shape.copy()
    result.translate(App.Vector(x, y, z))
    return result


def side_angle(side):
    return -TENT_DEG if side == "Left" else TENT_DEG


def side_place(shape, side):
    result = shape.copy()
    result.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), side_angle(side))
    result.translate(App.Vector(-WING_X if side == "Left" else WING_X, 0, 0))
    return result


def side_point(point, side):
    vector = App.Vector(*point)
    vector = App.Rotation(App.Vector(0, 1, 0), side_angle(side)).multVec(vector)
    vector.x += -WING_X if side == "Left" else WING_X
    return vector


def tray(outer_w, outer_d, pocket_w, pocket_d, height=3.4):
    outer = cbox(outer_w, outer_d, height)
    pocket = cbox(pocket_w, pocket_d, height - TRAY_FLOOR + 0.2, TRAY_FLOOR)
    return outer.cut(pocket)


def cable_segment(start, end, width=13.0, thickness=0.30):
    delta = end.sub(start)
    length = delta.Length
    if length < 1e-6:
        raise ValueError("zero-length cable segment")
    body = Part.makeBox(length, width, thickness,
                        App.Vector(0, -width / 2, -thickness / 2))
    body.Placement = App.Placement(start,
                                  App.Rotation(App.Vector(1, 0, 0), delta))
    return body


def cable_path(points):
    return Part.makeCompound([
        cable_segment(start, end) for start, end in zip(points, points[1:])
    ])


def add(doc, group, name, label, shape, role, material, colour,
        transparency=0, dnp=False):
    obj = doc.addObject("PartDesign::Feature", name)
    obj.Label = label
    obj.Shape = shape.removeSplitter()
    obj.addProperty("App::PropertyString", "Role", "Reference")
    obj.Role = role
    obj.addProperty("App::PropertyString", "Material", "Reference")
    obj.Material = material
    obj.addProperty("App::PropertyString", "SuggestedColour", "Reference")
    obj.SuggestedColour = "%.3f, %.3f, %.3f" % colour
    obj.addProperty("App::PropertyInteger", "SuggestedTransparency", "Reference")
    obj.SuggestedTransparency = transparency
    obj.addProperty("App::PropertyBool", "DNP", "Reference")
    obj.DNP = dnp
    group.addObject(obj)
    return obj


def controller_board_shape():
    board = cbox(*CONTROLLER)
    # The current controller has two M2 NPTH holes.  Their transformed centres
    # are x=+11 mm and y=+/-24 mm when the 57 mm dimension is lengthwise.
    for y in (-24.0, 24.0):
        board = board.cut(Part.makeCylinder(
            1.1, CONTROLLER[2] + 0.4, App.Vector(11.0, y, -0.2)))
    return board


def controller_tray_shape():
    support = tray(32.0, 61.0, 28.8, 57.8)
    # Two bosses use the PCB's actual holes.  Two opposite-side edge ledges
    # prevent rocking without adding unsupported holes to the board.
    bosses = []
    for y in (-24.0, 24.0):
        boss = Part.makeCylinder(2.7, TRAY_FLOOR + 0.2,
                                 App.Vector(11.0, y, 0))
        boss = boss.cut(Part.makeCylinder(0.9, TRAY_FLOOR + 0.4,
                                          App.Vector(11.0, y, -0.1)))
        bosses.append(boss)
    return support.fuse(Part.makeCompound(bosses)).removeSplitter()


def bridge(side):
    sign = -1 if side == "Left" else 1
    inner = sign * 16.0
    outer = sign * 28.0
    x0, x1 = sorted((inner, outer))
    rise = math.tan(math.radians(TENT_DEG)) * (x1 - x0)
    if side == "Left":
        points = [(x0, rise), (x1, 0), (x1, 2.2), (x0, rise + 2.2)]
    else:
        points = [(x0, 0), (x1, rise), (x1, rise + 2.2), (x0, 2.2)]
    wire = Part.makePolygon([App.Vector(x, -2.0, z) for x, z in points] +
                            [App.Vector(points[0][0], -2.0, points[0][1])])
    rib = Part.Face(wire).extrude(App.Vector(0, 4.0, 0))
    return Part.makeCompound([moved(rib, y=-10), moved(rib, y=10)])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    GEN.mkdir(parents=True, exist_ok=True)
    doc = App.newDocument("Symm60HE_Neo_Pogo_Mounting_Reference")
    root = doc.addObject("App::Part", "MountingReference")
    root.Label = "Symm60HE Neo pogo case-design mounting reference"
    objects = []

    controller_group = doc.addObject("App::Part", "ControllerMount")
    controller_group.Label = "Rigid controller mount"
    root.addObject(controller_group)
    controller_z = TRAY_FLOOR + 0.2
    objects.append(add(
        doc, controller_group, "ControllerTray", "Controller support tray",
        controller_tray_shape(),
        "Example 1.2 mm floor with 0.4 mm XY PCB clearance",
        "PA12-CF, PETG, or machined polymer", (0.28, 0.46, 0.66)))
    objects.append(add(
        doc, controller_group, "ControllerPCB", "57 x 28 mm controller PCB",
        moved(controller_board_shape(), z=controller_z),
        "Rigid MCU daughterboard reference; 57 mm dimension runs fore-aft",
        "1.2 mm FR-4", (0.05, 0.34, 0.18)))

    # M2 screw and washer envelopes through the two real controller holes.
    screws = []
    washers = []
    for y in (-24.0, 24.0):
        screws.append(Part.makeCylinder(
            1.0, 5.2, App.Vector(11.0, y, 0.2)))
        washers.append(Part.makeCylinder(
            2.2, 0.6, App.Vector(11.0, y,
                                controller_z + CONTROLLER[2])))
    objects.append(add(
        doc, controller_group, "ControllerM2Hardware",
        "Controller M2 screw envelopes",
        Part.makeCompound(screws + washers),
        "Two M2 fasteners through the existing NPTH holes; do not clamp hard",
        "M2 hardware", (0.68, 0.70, 0.73)))

    # Low edge ledges on the hole-free side stop the two-hole board rocking.
    ledges = Part.makeCompound([
        moved(cbox(5.0, 8.0, 1.0), x=-14.6, y=y,
              z=controller_z + CONTROLLER[2] - 0.2)
        for y in (-18.0, 18.0)
    ])
    objects.append(add(
        doc, controller_group, "ControllerAntiRockLedges",
        "Controller anti-rock edge ledges", ledges,
        "Two removable or compliant perimeter ledges; no added PCB holes",
        "Printed polymer", (0.36, 0.48, 0.72)))

    spring_surface = TRAY_FLOOR + 0.2 + SPRING_BOARD[2]
    target_board_bottom = spring_surface + BOARD_TO_BOARD
    ffc_paths = []
    for side in ("Left", "Right"):
        group = doc.addObject("App::Part", side + "FloatingPogoMount")
        group.Label = side + " floating pogo mount"
        root.addObject(group)

        carrier_raw = tray(24.0, 24.0, 20.0 + 2 * PCB_CLEARANCE_XY,
                           20.0 + 2 * PCB_CLEARANCE_XY)
        # Cable exit faces the controller.
        exit_x = 10.8 if side == "Left" else -10.8
        carrier_raw = carrier_raw.cut(
            moved(cbox(4.0, 12.0, 2.8), x=exit_x, z=0.9))
        carrier = side_place(carrier_raw, side)
        objects.append(add(
            doc, group, side + "Carrier", side + " floating-head carrier",
            carrier,
            "20.8 mm pocket: 0.4 mm X/Y clearance around 20 mm PCB",
            "PA12-CF, PETG, or machined polymer", (0.28, 0.46, 0.66)))

        spring_pcb_raw = moved(cbox(*SPRING_BOARD), z=controller_z)
        objects.append(add(
            doc, group, side + "SpringPCB", side + " 20 x 20 mm spring PCB",
            side_place(spring_pcb_raw, side),
            "Floating FFC-to-pogo PCB; retained without rigid clamping",
            "1.2 mm FR-4", (0.05, 0.34, 0.18)))

        spring_raw = moved(spring_connector(
            spring_surface, SPRING_WORKING_HEIGHT), y=-2.0)
        objects.append(add(
            doc, group, side + "SpringConnector",
            side + " Mill-Max spring connector",
            side_place(spring_raw, side),
            SPRING_MPN + " dimensioned compressed working model",
            "Nylon and brass", (0.82, 0.60, 0.18)))

        travel_raw = moved(spring_motion_envelope(spring_surface), y=-2.0)
        objects.append(add(
            doc, group, side + "SpringTravelEnvelope",
            side + " pogo maximum-extension envelope",
            side_place(travel_raw, side),
            "Reserve the complete 4.216 mm initial-height swept volume",
            "Mechanical keep-out", (0.95, 0.55, 0.16), transparency=75))

        target_raw = moved(target_connector(
            target_board_bottom - TARGET_PROJECTION, TARGET_PROJECTION),
            y=-2.0)
        objects.append(add(
            doc, group, side + "TargetConnector",
            side + " direct Hall-PCB target",
            side_place(target_raw, side),
            TARGET_MPN + " mounted directly on the Hall PCB",
            "Thermoplastic and brass", (0.82, 0.60, 0.18)))

        hall_raw = moved(cbox(*HALL_DATUM), z=target_board_bottom)
        objects.append(add(
            doc, group, side + "HallPCBDatum",
            side + " Hall-PCB local datum",
            side_place(hall_raw, side),
            "Local reference only; replace with the full keyboard PCB in the case",
            "1.2 mm FR-4", (0.10, 0.48, 0.26), transparency=45))

        # Four Poron islands support the spring head without clamping it.
        poron_raw = Part.makeCompound([
            moved(cbox(4.0, 4.0, 0.8), x=x, y=y,
                  z=controller_z - 0.6)
            for x, y in ((-7.0, -6.0), (7.0, -6.0),
                         (-7.0, 6.0), (7.0, 6.0))
        ])
        objects.append(add(
            doc, group, side + "PoronSupports", side + " Poron supports",
            side_place(poron_raw, side),
            "0.8 mm compliant supports under the floating spring PCB",
            "Poron 4701-30", (0.12, 0.12, 0.14)))

        # Small capture lips overlap only the PCB perimeter.
        lips_raw = Part.makeCompound([
            moved(cbox(5.0, 1.6, 0.8), x=x, y=y,
                  z=controller_z + SPRING_BOARD[2] + 0.6)
            for x in (-7.0, 7.0) for y in (-10.5, 10.5)
        ])
        objects.append(add(
            doc, group, side + "CaptureLips", side + " capture lips",
            side_place(lips_raw, side),
            "Retain the PCB perimeter while preserving X/Y and small Z motion",
            "Printed polymer", (0.36, 0.48, 0.72)))

        # Four narrow hard stops define the 6 mm PCB spacing.  Keep their Hall
        # PCB contact patches out of every sensor and copper-critical region.
        stops_raw = Part.makeCompound([
            Part.makeCylinder(1.2, BOARD_TO_BOARD,
                              App.Vector(x, y, spring_surface))
            for x, y in ((-8.0, -7.0), (8.0, -7.0),
                         (-8.0, 7.0), (8.0, 7.0))
        ])
        objects.append(add(
            doc, group, side + "CompressionStops",
            side + " compression-stop envelopes",
            side_place(stops_raw, side),
            "Optional 2.4 mm diameter stops defining 6.0 mm PCB spacing",
            "POM or printed polymer", (0.85, 0.86, 0.88)))

        # Connector envelope on the spring PCB and the illustrative FFC route.
        ffc_connector_raw = moved(cbox(14.1, 4.9, 2.8), y=5.5,
                                  z=spring_surface)
        objects.append(add(
            doc, group, side + "SpringFFCConnector",
            side + " spring-board FFC connector",
            side_place(ffc_connector_raw, side),
            "12-way 1.0 mm top-contact connector envelope",
            "LCP and copper", (0.18, 0.44, 0.72)))

        wing_end = side_point((0.0, 8.0, spring_surface + 2.0), side)
        if side == "Left":
            controller_end = App.Vector(-2.0, -25.7,
                                        controller_z + CONTROLLER[2] + 2.0)
            middle = App.Vector(-21.0, -15.0, max(controller_end.z, wing_end.z) + 2.0)
        else:
            controller_end = App.Vector(-2.0, 25.7,
                                        controller_z + CONTROLLER[2] + 2.0)
            middle = App.Vector(21.0, 15.0, max(controller_end.z, wing_end.z) + 2.0)
        ffc_paths.append((side, [controller_end, middle, wing_end]))

        objects.append(add(
            doc, root, side + "BridgeRibs", side + " fixed-angle bridge ribs",
            bridge(side),
            "Example structural bridge; keep clear of gasket-loaded plate motion",
            "PA12-CF, PETG, or machined polymer", (0.28, 0.46, 0.66)))

    for side, points in ffc_paths:
        objects.append(add(
            doc, root, side + "FFCEnvelope", side + " flexible FFC route envelope",
            cable_path(points),
            "Illustrative slack route only; preserve bend radius and service loop",
            "0.3 mm 12-way FFC", (0.20, 0.55, 0.90), transparency=25))

    doc.recompute()
    for obj in objects:
        if obj.Shape.isNull() or not obj.Shape.isValid():
            raise RuntimeError(f"invalid reference body: {obj.Name}")

    fcstd = OUT / "Symm60HE-Neo-Pogo-Mounting-Reference.FCStd"
    assembled = OUT / "Symm60HE-Neo-Pogo-Mounting-Reference.step"
    if fcstd.exists():
        fcstd.unlink()
    doc.saveAs(str(fcstd))
    Import.export(objects, str(assembled))

    # Export every solid independently so Fusion users can replace, hide or
    # derive against individual parts even if their STEP import settings flatten
    # the main assembly hierarchy.
    for obj in objects:
        Import.export([obj], str(GEN / f"{obj.Name}.step"))
        Mesh.export([obj], str(GEN / f"{obj.Name}.stl"))

    # A second, exploded STEP makes each interface readable before enclosure
    # work starts.  The source document remains the assembled configuration.
    exploded_doc = App.newDocument("Symm60HE_Neo_Pogo_Mounting_Exploded")
    exploded_objects = []
    for obj in objects:
        copy = exploded_doc.addObject("PartDesign::Feature", obj.Name + "Exploded")
        copy.Label = obj.Label + " (exploded)"
        shape = obj.Shape.copy()
        dz = 0.0
        if "HallPCBDatum" in obj.Name:
            dz = 12.0
        elif "TargetConnector" in obj.Name:
            dz = 8.0
        elif "SpringTravelEnvelope" in obj.Name:
            dz = 2.0
        elif "CaptureLips" in obj.Name or "CompressionStops" in obj.Name:
            dz = 4.0
        shape.translate(App.Vector(0, 0, dz))
        copy.Shape = shape
        exploded_objects.append(copy)
    exploded_doc.recompute()
    exploded = OUT / "Symm60HE-Neo-Pogo-Mounting-Reference-Exploded.step"
    Import.export(exploded_objects, str(exploded))

    manifest = {
        "status": "case-design reference; prototype before production",
        "tent_angle_deg": TENT_DEG,
        "controller_pcb_mm": list(CONTROLLER),
        "spring_pcb_mm": list(SPRING_BOARD),
        "hall_pcb_thickness_mm": HALL_DATUM[2],
        "spring_pocket_mm": [20.0 + 2 * PCB_CLEARANCE_XY] * 2,
        "spring_pcb_xy_clearance_per_side_mm": PCB_CLEARANCE_XY,
        "spring_to_target_pcb_spacing_mm": BOARD_TO_BOARD,
        "pogo_spring_mpn": SPRING_MPN,
        "pogo_target_mpn": TARGET_MPN,
        "pogo_contacts": CONTACTS,
        "pogo_pitch_mm": PITCH,
        "pogo_body_mm": [BODY_LENGTH, BODY_DEPTH],
        "pogo_spring_initial_height_mm": SPRING_INITIAL_HEIGHT,
        "pogo_spring_stroke_mm": SPRING_STROKE,
        "pogo_spring_working_height_mm": SPRING_WORKING_HEIGHT,
        "pogo_target_projection_mm": TARGET_PROJECTION,
        "pogo_model_note": "dimensioned case-design reference, not vendor-certified CAD",
        "tray_floor_mm": TRAY_FLOOR,
        "controller_mount": "two existing M2 NPTH holes plus two compliant opposite-edge ledges",
        "spring_mount": "four Poron supports and four perimeter capture lips; no rigid PCB clamp",
        "target_mount": "target connector soldered directly to Hall PCB",
        "ffc": "two 12-way 1.0 mm same-side cables; shown routes are clearance envelopes",
        "objects": [obj.Name for obj in objects],
        "fusion_handoff": [assembled.name, exploded.name],
    }
    dimensions = OUT / "dimensions.json"
    dimensions.write_text(json.dumps(manifest, indent=2) + "\n")
    readme = OUT / "README.md"
    readme.write_text(
        "# Symm60HE Neo pogo mounting reference for Fusion 360\n\n"
        "Open `Symm60HE-Neo-Pogo-Mounting-Reference.step` in Fusion 360. "
        "The assembly is deliberately made from separately named solids. If "
        "Fusion imports a flat body list, use the matching individual STEP files "
        "under `generated/` to create components. The exploded STEP is provided "
        "only to make the stack and retention order easier to inspect.\n\n"
        "This is an example electronics carrier, not a finished or printable "
        "case. Build the enclosure around the green PCB references and keep the "
        "blue carrier, pale hard-stop, black Poron and cyan FFC envelopes as "
        "reserved volumes. The translucent 32 mm Hall-PCB squares are local "
        "target datums; replace them with the full left/right PCB references.\n\n"
        "The spring and target connector bodies include all twelve contacts at "
        "1.27 mm pitch. The translucent orange spring-travel bodies reserve the "
        "complete 4.216 mm initial-height envelope; do not build case features "
        "inside them. These are dimensioned engineering references rather than "
        "vendor-certified STEP models.\n\n"
        "The controller is rigidly supported on a 1.2 mm floor. Two M2 fastener "
        "envelopes use its existing NPTH holes, while two compliant edge ledges "
        "prevent rocking. Do not bow the controller when tightening it. Each "
        "20 x 20 x 1.2 mm spring PCB floats in a 20.8 mm pocket on four 0.8 mm "
        "Poron pads and is retained only at its perimeter. The direct target "
        "travels with the gasket-mounted Hall PCB. Four small optional stops "
        "protect the pogo contacts from bottoming; relocate their contact patches "
        "as needed to avoid sensors, traces and components.\n\n"
        "The FFC solids are route/clearance examples, not formed-cable drawings. "
        "Keep a service loop, respect the cable supplier's dynamic bend guidance, "
        "and verify the final path at both gasket travel limits. Magnets are not "
        "part of this reference and remain DNP until Hall-offset/noise testing.\n")

    critical = [fcstd, assembled, exploded, dimensions, readme]
    (OUT / "SHA256SUMS.txt").write_text("".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
        for path in critical))
    print(assembled.relative_to(ROOT))
    print(exploded.relative_to(ROOT))
    print(fcstd.relative_to(ROOT))
    print(len(objects), "valid separate reference bodies")


main()
