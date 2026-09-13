#!/usr/bin/env python3
"""Read-only mechanical sanity checks for the generated Fusion reference."""
from pathlib import Path
import hashlib
import json
import math

import FreeCAD as App
import Import
import Part

ROOT = Path(__file__).resolve().parent.parent
FUSION = ROOT / "case/fusion360"


def close(a, b, tolerance=0.05):
    return abs(a - b) <= tolerance


def main():
    layout = json.loads((FUSION / "generated/reference-layout.json").read_text())
    assert layout["tent_deg"] == 3.0
    assert layout["typing_deg"] == 7.0
    assert layout["half_spread_mm"] == 2.75
    source = FUSION / "Symm60HE-case-reference-assembly.FCStd"
    master = FUSION / "Symm60HE-case-reference-assembly.step"
    vendor_usb = (FUSION / "models" /
                  "USB_C_Receptacle_HRO_TYPE-C-31-M-12.STEP")
    vendor_ffc = (FUSION / "models" /
                  "FFC_BOOMELE_1.0-12P_C20111.step")
    vendor_spring = (FUSION / "models" / "vendor" /
                     "Mill-Max_854-22-012-30-004101.step")
    vendor_target = (FUSION / "models" / "vendor" /
                     "Mill-Max_856-10-012-30-051000.step")
    expected_hashes = {
        vendor_spring: "13bba116749c329df6a491aa5ec57a3bdeaa1cbe453fd5ad21363497886376cd",
        vendor_target: "2436584a35d7b4dace4d154a5ab15c9538083755c03c8613585b12eb164dc912",
    }
    for path, expected_hash in expected_hashes.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash
    doc = App.openDocument(str(source))
    objects = {obj.Name: obj for obj in doc.Objects
               if hasattr(obj, "Shape") and not obj.Shape.isNull()}
    required = {
        "LeftPCB", "RightPCB", "DaughterboardPCB",
        "LeftPCBComponents", "RightPCBComponents",
        "DaughterboardComponents",
        "LeftSpringPCB", "RightSpringPCB",
        "LeftTargetConnector", "RightTargetConnector",
        "LeftSpringConnector", "RightSpringConnector",
        "LeftSpringFFCConnector", "RightSpringFFCConnector",
        "LeftControllerFFC", "RightControllerFFC",
        "ControllerUSBConnector", "ControllerUSBPlugEnvelope",
    }
    assert required.issubset(objects), sorted(required - objects.keys())
    assert all(obj.Shape.isValid() for obj in objects.values())
    assert objects["LeftPlate"].Shape.common(
        objects["RightPlate"].Shape).Volume < 1e-5
    plate_gap = objects["LeftPlate"].Shape.distToShape(
        objects["RightPlate"].Shape)[0]
    assert plate_gap > 0.40, plate_gap

    # Measure the broad top-face normal of each Hall PCB rather than trusting
    # labels or generated metadata.  With the exporter's X-then-Y rotation,
    # elevation of the normal recovers the front-to-back typing angle and its
    # X/Z projection recovers the mirrored lateral tent angle.
    def top_normal(shape):
        candidates = []
        for face in shape.Faces:
            normal = face.normalAt(0, 0)
            if normal.z > 0.5:
                candidates.append((face.Area, normal))
        assert candidates
        return max(candidates, key=lambda item: item[0])[1]

    recovered = []
    for side, expected_x_sign in (("Left", -1), ("Right", 1)):
        normal = top_normal(objects[side + "PCB"].Shape)
        typing = math.degrees(math.atan2(
            normal.y, math.hypot(normal.x, normal.z)))
        tent = math.degrees(math.atan2(abs(normal.x), normal.z))
        assert abs(typing - layout["typing_deg"]) < 1e-5, (side, typing)
        assert abs(tent - layout["tent_deg"]) < 1e-5, (side, tent)
        assert normal.x * expected_x_sign > 0, (side, normal.x)
        package_centre = objects[side + "PCBComponents"].Shape.BoundBox.Center
        pcb_centre = objects[side + "PCB"].Shape.BoundBox.Center
        package_offset = package_centre.sub(pcb_centre)
        assert package_offset.dot(normal) < 0, (
            side, "Hall components are not on the B.Cu side")
        board_box = objects[side + "PCB"].Shape.BoundBox
        package_box = objects[side + "PCBComponents"].Shape.BoundBox
        assert (board_box.XMin < package_centre.x < board_box.XMax and
                board_box.YMin < package_centre.y < board_box.YMax), (
                    side, "Hall components do not share the PCB XY datum")
        # All component mounting faces lie in the B.Cu plane. Comparing plane
        # projections is both exact and much faster than a compound-to-board
        # B-rep distance calculation across hundreds of package solids.
        board_bottom = min(vertex.Point.dot(normal)
                           for vertex in objects[side + "PCB"].Shape.Vertexes)
        package_top = max(vertex.Point.dot(normal) for vertex in
                          objects[side + "PCBComponents"].Shape.Vertexes)
        package_gap = board_bottom - package_top
        assert abs(package_gap) < 1e-5, (
            side, "Hall components are not seated on B.Cu", package_gap)
        recovered.append((tent, typing))

    controller = objects["DaughterboardPCB"].Shape.BoundBox
    assert close(controller.XLength, 57.0)
    assert close(controller.YLength, 28.0)
    assert objects["DaughterboardPCB"].Shape.common(
        objects["LeftPCB"].Shape).Volume < 1e-5
    assert objects["DaughterboardPCB"].Shape.common(
        objects["RightPCB"].Shape).Volume < 1e-5

    # Switch housings pass through the regenerated plate apertures.  Any
    # disagreement between the shifted plate cutouts and shifted PCB/key stack
    # produces a non-zero collision here.
    for side in ("Left", "Right"):
        assert objects[side + "Switches"].Shape.common(
            objects[side + "Plate"].Shape).Volume < 1e-5

    left_ffc = objects["LeftControllerFFC"].Shape.BoundBox
    right_ffc = objects["RightControllerFFC"].Shape.BoundBox
    assert left_ffc.Center.x < controller.Center.x < right_ffc.Center.x
    # These are the exact 19.0 x 6.75 x 2.51 mm C20111 distributor models,
    # rotated 90 degrees at J2/J3—not the old undersized ZIF boxes.
    assert close(left_ffc.XLength, 6.75) and close(left_ffc.YLength, 19.0)
    assert close(right_ffc.XLength, 6.75) and close(right_ffc.YLength, 19.0)
    assert objects["LeftControllerFFC"].Shape.common(
        objects["DaughterboardPCB"].Shape).Volume < 1e-5
    assert objects["RightControllerFFC"].Shape.common(
        objects["DaughterboardPCB"].Shape).Volume < 1e-5

    usb = objects["ControllerUSBConnector"].Shape.BoundBox
    plug = objects["ControllerUSBPlugEnvelope"].Shape.BoundBox
    assert usb.Center.y < controller.Center.y
    # The actual receptacle mouth remains on the controller's original rear
    # datum while the local PCB edge beneath it is set back 1.0 mm.  This
    # produces a real shell overhang rather than moving only a preview body.
    assert close(usb.YMin, controller.YMin, 0.05), (
        usb.YMin, controller.YMin)
    assert close(layout["mechanism"]["controller_usb_overhang"], 1.0)
    usb_probe = Part.makeBox(
        0.10, controller.YLength + 4.0, controller.ZLength + 2.0,
        App.Vector(usb.Center.x - 0.05, controller.YMin - 2.0,
                   controller.ZMin - 1.0))
    local_board = objects["DaughterboardPCB"].Shape.common(usb_probe)
    assert not local_board.isNull() and local_board.Volume > 1e-5
    actual_overhang = local_board.BoundBox.YMin - usb.YMin
    assert close(actual_overhang,
                 layout["mechanism"]["controller_usb_overhang"], 0.05), (
                     actual_overhang, local_board.BoundBox.YMin, usb.YMin)
    assert usb.YMax < controller.Center.y
    assert plug.Center.y < usb.Center.y
    assert plug.YMin < controller.YMin
    # Actual HRO model envelope; this prevents a simplified placeholder box
    # from silently returning to the case-design reference.
    assert close(usb.XLength, 9.104, 0.05), usb.XLength
    assert close(usb.YLength, 7.900, 0.05), usb.YLength
    assert close(usb.ZLength, 4.215, 0.05), usb.ZLength

    for side in ("Left", "Right"):
        spring = objects[side + "SpringConnector"].Shape
        target = objects[side + "TargetConnector"].Shape
        hall_pcb = objects[side + "PCB"].Shape
        spring_pcb = objects[side + "SpringPCB"].Shape
        assert spring.distToShape(target)[0] < 1e-5
        assert spring.common(target).Volume < 1e-5
        # Both connector bodies must remain seated on their respective PCBs
        # after the entire half is translated outward.
        assert target.distToShape(hall_pcb)[0] < 1e-5
        assert spring.distToShape(spring_pcb)[0] < 1e-5
        spring_ffc = objects[side + "SpringFFCConnector"].Shape
        assert spring_ffc.distToShape(spring_pcb)[0] < 1e-5
        assert spring_ffc.common(spring_pcb).Volume < 1e-5
        assert objects[side + "SpringPCB"].Shape.common(
            objects["DaughterboardPCB"].Shape).Volume < 1e-5

    assert close(layout["mechanism"]["board_to_board"], 5.0, 1e-6)

    # Independently load both exact 12-position supplier files. The selected
    # 3D ContentCentral exports contain 13 solids (housing plus 12 contacts)
    # and their configured 15.621 mm row length; a generic 2-position file or
    # the earlier procedural boxes cannot pass these checks.
    for path, expected_size in (
            (vendor_spring, (15.6210, 4.2164, 2.2098)),
            (vendor_target, (15.6210, 2.4638, 2.2098))):
        vendor_pogo_doc = App.newDocument("VendorPogoRoundTrip")
        Import.insert(str(path), vendor_pogo_doc.Name)
        vendor_pogo_shapes = [candidate.Shape for candidate in
                              vendor_pogo_doc.Objects
                              if (hasattr(candidate, "Shape") and
                                  not candidate.Shape.isNull() and
                                  len(candidate.Shape.Solids) == 13)]
        assert vendor_pogo_shapes, path
        pogo = max(vendor_pogo_shapes, key=lambda shape: abs(shape.Volume))
        actual_size = (pogo.BoundBox.XLength, pogo.BoundBox.YLength,
                       pogo.BoundBox.ZLength)
        assert all(close(actual, expected, 0.001)
                   for actual, expected in zip(actual_size, expected_size)), (
                       path, actual_size)
        App.closeDocument(vendor_pogo_doc.Name)

    # Fusion imports these files into pre-created child components. Their
    # assembly placements must therefore be baked into the STEP geometry
    # instead of being left as optional STEP occurrence transforms.
    component_steps = (
        "LeftPlate", "LeftSwitches", "LeftKeycaps",
        "RightPlate", "RightSwitches", "RightKeycaps",
        "LeftPCB", "LeftPCBComponents", "LeftTargetConnector",
        "RightPCB", "RightPCBComponents", "RightTargetConnector",
        "DaughterboardPCB", "DaughterboardComponents",
        "ControllerUSBConnector",
        "LeftControllerFFC", "RightControllerFFC",
        "LeftSpringPCB", "LeftSpringConnector", "LeftSpringFFCConnector",
        "RightSpringPCB", "RightSpringConnector", "RightSpringFFCConnector",
        "ControllerUSBPlugEnvelope", "LeftPogoTravelEnvelope",
        "RightPogoTravelEnvelope", "LeftFFCEnvelope", "RightFFCEnvelope",
    )
    for name in component_steps:
        component_doc = App.newDocument("ComponentStep_" + name)
        Import.insert(str(FUSION / ("Symm60HE-" + name + ".step")),
                      component_doc.Name)
        shapes = [candidate.Shape for candidate in component_doc.Objects
                  if (hasattr(candidate, "Shape") and
                      not candidate.Shape.isNull() and candidate.Shape.Solids)]
        assert shapes, name
        bounds = (
            min(shape.BoundBox.XMin for shape in shapes),
            min(shape.BoundBox.YMin for shape in shapes),
            min(shape.BoundBox.ZMin for shape in shapes),
            max(shape.BoundBox.XMax for shape in shapes),
            max(shape.BoundBox.YMax for shape in shapes),
            max(shape.BoundBox.ZMax for shape in shapes),
        )
        expected = objects[name].Shape.BoundBox
        expected_bounds = (expected.XMin, expected.YMin, expected.ZMin,
                           expected.XMax, expected.YMax, expected.ZMax)
        assert all(close(actual, wanted, 0.02)
                   for actual, wanted in zip(bounds, expected_bounds)), (
                       name, bounds, expected_bounds)
        App.closeDocument(component_doc.Name)

    roundtrip = App.newDocument("FusionReferenceRoundTrip")
    Import.insert(str(master), roundtrip.Name)
    imported = [obj.Shape for obj in roundtrip.Objects
                if hasattr(obj, "Shape") and not obj.Shape.isNull()]
    assert imported and all(shape.isValid() for shape in imported)
    solids = sum(len(shape.Solids) for shape in imported)
    assert solids > 100
    vendor_doc = App.newDocument("VendorUSBRoundTrip")
    Import.insert(str(vendor_usb), vendor_doc.Name)
    vendor_shapes = [obj.Shape for obj in vendor_doc.Objects
                     if (hasattr(obj, "Shape") and not obj.Shape.isNull() and
                         obj.Shape.Solids and
                         1e-6 < abs(obj.Shape.Volume) < 1e12)]
    assert vendor_shapes and all(shape.isValid() for shape in vendor_shapes)
    vendor = max(vendor_shapes, key=lambda shape: abs(shape.Volume)).copy()
    mech = layout["mechanism"]
    expected_x = (mech["controller_centre"][0] +
                  mech["controller_usb"][0] -
                  mech["controller_source_centre"][0])
    vendor.rotate(App.Vector(), App.Vector(0, 0, 1),
                  mech["controller_usb_model_rotation_deg"])
    vendor_box = vendor.BoundBox
    vendor.translate(App.Vector(
        expected_x - vendor_box.Center.x,
        controller.YMin - vendor_box.YMin,
        mech["controller_bottom_z"] + 1.195))
    # Compare the full asymmetric vendor geometry.  This catches a connector
    # whose envelope is at the rear edge but whose mouth and solder tails have
    # been exchanged by a 180-degree rotation.
    overlap = objects["ControllerUSBConnector"].Shape.common(vendor).Volume
    assert overlap > 0.9999 * vendor.Volume, (overlap, vendor.Volume)
    ffc_doc = App.newDocument("VendorFFCRoundTrip")
    Import.insert(str(vendor_ffc), ffc_doc.Name)
    ffc_shapes = [obj.Shape for obj in ffc_doc.Objects
                  if (hasattr(obj, "Shape") and not obj.Shape.isNull() and
                      obj.Shape.Solids and
                      1e-6 < abs(obj.Shape.Volume) < 1e12)]
    assert ffc_shapes and all(shape.isValid() for shape in ffc_shapes)
    ffc_vendor = max(ffc_shapes, key=lambda shape: abs(shape.Volume))
    for name in ("LeftControllerFFC", "RightControllerFFC",
                 "LeftSpringFFCConnector", "RightSpringFFCConnector"):
        assert close(objects[name].Shape.Volume, ffc_vendor.Volume, 0.01), (
            name, objects[name].Shape.Volume, ffc_vendor.Volume)
    print("Fusion reference verification: PASS")
    print("controller %.3f x %.3f mm; USB-C exits rear; J2/J3 face left/right" %
          (controller.XLength, controller.YLength))
    print("Hall PCB planes recover %.3f/%.3f degree mirrored tent and "
          "%.3f/%.3f degree typing angle" %
          (recovered[0][0], recovered[1][0],
           recovered[0][1], recovered[1][1]))
    print("both pogo spring/target interfaces are face-mated")
    print("both exact 12-position Mill-Max supplier STEP files are hash-verified")
    print("both Hall/plate/pogo assemblies use %.3f mm symmetric half spread" %
          layout["half_spread_mm"])
    print("inner plate/gasket mounts clear by %.3f mm" % plate_gap)
    print("actual HRO USB-C envelope %.3f x %.3f x %.3f mm" %
          (usb.XLength, usb.YLength, usb.ZLength))
    print("all four exact C20111 FFC bodies use the 19.000 x 6.750 x "
          "2.510 mm distributor envelope")
    print("USB-C shell overhangs its local PCB edge by %.3f mm" %
          actual_overhang)
    print("all %d component STEP files preserve absolute assembly placement" %
          len(component_steps))
    print("STEP round-trip: %d objects, %d valid solids" %
          (len(imported), solids))


# FreeCAD's command-line runner does not consistently assign ``__main__`` to
# executed macro script files, so invoke the audit explicitly.
main()
