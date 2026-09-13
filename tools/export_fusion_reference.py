#!/usr/bin/env python3
"""Build the complete Symm60HE in-case mechanical reference assembly.

The plate is the datum for each gasket-mounted half. Its Hall PCB, switches,
keycaps, direct target connector and floating FFC-to-pogo head all receive the
same mirrored tent/typing transform. The controller remains flat beneath the
centre blocker. Fusion therefore imports one coherent mechanism.
"""
from pathlib import Path
import json
import math
import shutil

import FreeCAD as App
import Import
import Mesh
import Part

from geom import KEYS, U
from pogo_connector_models import (
    BOARD_SPACING, SPRING_WORKING_HEIGHT, TARGET_PROJECTION,
    spring_connector, spring_motion_envelope, target_connector,
)

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
    result = max(shapes, key=lambda shape: abs(shape.Volume)).copy()
    App.closeDocument(temp.Name)
    return result


def solid_from_stl(path):
    mesh = Mesh.Mesh(str(path))
    shape = Part.Shape()
    shape.makeShapeFromMesh(mesh.Topology, 0.02)
    solids = [Part.makeSolid(shell) for shell in shape.Shells]
    solids = [solid for solid in solids
              if not solid.isNull() and solid.Volume > 1e-5]
    if not solids:
        raise RuntimeError(f"STL conversion produced no solid: {path}")
    return Part.makeCompound(solids).removeSplitter()


def align_xy(shape, desired_centre, mirror_y=False, bottom_z=None):
    """Convert KiCad Y-up STEP coordinates while preserving native X/Y.

    PCB STEP and plate DXF geometry are already authored on the same absolute
    datum.  Independently centring their irregular outlines misaligns them.
    ``desired_centre`` remains in the signature for explicit call-site intent.
    """
    result = shape.copy()
    if mirror_y:
        result.rotate(App.Vector(), App.Vector(1, 0, 0), 180)
    bb = result.BoundBox
    dz = 0 if bottom_z is None else bottom_z - bb.ZMin
    result.translate(App.Vector(0, 0, dz))
    return result


def exact_board_thickness(shape, bottom_z, thickness):
    """Normalize KiCad's board-only solid to the specified finished thickness."""
    result = shape.copy()
    current = result.BoundBox.ZLength
    if current <= 0:
        raise RuntimeError("board STEP has no measurable thickness")
    result.translate(App.Vector(0, 0, -bottom_z))
    matrix = App.Matrix()
    matrix.A33 = thickness / current
    result = result.transformGeometry(matrix)
    result.translate(App.Vector(0, 0, bottom_z))
    if not result.isValid():
        raise RuntimeError("board thickness normalization produced invalid geometry")
    return result


def place_wing(shape, layout, side):
    result = shape.copy()
    pivot = App.Vector(layout["axis_x"], layout["front_y"], 0)
    # Y=0 is the rear row and front_y is the front edge. Negative X rotation
    # raises the rear and leaves the front datum low, the normal typing slope.
    result.rotate(pivot, App.Vector(1, 0, 0), -layout["typing_deg"])
    result.rotate(pivot, App.Vector(0, 1, 0),
                  -layout["tent_deg"] if side == "left"
                  else layout["tent_deg"])
    return result


def transform_wing_point(point, layout, side):
    pivot = App.Vector(layout["axis_x"], layout["front_y"], 0)
    local = point.sub(pivot)
    rx = App.Rotation(App.Vector(1, 0, 0), -layout["typing_deg"])
    ry = App.Rotation(App.Vector(0, 1, 0),
                      -layout["tent_deg"] if side == "left"
                      else layout["tent_deg"])
    return pivot.add(ry.multVec(rx.multVec(local)))


def centred_box(width, depth, height, z):
    return Part.makeBox(width, depth, height,
                        App.Vector(-width / 2, -depth / 2, z))


