#!/usr/bin/env python3
"""Combine the populated split-keyboard reference with the Neo pogo kernel."""
from pathlib import Path
import json

import FreeCAD as App
import Import

ROOT = Path(__file__).resolve().parent.parent
FUSION = ROOT / "case/fusion360"
OUT = FUSION / "pogo-neo"


def feature(doc, group, name, label, shape, role):
    obj = doc.addObject("PartDesign::Feature", name)
    obj.Label = label
    obj.Shape = shape.removeSplitter()
    obj.addProperty("App::PropertyString", "Role", "Reference")
    obj.Role = role
    group.addObject(obj)
    return obj


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    layout = json.loads((FUSION / "generated/reference-layout.json").read_text())
    base = App.openDocument(str(FUSION / "Symm60HE-reference-assembly.FCStd"))
    kernel = App.openDocument(str(
        FUSION / "tenting-solution/Symm60HE-fixed-tent-pogo-module.FCStd"))
    doc = App.newDocument("Symm60HE_Neo_Pogo_Reference")
    root = doc.addObject("App::Part", "Symm60HENeoPogoReference")
    root.Label = "Symm60HE populated Neo-style pogo reference"
    objects = []

    # The old FFC reference's daughterboard is deliberately excluded. The
    # rigid flat controller in the kernel replaces it; all other PCB, plate,
    # switch and keycap reference bodies are retained at their checked planes.
    for source in base.Objects:
        if (source.TypeId != "PartDesign::Feature" or
                source.Name == "DaughterboardPCB"):
            continue
        objects.append(feature(doc, root, "Keyboard" + source.Name,
                               source.Label, source.Shape.copy(),
                               "Existing populated keyboard reference"))

    axis = layout["axis_x"]
    centre_y = 56.0
    pivot = App.Vector(axis, layout["front_y"], 0)
    kernel_sources = [source for source in kernel.Objects
                      if source.TypeId == "PartDesign::Feature"]
    for source in kernel_sources:
        shape = source.Shape.copy()
        shape.translate(App.Vector(axis, centre_y, 0))
        shape.rotate(pivot, App.Vector(1, 0, 0), layout["typing_deg"])
        objects.append(feature(doc, root, "Kernel" + source.Name,
                               source.Label, shape,
                               "Neo-style rigid controller and plate-isolated pogo kernel"))

    doc.recompute()
    step = OUT / "Symm60HE-Neo-Pogo-Reference.step"
    source = OUT / "Symm60HE-Neo-Pogo-Reference.FCStd"
    Import.export(objects, str(step))
    if source.exists():
        source.unlink()
    doc.saveAs(str(source))
    manifest = {
        "body_count": len(objects),
        "keyboard_reference_bodies": 8,
        "kernel_bodies": len(kernel_sources),
        "pogo_spring_mpn": "854-22-012-30-004101",
        "pogo_target_mpn": "856-10-012-30-051000",
        "pogo_contacts_per_interface": 12,
        "pogo_pitch_mm": 1.27,
        "pogo_spring_initial_height_mm": 4.216,
        "pogo_spring_stroke_mm": 1.016,
        "pogo_spring_working_height_mm": 3.79,
        "pogo_target_projection_mm": 2.21,
        "pogo_model_note": "dimensioned case-design reference, not vendor-certified CAD",
        "controller_orientation": "lengthwise on centreline; flat across lateral tent; common 7 degree typing plane",
        "target_retention": "12-contact targets mounted directly on Hall PCBs",
        "keyboard_suspension": "eight side gaskets on plates only",
        "files": [step.name, source.name],
    }
    (OUT / "reference-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(step.relative_to(ROOT))
    print(source.relative_to(ROOT))
    print(len(objects), "separate reference bodies")


main()
