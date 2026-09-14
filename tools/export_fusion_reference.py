#!/usr/bin/env python3
"""Build the complete Symm60HE in-case mechanical reference assembly.

The plate is the datum for each gasket-mounted half. Its Hall PCB, switches,
keycaps, direct target connector and floating FPC-to-pogo head all receive the
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


def mirror_y_preserve_z(shape):
    """Convert KiCad STEP Y-up coordinates without flipping component height."""
    result = shape.copy()
    # Unlike TopoShape.rotate/translate, TopoShape.mirror returns the mirrored
    # B-rep instead of mutating the receiver.  Ignoring that return value left
    # the Hall packages at negative KiCad Y while their boards were converted
    # to positive assembly Y, making the parts appear suspended below the
    # keyboard in the preview.
    return result.mirror(App.Vector(), App.Vector(0, 1, 0))


def exact_board_thickness(shape, bottom_z, thickness):
    """Re-extrude KiCad's board face to the specified finished thickness.

    A non-uniform B-rep transform silently bridged concave Edge.Cuts features,
    including the USB-C setback.  Extruding the broad planar board face keeps
    every perimeter recess and drilled opening while producing an exact 1.2 mm
    mechanical reference.
    """
    planar = []
    for face in shape.Faces:
        try:
            if abs(face.normalAt(0, 0).z) > 0.99:
                planar.append(face)
        except Exception:
            pass
    if not planar:
        raise RuntimeError("board STEP has no broad planar face")
    face = max(planar, key=lambda candidate: candidate.Area).copy()
    face.translate(App.Vector(0, 0, bottom_z - face.BoundBox.ZMin))
    result = face.extrude(App.Vector(0, 0, thickness))
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


def half_spread_x(layout, side):
    spread = layout["half_spread_mm"]
    return -spread if side == "left" else spread


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


def place_smt_model(path, centre, angle, mounting_z, underside=False):
    """Place an exact, footprint-centred SMT STEP on a board surface.

    The vendored EasyEDA/LCSC connector models use the footprint origin in XY
    but not a guaranteed zero Z datum.  Normalizing their lower face before
    applying the real footprint rotation avoids depending on exporter-specific
    STEP assembly placements.  An underside part is reflected only through the
    board plane so its cable-entry direction remains tied to the footprint.
    """
    result = import_step_shape(path)
    bb = result.BoundBox
    result.translate(App.Vector(-bb.Center.x, -bb.Center.y, -bb.ZMin))
    if underside:
        # A rigid 180 degree Y rotation puts the component below the mounting
        # plane while preserving its cable-entry direction. It also reverses
        # the contact order, matching KiCad's physical B.Cu footprint view.
        # A B-rep mirror left some imported C20111 sub-solids on the wrong side
        # of the board plane in FreeCAD 1.1.3.
        result.rotate(App.Vector(), App.Vector(0, 1, 0), 180)
    result.rotate(App.Vector(), App.Vector(0, 0, 1), angle)
    result.translate(App.Vector(centre[0], centre[1], mounting_z))
    return result


def at_key(shape, key):
    result = shape.copy()
    result.rotate(App.Vector(), App.Vector(0, 0, 1), key["rot"])
    result.translate(App.Vector(key["cx"] * U, key["cy"] * U, 0))
    return result


def switch_shape(key):
    """Product-specific XVX Whisper EC/HE clearance reference.

    XVX does not publish a mechanical CAD file or dimensioned housing drawing.
    Keep the standard 13.8 mm plate-opening body as the controlling envelope,
    then represent the Whisper's visible translucent upper housing, MX stem,
    rubber-dome shoulder and centre magnetic plunger separately.  This is an
    enclosure/visualisation model, not manufacturer CAD.
    """
    lower = centred_box(13.8, 13.8, 3.6, -2.2)
    upper = centred_box(15.6, 15.6, 2.1, 1.5)
    dome = Part.makeCylinder(6.4, 1.5, App.Vector(0, 0, 3.6))
    stem_a = centred_box(4.1, 1.25, 3.8, 5.1)
    stem_b = centred_box(1.25, 4.1, 3.8, 5.1)
    magnet = Part.makeCylinder(2.0, 2.4, App.Vector(0, 0, -4.6))
    return at_key(Part.makeCompound(
        [lower, upper, dome, stem_a, stem_b, magnet]), key)


def rectangle_wire(width, depth, z, tilt_deg=0.0, y_offset=0.0):
    slope = math.tan(math.radians(tilt_deg))
    pts = [App.Vector(-width/2, -depth/2 + y_offset,
                      z - depth/2 * slope),
           App.Vector(width/2, -depth/2 + y_offset,
                      z - depth/2 * slope),
           App.Vector(width/2, depth/2 + y_offset,
                      z + depth/2 * slope),
           App.Vector(-width/2, depth/2 + y_offset,
                      z + depth/2 * slope)]
    return Part.makePolygon(pts + [pts[0]])


def cherry_row(key):
    """Return the KeyV2 Cherry row index for this compact five-row layout."""
    # KLE Y is mildly perturbed by the Doe column rotations, so round to the
    # nearest logical keyboard row rather than comparing exact coordinates.
    logical = max(0, min(4, int(round(key["cy"] - 0.5))))
    # Number, Q, A, Z and modifier rows correspond to Cherry rows 1..4, with
    # the two bottom rows sharing R4 as in common 60% kits.
    return (1, 2, 3, 4, 4)[logical]


def keycap_shape(key):
    """Nominal row-specific Cherry-profile clearance body.

    Dimensions follow the open KeyV2 Cherry profile: 18.16 mm base,
    11.85 x 14.64 mm 1u top, and row depth/tilt of 9.8/0, 7.45/2.5,
    6.55/5 and 7.35/11.5 degrees for R1..R4.  The exact user's keycap kit is
    not yet selected, so this intentionally remains a conservative outer
    reference rather than an injection-moulded production model.
    """
    row = cherry_row(key)
    height, tilt = {
        1: (9.80, 0.0),
        2: (7.45, 2.5),
        3: (6.55, 5.0),
        4: (7.35, 11.5),
    }[row]
    lower_w = max(12.0, key["w"] * U - 0.89)
    upper_w = max(10.0, lower_w - 6.31)
    base_z = 8.2
    cap = Part.makeLoft([
        rectangle_wire(lower_w, 18.16, base_z),
        rectangle_wire(upper_w, 14.64, base_z + height,
                       tilt_deg=tilt, y_offset=0.25),
    ], True)
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


def export_absolute_step(obj, path):
    """Export the visible assembly position baked into the STEP geometry.

    FreeCAD normally writes ``TopoShape.Placement`` as a STEP assembly
    transform. Fusion discards or reinterprets that transform when the STEP is
    imported into an already-created target component, which sent the small
    pogo boards and connector blocks back to their local origins. Apply the
    placement to the underlying geometry and reset it before export so every
    imported component has unambiguous world-space coordinates.
    """
    shape = obj.Shape.copy()
    placement = shape.Placement
    shape.Placement = App.Placement()
    # ``transformShape`` preserves exact analytic geometry under this rigid
    # rotation/translation and, unlike ``transformGeometry``, reproduces the
    # source bounding box exactly for tented plates and connector compounds.
    shape.transformShape(placement.toMatrix(), True)
    shape.exportStep(str(path))


def controller_point(source, layout):
    mech = layout["mechanism"]
    sx, sy = mech["controller_source_centre"]
    # The controller STEP is converted from KiCad's inverted raw Y coordinates
    # into the same Y-forward assembly coordinates as the Hall PCBs.  Source
    # datums can therefore be transformed directly: J1's minimum-Y edge is the
    # keyboard rear, while J2/J3 retain their left/right positions.
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
            # Plate source geometry is already spread in outline.py.  The
            # existing routed Hall PCBs remain unchanged manufacturing files,
            # so apply the same rigid-half offset only in the assembly.
            aligned.translate(App.Vector(half_spread_x(layout, side), 0, 0))
        obj = add_reference(doc, root, internal, label,
                            place_wing(aligned, layout, side),
                            "moving Hall PCB" if is_step else "plate datum",
                            (0.10, 0.34, 0.17) if is_step else (0.68, 0.70, 0.73),
                            0 if is_step else 15)
        objects.append(obj)
        Import.export([obj], str(OUT / f"Symm60HE-{internal}.step"))

    # Include the actual fitted package envelopes from KiCad. These are kept
    # separate from the board solids so Fusion users can hide them while
    # sketching, and so the exact USB/FPC/pogo components remain independently
    # selectable. The Hall assemblies are B.Cu-populated; reflecting only Y
    # preserves their correct below-board Z relationship.
    for side in ("left", "right"):
        cap = side.title()
        components = import_step_shape(GEN / f"{cap}PCBComponents.step")
        components = mirror_y_preserve_z(components)
        # All Hall-half SMT is on B.Cu.  Seat the highest component face on
        # the finished PCB bottom rather than translating from the raw KiCad
        # board Z minimum.  The raw STEP datum reflects its export thickness,
        # while the reference board is subsequently re-extruded to 1.2 mm;
        # mixing those datums left an approximately 0.39 mm visual air gap.
        components.translate(App.Vector(
            half_spread_x(layout, side), 0,
            layout["pcb_z"] - components.BoundBox.ZMax))
        component_obj = add_reference(
            doc, root, cap + "PCBComponents", cap + " Hall PCB components",
            place_wing(components, layout, side),
            "fitted KiCad package models; package CAD, not manufacturer CAD",
            (0.20, 0.22, 0.24))
        objects.append(component_obj)

    selected = [key for key in KEYS if layout["visual_layout"] in key["builds"]]
    for side_name, side_code in (("Left", "L"), ("Right", "R")):
        keys = [key for key in selected if key["half"] == side_code]
        for kind, shape, role, colour, alpha in (
            ("Switches", Part.makeCompound([switch_shape(k) for k in keys]),
             "XVX Whisper EC/HE product-specific clearance references; "
             "not manufacturer CAD", (0.88, 0.91, 0.88), 15),
            ("Keycaps", Part.makeCompound([keycap_shape(k) for k in keys]),
             "row-specific nominal Cherry-profile clearance references; "
             "not manufacturer CAD", (0.83, 0.84, 0.80), 10),
        ):
            shape.translate(App.Vector(
                half_spread_x(layout, side_name.lower()), 0, 0))
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
    controller = mirror_y_preserve_z(
        import_step_shape(GEN / "DaughterboardPCB.step"))
    controller = align_xy(controller, mech["controller_source_centre"],
                          mirror_y=False,
                          bottom_z=mech["controller_bottom_z"])
    controller = exact_board_thickness(
        controller, mech["controller_bottom_z"], mech["board_thickness"])
    controller_source_raw = tuple(mech["controller_source_centre"])
    controller = rotate_xy(controller, controller_source_raw,
                           mech["controller_rotation_deg"])
    cc, sc = mech["controller_centre"], controller_source_raw
    controller.translate(App.Vector(cc[0]-sc[0], cc[1]-sc[1], 0))
    controller_obj = add_reference(
        doc, root, "DaughterboardPCB", "Flat central controller daughterboard",
        controller, "rigid case-mounted controller PCB", (0.08, 0.27, 0.13))
    objects.append(controller_obj)
    Import.export([controller_obj], str(OUT / "Symm60HE-DaughterboardPCB.step"))

    raw_controller_board = mirror_y_preserve_z(
        import_step_shape(GEN / "DaughterboardPCB.step"))
    controller_components = mirror_y_preserve_z(import_step_shape(
        GEN / "DaughterboardComponents.step"))
    # KiCad 10.0.4 does not ship the TS-1187A package model referenced by the
    # legacy footprint. Add the exact C318884 distributor model at both real
    # F.Cu footprint datums before applying the controller assembly transform.
    button_path = OUT / "models/Button_XKB_TS-1187A-B-A-B_C318884.step"
    button_shapes = [
        place_smt_model(button_path, (x, y), 0,
                        raw_controller_board.BoundBox.ZMax)
        for x, y in ((170.709, -2.7633), (166.709, 3.2367))
    ]
    controller_components = Part.makeCompound(
        [controller_components] + button_shapes)
    controller_components.translate(App.Vector(
        0, 0, mech["controller_bottom_z"] - raw_controller_board.BoundBox.ZMin))
    controller_components = rotate_xy(
        controller_components, controller_source_raw,
        mech["controller_rotation_deg"])
    controller_components.translate(App.Vector(
        cc[0]-sc[0], cc[1]-sc[1], 0))
    controller_components_obj = add_reference(
        doc, root, "DaughterboardComponents",
        "Controller fitted components (excluding exact connectors)",
        controller_components,
        "fitted package models including exact C318884 buttons; exact USB "
        "and FPC modeled separately",
        (0.22, 0.24, 0.27))
    objects.append(controller_components_obj)

    # Include the actual HRO TYPE-C-31-M-12 model and a conservative external
    # plug/cable keepout.  The model is exported by KiCad at its real footprint
    # placement, so apply exactly the controller PCB's XY placement while
    # preserving the model's component-side Z height.
    # The source PCB's minimum-Y edge is the keyboard rear after converting
    # KiCad's raw STEP Y convention. Transform both the receptacle and edge
    # datum through the same controller placement.
    usb_point = controller_point(mech["controller_usb"], layout)
    # Import the vendor HRO solid directly.  KiCad's component-only STEP
    # wrapper reproduces the placement correctly but turns this otherwise
    # valid vendor solid into an invalid compound in FreeCAD.  Applying the
    # footprint transform here preserves the exact body and keeps the Fusion
    # reference B-rep valid.  The 1.195 mm Z placement is KiCad's F.Cu model
    # datum for this 1.2 mm finished controller board.
    usb_shell = import_step_shape(
        OUT / "models/USB_C_Receptacle_HRO_TYPE-C-31-M-12.STEP")
    # The vendor body's native mating mouth is at positive Y. Rotate it 180
    # degrees so the mouth faces the keyboard rear at minimum Y.  The actual
    # PCB now has one straight rear wall, so place the mouth exactly 1.0 mm
    # beyond that wall instead of relying on a local Edge.Cuts notch.
    usb_shell.rotate(App.Vector(), App.Vector(0, 0, 1),
                     mech["controller_usb_model_rotation_deg"])
    usb_box = usb_shell.BoundBox
    controller_box = controller.BoundBox
    usb_translation = App.Vector(
        usb_point.x - usb_box.Center.x,
        controller_box.YMin - mech["controller_usb_overhang"] - usb_box.YMin,
        mech["controller_bottom_z"] + 1.195)
    usb_shell.translate(usb_translation)
    (GEN / "usb-placement.json").write_text(json.dumps({
        "rotation_degrees": mech["controller_usb_model_rotation_deg"],
        "translation_mm": [usb_translation.x, usb_translation.y,
                           usb_translation.z],
        "overhang_mm": mech["controller_usb_overhang"],
    }, indent=2) + "\n")
    usb_obj = add_reference(
        doc, root, "ControllerUSBConnector",
        "HRO TYPE-C-31-M-12 USB-C receptacle",
        usb_shell, "actual USB-C receptacle model and case-opening datum",
        (0.62, 0.64, 0.67))
    objects.append(usb_obj)
    # Bake the verified world placement into this standalone component STEP.
    # Importing the untouched vendor hierarchy and then moving its nested
    # occurrence in Fusion proved origin-dependent.  A direct TopoShape export
    # gives Fusion one already-positioned B-rep with no assembly transform to
    # reinterpret.
    export_absolute_step(
        usb_obj, OUT / "Symm60HE-ControllerUSBConnector.step")

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
        target = list(mech[side + "_target"])
        target[0] += half_spread_x(layout, side)
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
                                  cap + " floating FPC-to-pogo PCB",
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
        spring_ffc = place_smt_model(
            OUT / "models/FFC_BOOMELE_1.0-12P_C20111.step",
            target, board_angle, spring_bottom, underside=True)
        spring_ffc_obj = add_reference(
            doc, root, cap + "SpringFFCConnector",
            cap + " floating-head FPC connector",
            place_wing(spring_ffc, layout, side),
            "exact BOOMELE 1.0-12P / LCSC C20111 B.Cu connector model",
            (0.12, 0.12, 0.14))
        objects.append(spring_ffc_obj)

        rad = math.radians(board_angle)
        entry_offset = 3.5
        ffc_dx = -entry_offset * math.sin(rad)
        ffc_dy = entry_offset * math.cos(rad)
        ffc_local = App.Vector(target[0] + ffc_dx,
                               target[1] + ffc_dy,
                               spring_bottom - 1.0)
        cable_endpoints[side] = transform_wing_point(ffc_local, layout, side)

    # Model the controller ZIF envelopes and flexible FPC reserved volumes.
    for side, source in (("left", mech["controller_left_ffc"]),
                         ("right", mech["controller_right_ffc"])):
        start, end = cable_endpoints[side], controller_point(source, layout)
        # J2/J3 are F.Cu parts, so the envelope begins at the controller's
        # finished top surface.  Do not bury half the connector in the PCB.
        # Use the real J2/J3 footprint angle plus the controller transform.
        # The previous fixed 90 degree angle disagreed with the rotated PCB.
        mouth_angle = (mech[f"controller_{side}_ffc_rotation_deg"] +
                       mech["controller_rotation_deg"])
        mouth = place_smt_model(
            OUT / "models/FFC_BOOMELE_1.0-12P_C20111.step",
            (end.x, end.y), mouth_angle, end.z)
        mouth_obj = add_reference(doc, root, side.title()+"ControllerFFC",
                                  side.title()+" controller FPC connector",
                                  mouth,
                                  "exact BOOMELE 1.0-12P / LCSC C20111 connector model",
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
            side.title()+" flexible FPC route",
            ribbon_path([start, mid1, mid2, end]),
            "12-way FPC bend and clearance reference",
            (0.15, 0.72, 0.82), 30)
        objects.append(cable_obj)

    doc.recompute()
    # Fusion independently reads this manifest after importing the component
    # files.  A mismatch stops the setup instead of leaving a plausible-looking
    # project with a daughterboard or pogo block at a STEP-local origin.
    placement_manifest = {}
    for obj in objects:
        bb = obj.Shape.BoundBox
        placement_manifest[obj.Name] = [
            bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax]
    (GEN / "component-placement.json").write_text(
        json.dumps(placement_manifest, indent=2) + "\n")
    # Meshes are generated solely for the checked documentation preview. STEP
    # and FCStd remain the authoritative Fusion handoff formats.
    for obj in objects:
        Mesh.export([obj], str(GEN / ("CaseRef-" + obj.Name + ".stl")))
        # Export every reference object independently as well.  The Fusion
        # setup uses these globally positioned files to build a useful native
        # component hierarchy instead of importing the master STEP as one
        # monolithic occurrence.  Keep the exact HRO receptacle on its vendor
        # STEP path; it is the one object that FreeCAD cannot round-trip safely.
        if obj is not usb_obj:
            export_absolute_step(
                obj, OUT / ("Symm60HE-" + obj.Name + ".step"))
    master = OUT / "Symm60HE-case-reference-assembly.step"
    legacy = OUT / "Symm60HE-reference-assembly.step"
    # Keep the exact HRO body in the editable FCStd, but import its untouched
    # vendor STEP separately in the Fusion setup add-in.  FreeCAD's STEP
    # writer makes this particular valid vendor solid "unorientable" on
    # round-trip, even without transforming it.  Excluding only that one body
    # keeps the master assembly STEP fully valid; Fusion then adds the original
    # exact solid at the same checked placement.
    step_objects = [obj for obj in objects if obj is not usb_obj]
    Import.export(step_objects, str(master))
    Import.export(step_objects, str(legacy))
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
