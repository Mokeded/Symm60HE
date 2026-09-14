#!/usr/bin/env python3
"""Validate the editable fixed-tent FreeCAD handoff and controlled dimensions."""
from pathlib import Path
import json
import math

import FreeCAD as App

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "case/fusion360/tenting-solution"


def main():
    dimensions = json.loads((OUT / "dimensions.json").read_text())
    assert dimensions["tent_angle_deg"] == 3.0
    assert dimensions["tent_direction"] == "centre_edges_high"
    assert dimensions["board_to_board_mm"] == 6.0
    assert dimensions["nominal_spring_compression_mm"] == 0.5
    assert dimensions["printed_floor_mm"] >= 1.0
    assert dimensions["keyboard_suspension"] == \
        "eight plate-only side pads; no PCB gasket load"
    assert dimensions["target_retention"] == \
        "12-contact targets mounted directly on Hall PCBs"
    assert dimensions["interconnect"] == \
        "one short 12-way controller-to-floating-spring FPC per side"

    doc = App.openDocument(str(OUT / "Symm60HE-fixed-tent-pogo-module.FCStd"))
    features = [obj for obj in doc.Objects if obj.TypeId == "PartDesign::Feature"]
    expected = set(dimensions["separate_bodies"])
    actual = {obj.Name for obj in features}
    assert actual == expected, (sorted(expected - actual), sorted(actual - expected))
    assert len(features) == 27
    for obj in features:
        assert not obj.Shape.isNull(), obj.Name
        assert obj.Shape.isValid(), obj.Name
        assert obj.Shape.Volume > 0.01, (obj.Name, obj.Shape.Volume)
    dnp = [obj.Name for obj in features
           if hasattr(obj, "DNP_Until_Hall_Test") and obj.DNP_Until_Hall_Test]
    assert sorted(dnp) == ["LeftOptionalMagnets", "RightOptionalMagnets"], dnp

    # Guard both the magnitude and direction of the compound transform.  The
    # old extreme-vertex calculation was distorted by the PCB thickness after
    # rotation; the normal of the broad planar PCB face recovers the actual
    # tent plane independently of board thickness.
    def top_normal(obj):
        candidates = []
        for face in obj.Shape.Faces:
            normal = face.normalAt(0, 0)
            if normal.z > 0.5:
                candidates.append((face.Area, normal))
        assert candidates, obj.Name
        return max(candidates, key=lambda item: item[0])[1]

    left = doc.getObject("LeftWingPCB")
    right = doc.getObject("RightWingPCB")
    left_normal = top_normal(left)
    right_normal = top_normal(right)
    left_angle = math.degrees(math.atan2(abs(left_normal.x), left_normal.z))
    right_angle = math.degrees(math.atan2(abs(right_normal.x), right_normal.z))
    assert abs(left_angle - dimensions["tent_angle_deg"]) < 1e-5, left_angle
    assert abs(right_angle - dimensions["tent_angle_deg"]) < 1e-5, right_angle
    assert left_normal.x < 0, "left wing centre edge is not raised"
    assert right_normal.x > 0, "right wing centre edge is not raised"
    print("wing plane normals recover %.3f/%.3f degree mirrored tent" %
          (left_angle, right_angle))
    # Report the full feature union bounds rather than depending on group shape.
    xmin = min(obj.Shape.BoundBox.XMin for obj in features)
    xmax = max(obj.Shape.BoundBox.XMax for obj in features)
    ymin = min(obj.Shape.BoundBox.YMin for obj in features)
    ymax = max(obj.Shape.BoundBox.YMax for obj in features)
    zmin = min(obj.Shape.BoundBox.ZMin for obj in features)
    zmax = max(obj.Shape.BoundBox.ZMax for obj in features)
    print(f"27 valid separate bodies; envelope {xmax-xmin:.2f} x {ymax-ymin:.2f} x {zmax-zmin:.2f} mm")
    print("centre-high 3 degree tent direction verified")
    print("6.0 mm stack; direct Hall-PCB targets; two floating FPC spring heads; plate-only side gaskets")
    App.closeDocument(doc.Name)


main()