def at_key(shape, key):
    result = shape.copy()
    result.rotate(App.Vector(), App.Vector(0, 0, 1), key["rot"])
    result.translate(App.Vector(key["cx"] * U, key["cy"] * U, 0))
    return result


def switch_shape(key):
    housing = centred_box(13.8, 13.8, 5.8, -2.2)
    stem_a = centred_box(4.2, 1.3, 4.2, 3.6)
    stem_b = centred_box(1.3, 4.2, 4.2, 3.6)
    return at_key(Part.makeCompound([housing, stem_a, stem_b]), key)


def rectangle_wire(width, depth, z):
    pts = [App.Vector(-width/2, -depth/2, z),
           App.Vector(width/2, -depth/2, z),
           App.Vector(width/2, depth/2, z),
           App.Vector(-width/2, depth/2, z)]
    return Part.makePolygon(pts + [pts[0]])


def keycap_shape(key):
    lower_w = max(12.0, key["w"] * U - 1.0)
    cap = Part.makeLoft([rectangle_wire(lower_w, U - 1.0, 6.4),
                         rectangle_wire(max(10.0, lower_w - 3.0),
                                        U - 4.0, 15.4)], True)
    return at_key(cap, key)


def rotate_xy(shape, centre, angle):
    result = shape.copy()
    result.rotate(App.Vector(centre[0], centre[1], 0),
                  App.Vector(0, 0, 1), angle)
    return result


def ribbon_segment(start, end, width=12.5, thickness=0.30):
    vector = end.sub(start)
    if vector.Length < 0.01:
        return Part.Shape()
    shape = Part.makeBox(vector.Length, width, thickness,
                         App.Vector(0, -width / 2, -thickness / 2))
    shape.Placement = App.Placement(
        start, App.Rotation(App.Vector(1, 0, 0), vector))
    return shape


def ribbon_path(points):
    return Part.makeCompound([ribbon_segment(a, b)
                              for a, b in zip(points, points[1:])])


def add_reference(doc, root, internal, label, shape, role, colour,
                  transparency=0):
    obj = doc.addObject("PartDesign::Feature", internal)
    obj.Label = label
    obj.Shape = shape
    obj.addProperty("App::PropertyString", "Role", "Reference")
    obj.Role = role
    obj.addProperty("App::PropertyString", "SuggestedColour", "Reference")
    obj.SuggestedColour = "%.3f, %.3f, %.3f" % colour
    obj.addProperty("App::PropertyInteger", "SuggestedTransparency",
                    "Reference")
    obj.SuggestedTransparency = transparency
    root.addObject(obj)
    return obj


def controller_point(source, layout):
    mech = layout["mechanism"]
    sx, sy = mech["controller_source_centre"]
    dx, dy = source[0] - sx, source[1] - sy
    angle = math.radians(mech["controller_rotation_deg"])
    return App.Vector(
        mech["controller_centre"][0] + dx*math.cos(angle) - dy*math.sin(angle),
        mech["controller_centre"][1] + dx*math.sin(angle) + dy*math.cos(angle),
        mech["controller_bottom_z"] + mech["board_thickness"])


