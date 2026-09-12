#!/usr/bin/env python3
"""Validate the editable fixed-tent FreeCAD handoff and controlled dimensions."""
from pathlib import Path
import json

import FreeCAD as App

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "case/fusion360/tenting-solution"


def main():
    dimensions = json.loads((OUT / "dimensions.json").read_text())
    assert dimensions["tent_angle_deg"] == 6.0
    assert dimensions["tent_direction"] == "centre_edges_high"
    assert dimensions["board_to_board_mm"] == 6.0
    assert dimensions["nominal_spring_compression_mm"] == 0.5
    assert dimensions["printed_floor_mm"] >= 1.0
    assert dimensions["keyboard_suspension"] == \
        "eight plate-only side pads; no PCB gasket load"
    assert dimensions["target_retention"] == \
        "12-contact targets mounted directly on Hall PCBs"
    assert dimensions["interconnect"] == \
        "one short 12-way controller-to-floating-spring FFC per side"

    doc = App.openDocument(str(OUT / "Symm60HE-fixed-tent-pogo-module.FCStd"))
    features = [obj for obj in doc.Objects if obj.TypeId == "PartDesign::Feature"]
    expected = set(dimensions["separate_bodies"])
    actual = {obj.Name for obj in features}
    assert actual == expected, (sorted(expected - actual), sorted(actual - expected))
    assert len(features) == 25
    for obj in features:
        assert not obj.Shape.isNull(), obj.Name
        assert obj.Shape.isValid(), obj.Name
        assert obj.Shape.Volume > 0.01, (obj.Name, obj.Shape.Volume)
    dnp = [obj.Name for obj in features
           if hasattr(obj, "DNP_Until_Hall_Test") and obj.DNP_Until_Hall_Test]
    assert sorted(dnp) == ["LeftOptionalMagnets", "RightOptionalMagnets"], dnp

    # Guard against mirroring the tent in the wrong direction. For the left
    # wing the centre-facing edge is max X; for the right wing it is min X.
    # Compare each PCB's edge mid-plane Z so board thickness cannot mask the
    # direction of the slope.
    def edge_midplane_z(obj, use_max_x):
        vertices = [(v.Point.x, v.Point.z) for v in obj.Shape.Vertexes]
        edge_x = (max if use_max_x else min)(x for x, _ in vertices)
        edge_z = [z for x, z in vertices if abs(x - edge_x) < 1e-6]
        assert edge_z, obj.Name
        return sum(edge_z) / len(edge_z)

    left = doc.getObject("LeftWingPCB")
    right = doc.getObject("RightWingPCB")
    assert edge_midplane_z(left, True) > edge_midplane_z(left, False), \
        "left wing centre edge is not raised"
    assert edge_midplane_z(right, False) > edge_midplane_z(right, True), \
        "right wing centre edge is not raised"
    # Report the full feature union bounds rather than depending on group shape.
    xmin = min(obj.Shape.BoundBox.XMin for obj in features)
    xmax = max(obj.Shape.BoundBox.XMax for obj in features)
    ymin = min(obj.Shape.BoundBox.YMin for obj in features)
    ymax = max(obj.Shape.BoundBox.YMax for obj in features)
    zmin = min(obj.Shape.BoundBox.ZMin for obj in features)
    zmax = max(obj.Shape.BoundBox.ZMax for obj in features)
    print(f"25 valid separate bodies; envelope {xmax-xmin:.2f} x {ymax-ymin:.2f} x {zmax-zmin:.2f} mm")
    print("centre-high 6 degree tent direction verified")
    print("6.0 mm stack; direct Hall-PCB targets; two floating FFC spring heads; plate-only side gaskets")
    App.closeDocument(doc.Name)


main()
