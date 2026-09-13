#!/usr/bin/env python3
"""Read-only mechanical sanity checks for the generated Fusion reference."""
from pathlib import Path
import json
import math

import FreeCAD as App
import Import

ROOT = Path(__file__).resolve().parent.parent
FUSION = ROOT / "case/fusion360"


def close(a, b, tolerance=0.05):
    return abs(a - b) <= tolerance


def main():
    layout = json.loads((FUSION / "generated/reference-layout.json").read_text())
    assert layout["tent_deg"] == 3.0
    assert layout["typing_deg"] == 7.0
    source = FUSION / "Symm60HE-case-reference-assembly.FCStd"
    master = FUSION / "Symm60HE-case-reference-assembly.step"
    doc = App.openDocument(str(source))
    objects = {obj.Name: obj for obj in doc.Objects
               if hasattr(obj, "Shape") and not obj.Shape.isNull()}
    required = {
        "LeftPCB", "RightPCB", "DaughterboardPCB",
        "LeftSpringPCB", "RightSpringPCB",
        "LeftTargetConnector", "RightTargetConnector",
        "LeftSpringConnector", "RightSpringConnector",
        "LeftSpringFFCConnector", "RightSpringFFCConnector",
        "LeftControllerFFC", "RightControllerFFC",
        "ControllerUSBConnector", "ControllerUSBPlugEnvelope",
    }
    assert required.issubset(objects), sorted(required - objects.keys())
    assert all(obj.Shape.isValid() for obj in objects.values())

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
        recovered.append((tent, typing))

    controller = objects["DaughterboardPCB"].Shape.BoundBox
    assert close(controller.XLength, 57.0)
    assert close(controller.YLength, 28.0)
    assert objects["DaughterboardPCB"].Shape.common(
        objects["LeftPCB"].Shape).Volume < 1e-5
    assert objects["DaughterboardPCB"].Shape.common(
        objects["RightPCB"].Shape).Volume < 1e-5

    left_ffc = objects["LeftControllerFFC"].Shape.BoundBox
    right_ffc = objects["RightControllerFFC"].Shape.BoundBox
    assert left_ffc.Center.x < controller.Center.x < right_ffc.Center.x
    assert close(left_ffc.XLength, 5.0) and close(left_ffc.YLength, 14.0)
    assert close(right_ffc.XLength, 5.0) and close(right_ffc.YLength, 14.0)
    assert objects["LeftControllerFFC"].Shape.common(
        objects["DaughterboardPCB"].Shape).Volume < 1e-5
    assert objects["RightControllerFFC"].Shape.common(
        objects["DaughterboardPCB"].Shape).Volume < 1e-5

    usb = objects["ControllerUSBConnector"].Shape.BoundBox
    plug = objects["ControllerUSBPlugEnvelope"].Shape.BoundBox
    assert usb.Center.y < controller.Center.y
    assert plug.Center.y < usb.Center.y
    assert plug.YMin < controller.YMin

    for side in ("Left", "Right"):
        spring = objects[side + "SpringConnector"].Shape
        target = objects[side + "TargetConnector"].Shape
        assert spring.distToShape(target)[0] < 1e-5
        assert spring.common(target).Volume < 1e-5
        assert objects[side + "SpringPCB"].Shape.common(
            objects["DaughterboardPCB"].Shape).Volume < 1e-5

    roundtrip = App.newDocument("FusionReferenceRoundTrip")
    Import.insert(str(master), roundtrip.Name)
    imported = [obj.Shape for obj in roundtrip.Objects
                if hasattr(obj, "Shape") and not obj.Shape.isNull()]
    assert imported and all(shape.isValid() for shape in imported)
    solids = sum(len(shape.Solids) for shape in imported)
    assert solids > 100
    print("Fusion reference verification: PASS")
    print("controller %.3f x %.3f mm; USB-C exits rear; J2/J3 face left/right" %
          (controller.XLength, controller.YLength))
    print("Hall PCB planes recover %.3f/%.3f degree mirrored tent and "
          "%.3f/%.3f degree typing angle" %
          (recovered[0][0], recovered[1][0],
           recovered[0][1], recovered[1][1]))
    print("both pogo spring/target interfaces are face-mated")
    print("STEP round-trip: %d objects, %d valid solids" %
          (len(imported), solids))


# FreeCAD's command-line runner does not consistently assign ``__main__`` to
# executed macro script files, so invoke the audit explicitly.
main()