def main():
    layout = json.loads((GEN / "reference-layout.json").read_text())
    mech = layout["mechanism"]
    doc = App.newDocument("Symm60HE_Case_Reference_Assembly")
    root = doc.addObject("App::Part", "Symm60HECaseReferenceAssembly")
    root.Label = "Symm60HE in-case reference assembly"
    objects = []

    for internal, label, filename, side, bottom, is_step in (
        ("LeftPCB", "Left Hall PCB (1.2 mm)", "LeftPCB.step", "left", layout["pcb_z"], True),
        ("RightPCB", "Right Hall PCB (1.2 mm)", "RightPCB.step", "right", layout["pcb_z"], True),
        ("LeftPlate", "Left gasket plate", "LeftPlate.stl", "left", layout["plate_z"], False),
        ("RightPlate", "Right gasket plate", "RightPlate.stl", "right", layout["plate_z"], False),
    ):
        raw = import_step_shape(GEN / filename) if is_step else solid_from_stl(GEN / filename)
        aligned = align_xy(raw, layout[internal]["centre"], mirror_y=is_step,
                           bottom_z=bottom)
        if is_step:
            aligned = exact_board_thickness(
                aligned, bottom, mech["board_thickness"])
        obj = add_reference(doc, root, internal, label,
                            place_wing(aligned, layout, side),
                            "moving Hall PCB" if is_step else "plate datum",
                            (0.10, 0.34, 0.17) if is_step else (0.68, 0.70, 0.73),
                            0 if is_step else 15)
        objects.append(obj)
        Import.export([obj], str(OUT / f"Symm60HE-{internal}.step"))

    selected = [key for key in KEYS if layout["visual_layout"] in key["builds"]]
    for side_name, side_code in (("Left", "L"), ("Right", "R")):
        keys = [key for key in selected if key["half"] == side_code]
        for kind, shape, role, colour, alpha in (
            ("Switches", Part.makeCompound([switch_shape(k) for k in keys]),
             "simplified switch envelopes", (0.18, 0.18, 0.20), 15),
            ("Keycaps", Part.makeCompound([keycap_shape(k) for k in keys]),
             "simplified keycap envelopes", (0.83, 0.84, 0.80), 25),
        ):
            shape.translate(App.Vector(0, 0, layout["plate_z"]))
            obj = add_reference(doc, root, side_name + kind,
                                side_name + " " + kind.lower(),
                                place_wing(shape, layout, side_name.lower()),
                                role, colour, alpha)
            objects.append(obj)
            Import.export([obj], str(OUT / f"Symm60HE-{side_name}{kind}.step"))

    # The controller is rigidly case-mounted and flat under the blocker.  Its
    # native 57 mm axis runs left-to-right so J1 faces the rear case wall and
    # J2/J3 face their respective keyboard halves.
    controller = align_xy(import_step_shape(GEN / "DaughterboardPCB.step"),
                          mech["controller_source_centre"], mirror_y=True,
                          bottom_z=mech["controller_bottom_z"])
    controller = exact_board_thickness(
        controller, mech["controller_bottom_z"], mech["board_thickness"])
    controller = rotate_xy(controller, mech["controller_source_centre"],
                           mech["controller_rotation_deg"])
    cc, sc = mech["controller_centre"], mech["controller_source_centre"]
    controller.translate(App.Vector(cc[0]-sc[0], cc[1]-sc[1], 0))
    controller_obj = add_reference(
        doc, root, "DaughterboardPCB", "Flat central controller daughterboard",
        controller, "rigid case-mounted controller PCB", (0.08, 0.27, 0.13))
    objects.append(controller_obj)
    Import.export([controller_obj], str(OUT / "Symm60HE-DaughterboardPCB.step"))

    # Include the USB-C shell and a conservative external plug/cable keepout.
    # The source PCB's rear edge is the minimum-Y edge.  Transform both the
    # receptacle and edge datum through the same controller placement instead
    # of guessing an assembly-space direction.
    usb_point = controller_point(mech["controller_usb"], layout)
    usb_angle = (mech["controller_usb_rotation_deg"] +
                 mech["controller_rotation_deg"])
    usb_shell = centred_box(9.4, 7.3, 3.3, usb_point.z)
    usb_shell.rotate(App.Vector(), App.Vector(0, 0, 1), usb_angle)
    usb_shell.translate(App.Vector(usb_point.x, usb_point.y, 0))
    usb_obj = add_reference(
        doc, root, "ControllerUSBConnector", "Rear-facing USB-C connector",
        usb_shell, "USB-C receptacle case-opening datum", (0.62, 0.64, 0.67))
    objects.append(usb_obj)

    rear_source = [mech["controller_usb"][0],
                   layout["DaughterboardPCB"]["bounds"][1]]
    rear_edge = controller_point(rear_source, layout)
    outward = rear_edge.sub(usb_point)
    if outward.Length < 0.1:
        raise RuntimeError("USB rear-edge direction is undefined")
    scale = 1.0 / outward.Length
    outward = App.Vector(outward.x * scale, outward.y * scale,
                         outward.z * scale)
    plug_start = App.Vector(rear_edge.x, rear_edge.y, usb_point.z + 1.65)
    plug_end = App.Vector(plug_start.x + outward.x * 18.0,
                         plug_start.y + outward.y * 18.0,
                         plug_start.z + outward.z * 18.0)
    usb_keepout = ribbon_segment(plug_start, plug_end, width=12.0,
                                 thickness=8.0)
    usb_keepout_obj = add_reference(
        doc, root, "ControllerUSBPlugEnvelope", "USB-C plug and cable keepout",
        usb_keepout, "reserve through the rear case wall", (0.62, 0.72, 0.82), 65)
    objects.append(usb_keepout_obj)

    spring_surface = layout["pcb_z"] - BOARD_SPACING
    spring_bottom = spring_surface - mech["board_thickness"]
    target_face = layout["pcb_z"] - TARGET_PROJECTION
    cable_endpoints = {}
    for side in ("left", "right"):
        cap = side.title()
        target = mech[side + "_target"]
        angle = mech[side + "_target_rotation_deg"]
        board_angle = mech["spring_board_rotation_deg"]
        board_centre = target
        source_centre = mech["spring_board_source_centre"]
        board = align_xy(import_step_shape(GEN / f"{cap}SpringPCB.step"),
                         source_centre, mirror_y=True, bottom_z=spring_bottom)
        board = exact_board_thickness(
            board, spring_bottom, mech["board_thickness"])
        board = rotate_xy(board, source_centre, board_angle)
        board.translate(App.Vector(board_centre[0]-source_centre[0],
                                   board_centre[1]-source_centre[1], 0))
        board = place_wing(board, layout, side)
        board_obj = add_reference(doc, root, cap + "SpringPCB",
                                  cap + " floating FFC-to-pogo PCB",
                                  board, "loosely captured floating pogo head",
                                  (0.12, 0.42, 0.20))
        objects.append(board_obj)
        Import.export([board_obj], str(OUT / f"Symm60HE-{cap}SpringPCB.step"))

        target_shape = target_connector(target_face, TARGET_PROJECTION)
        target_shape.rotate(App.Vector(), App.Vector(0, 0, 1), angle)
        target_shape.translate(App.Vector(target[0], target[1], 0))
        target_shape = place_wing(target_shape, layout, side)
        target_obj = add_reference(doc, root, cap + "TargetConnector",
                                   cap + " Hall-PCB target connector",
                                   target_shape, "Mill-Max 856 target",
                                   (0.84, 0.67, 0.18))
        objects.append(target_obj)

        spring_shape = spring_connector(spring_surface, SPRING_WORKING_HEIGHT)
        spring_shape.rotate(App.Vector(), App.Vector(0, 0, 1), angle)
        spring_shape.translate(App.Vector(target[0], target[1], 0))
        spring_shape = place_wing(spring_shape, layout, side)
        spring_obj = add_reference(doc, root, cap + "SpringConnector",
                                   cap + " spring pogo connector",
                                   spring_shape, "Mill-Max 854 spring block",
                                   (0.86, 0.55, 0.12))
        objects.append(spring_obj)

        envelope = spring_motion_envelope(spring_surface)
        envelope.rotate(App.Vector(), App.Vector(0, 0, 1), angle)
        envelope.translate(App.Vector(target[0], target[1], 0))
        env_obj = add_reference(doc, root, cap + "PogoTravelEnvelope",
                                cap + " pogo travel keepout",
                                place_wing(envelope, layout, side),
                                "do not intrude into pogo stroke",
                                (0.95, 0.25, 0.15), 75)
        objects.append(env_obj)

        # JF1 is directly behind PS1 on B.Cu. Include its physical connector
        # body explicitly and begin the flexible-cable envelope at its mouth.
        spring_ffc = centred_box(14.1, 4.9, 2.0, spring_bottom - 2.0)
        spring_ffc.rotate(App.Vector(), App.Vector(0, 0, 1), board_angle)
        spring_ffc.translate(App.Vector(target[0], target[1], 0))
        spring_ffc_obj = add_reference(
            doc, root, cap + "SpringFFCConnector",
            cap + " floating-head FFC connector",
            place_wing(spring_ffc, layout, side),
            "B.Cu 12-way ZIF connector envelope", (0.12, 0.12, 0.14))
        objects.append(spring_ffc_obj)

        rad = math.radians(board_angle)
        entry_offset = 3.5
        ffc_dx = -entry_offset * math.sin(rad)
        ffc_dy = entry_offset * math.cos(rad)
        ffc_local = App.Vector(target[0] + ffc_dx,
                               target[1] + ffc_dy,
                               spring_bottom - 1.0)
        cable_endpoints[side] = transform_wing_point(ffc_local, layout, side)

    # Model the controller ZIF envelopes and flexible FFC reserved volumes.
    for side, source in (("left", mech["controller_left_ffc"]),
                         ("right", mech["controller_right_ffc"])):
        start, end = cable_endpoints[side], controller_point(source, layout)
        # J2/J3 are F.Cu parts, so the envelope begins at the controller's
        # finished top surface.  Do not bury half the connector in the PCB.
        mouth = centred_box(14.0, 5.0, 2.0, end.z)
        # Use the real J2/J3 footprint angle plus the controller transform.
        # The previous fixed 90 degree angle disagreed with the rotated PCB.
        mouth_angle = (mech[f"controller_{side}_ffc_rotation_deg"] +
                       mech["controller_rotation_deg"])
        mouth.rotate(App.Vector(), App.Vector(0, 0, 1), mouth_angle)
        mouth.translate(App.Vector(end.x, end.y, 0))
        mouth_obj = add_reference(doc, root, side.title()+"ControllerFFC",
                                  side.title()+" controller FFC connector",
                                  mouth, "controller ZIF envelope",
                                  (0.15, 0.15, 0.16))
        objects.append(mouth_obj)
        # With the controller restored left-to-right, route each illustrative
        # cable toward its own side instead of making a fore/aft S-turn.
        direction = -1 if side == "left" else 1
        mid1 = App.Vector(start.x + direction * 7.0, start.y,
                          start.z - 1.5)
        mid2 = App.Vector(end.x - direction * 7.0, end.y,
                          end.z + 1.0)
        cable_obj = add_reference(
            doc, root, side.title()+"FFCEnvelope",
            side.title()+" flexible FFC route",
            ribbon_path([start, mid1, mid2, end]),
            "12-way FFC bend and clearance reference",
            (0.15, 0.72, 0.82), 30)
        objects.append(cable_obj)

    doc.recompute()
    # Meshes are generated solely for the checked documentation preview. STEP
    # and FCStd remain the authoritative Fusion handoff formats.
    for obj in objects:
        Mesh.export([obj], str(GEN / ("CaseRef-" + obj.Name + ".stl")))
    master = OUT / "Symm60HE-case-reference-assembly.step"
    legacy = OUT / "Symm60HE-reference-assembly.step"
    Import.export(objects, str(master))
    Import.export(objects, str(legacy))
    source = OUT / "Symm60HE-case-reference-assembly.FCStd"
    legacy_source = OUT / "Symm60HE-reference-assembly.FCStd"
    for path in (source, legacy_source):
        if path.exists():
            path.unlink()
    doc.saveAs(str(source))
    shutil.copy2(source, legacy_source)
    print("wrote", master)
    print("pogo board spacing", BOARD_SPACING,
          "mm; working spring height", SPRING_WORKING_HEIGHT, "mm")


main()
