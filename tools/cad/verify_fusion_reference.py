#!/usr/bin/env python3
"""Verify that the Fusion handoff matches its recorded routed PCB sources.

Run with FreeCAD's bundled ``freecadcmd`` after export_fusion_reference.py.
"""
from hashlib import sha256
import json
from pathlib import Path

import FreeCAD as App
import Import


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "case/fusion360"
GEN = OUT / "generated"
PCB_NAMES = ("LeftPCB", "RightPCB", "DaughterboardPCB")
ASSEMBLY_OBJECTS = (
    "LeftPCB", "RightPCB", "DaughterboardPCB", "LeftPlate", "RightPlate",
    "LeftPCBComponents", "RightPCBComponents", "DaughterboardPCBComponents",
    "LeftRibbonCable", "RightRibbonCable",
    "LeftSwitches", "RightSwitches", "LeftKeycaps", "RightKeycaps",
)
TOLERANCE_MM = 0.02
OFFICIAL_MODEL_DIR = OUT / "models/official"
REFERENCE_MODEL_DIR = OUT / "models/reference"
EXPECTED_CHERRY_CAD_SHA256 = (
    "839630855fc95a5aee74658655b31a9037fdf7995a8269f8c4475ebaf88a8758")
EXPECTED_GATERON_SPEC_SHA256 = (
    "cdc1ff6d3354b4f10a28a2379c63e2e8bdfe8540eca2e74c31c97f7ac204655a")


def imported_primary_shape(path, document_name):
    doc = App.newDocument(document_name)
    Import.insert(str(path), doc.Name)
    shapes = [obj.Shape for obj in doc.Objects
              if (hasattr(obj, "Shape") and not obj.Shape.isNull() and
                  obj.Shape.Solids and obj.Shape.Volume > 1e-6)]
    if not shapes:
        raise RuntimeError(f"{path}: no solid geometry")
    shape = max(shapes, key=lambda candidate: candidate.Volume).copy()
    App.closeDocument(doc.Name)
    return shape


def close_enough(actual, expected):
    return abs(actual - expected) <= TOLERANCE_MM


def main():
    provenance = json.loads(
        (OFFICIAL_MODEL_DIR / "provenance.json").read_text())
    for model in provenance["models"]:
        path = OFFICIAL_MODEL_DIR / model["file"]
        digest = sha256(path.read_bytes()).hexdigest()
        if digest != model["sha256"]:
            raise RuntimeError(
                f"official component model changed: {path.name}")
        shape = imported_primary_shape(path, model["lcsc"] + "ModelCheck")
        if not shape.Solids or shape.Volume <= 1e-6:
            raise RuntimeError(f"official component model is empty: {path.name}")
        print(model["lcsc"], model["manufacturer_part"],
              "official model verified", digest[:12])

    model_record = json.loads(
        (GEN / "switch-keycap-model-provenance.json").read_text())
    cherry_path = ROOT / model_record["keycaps"]["local_source"]
    gateron_path = ROOT / model_record["switch"]["local_source"]
    cherry_digest = sha256(cherry_path.read_bytes()).hexdigest()
    gateron_digest = sha256(gateron_path.read_bytes()).hexdigest()
    if (cherry_digest != EXPECTED_CHERRY_CAD_SHA256 or
            cherry_digest != model_record["keycaps"]["sha256"]):
        raise RuntimeError("Cherry-profile reference CAD changed")
    if (gateron_digest != EXPECTED_GATERON_SPEC_SHA256 or
            gateron_digest != model_record["switch"]["sha256"]):
        raise RuntimeError("Gateron KS-20 official drawing changed")
    if (model_record["switch"]["part"] !=
            "KS-20 Magnetic Jade KS-20TF10B045NW-Y89" or
            model_record["keycaps"]["target"] !=
            "GMK CYL (original Cherry profile)"):
        raise RuntimeError("unexpected switch/keycap model identity")
    for side in ("Left", "Right"):
        record = model_record["sides"][side]
        if record["switch_count"] != 30 or record["keycap_count"] != 30:
            raise RuntimeError(f"{side}: incomplete switch/keycap bank")
        if record["keycap_minimum_clearance_mm"] < 0.20:
            raise RuntimeError(
                f"{side}: GMK CYL clearance is only "
                f"{record['keycap_minimum_clearance_mm']} mm")
    print("switch/keycap provenance verified: Gateron KS-20 Magnetic Jade",
          gateron_digest[:12], "; GMK CYL/Cherry-profile CAD",
          cherry_digest[:12], "; 60 collision-free keys")

    usb_placement = json.loads((GEN / "usb-placement.json").read_text())
    if (usb_placement["model_body_rotation_deg"] != 180.0 or
            usb_placement["opening_edge"] != "rear/min-y" or
            abs(usb_placement["overhang_mm"] - 0.6) > TOLERANCE_MM):
        raise RuntimeError(
            "USB-C must face the rear/min-Y wall and project 0.600 mm")
    print("USB-C orientation verified: rear/min-y opening;",
          round(usb_placement["overhang_mm"], 3), "mm projection")

    layout = json.loads((GEN / "reference-layout.json").read_text())
    for name in PCB_NAMES:
        record = layout[name]
        source = Path(record["source"])
        digest = sha256(source.read_bytes()).hexdigest()
        if digest != record["sha256"]:
            raise RuntimeError(f"{name}: routed PCB changed after preparation")
        shape = imported_primary_shape(GEN / f"{name}.step", name + "Check")
        actual_size = (shape.BoundBox.XLength, shape.BoundBox.YLength)
        expected_size = tuple(record["size"])
        if not all(close_enough(actual, expected)
                   for actual, expected in zip(actual_size, expected_size)):
            raise RuntimeError(
                f"{name}: STEP size {actual_size} != Edge.Cuts {expected_size}")
        configured_thickness = record["configured_board_thickness_mm"]
        # KiCad's board-only STEP is the dielectric body: copper and mask are
        # intentionally omitted. It must be positive and may not exceed the
        # complete configured stackup thickness.
        if not (0.5 < shape.BoundBox.ZLength <=
                configured_thickness + TOLERANCE_MM):
            raise RuntimeError(
                f"{name}: invalid STEP thickness {shape.BoundBox.ZLength} for "
                f"{configured_thickness} mm configured stackup")
        print(name, "verified", *(round(value, 4) for value in actual_size),
              "mm", "thickness", round(shape.BoundBox.ZLength, 4),
              "of", configured_thickness, "mm stackup", digest[:12])

    assembly_source = OUT / "Symm60HE-reference-assembly.FCStd"
    doc = App.openDocument(str(assembly_source))
    for name in ASSEMBLY_OBJECTS:
        obj = doc.getObject(name)
        if obj is None or not hasattr(obj, "Shape") or obj.Shape.isNull():
            raise RuntimeError(f"assembly missing valid {name} body")
    expected_roles = {
        "LeftSwitches": "Gateron KS-20 Magnetic Jade dimensional reference",
        "RightSwitches": "Gateron KS-20 Magnetic Jade dimensional reference",
        "LeftKeycaps": "GMK CYL / Cherry-profile dimensional reference",
        "RightKeycaps": "GMK CYL / Cherry-profile dimensional reference",
    }
    for name, role in expected_roles.items():
        if getattr(doc.getObject(name), "Role", "") != role:
            raise RuntimeError(f"{name}: wrong model role")
    for name in ("LeftKeycaps", "RightKeycaps"):
        if len(doc.getObject(name).Shape.Solids) != 30:
            raise RuntimeError(f"{name}: expected 30 detailed cap solids")
    for name in ("LeftSwitches", "RightSwitches"):
        if len(doc.getObject(name).Shape.Solids) < 300:
            raise RuntimeError(f"{name}: switch details were simplified away")
    minimum_component_solids = {
        "LeftPCBComponents": 150,
        "RightPCBComponents": 165,
        "DaughterboardPCBComponents": 25,
    }
    for name, minimum in minimum_component_solids.items():
        actual = len(doc.getObject(name).Shape.Solids)
        if actual < minimum:
            raise RuntimeError(
                f"{name}: only {actual} component solids; expected at least "
                f"{minimum}")
    component_alignment = {
        "LeftPCBComponents": ("LeftPCB", 3.0),
        "RightPCBComponents": ("RightPCB", 3.0),
        # USB-C intentionally projects slightly through the rear case wall.
        "DaughterboardPCBComponents": ("DaughterboardPCB", 6.0),
    }
    for component_name, (pcb_name, allowance) in component_alignment.items():
        component_box = doc.getObject(component_name).Shape.BoundBox
        pcb_box = doc.getObject(pcb_name).Shape.BoundBox
        if (component_box.XMin < pcb_box.XMin - allowance or
                component_box.XMax > pcb_box.XMax + allowance or
                component_box.YMin < pcb_box.YMin - allowance or
                component_box.YMax > pcb_box.YMax + allowance):
            raise RuntimeError(
                f"{component_name}: component layer is displaced from "
                f"{pcb_name}")
    collision_pairs = (
        ("LeftPlate", "RightPlate"),
        ("LeftPCB", "DaughterboardPCB"),
        ("RightPCB", "DaughterboardPCB"),
        ("LeftRibbonCable", "DaughterboardPCB"),
        ("RightRibbonCable", "DaughterboardPCB"),
        ("LeftRibbonCable", "LeftPlate"),
        ("LeftRibbonCable", "RightPlate"),
        ("RightRibbonCable", "LeftPlate"),
        ("RightRibbonCable", "RightPlate"),
        ("LeftKeycaps", "RightKeycaps"),
        ("LeftSwitches", "RightSwitches"),
    )
    for first, second in collision_pairs:
        overlap = doc.getObject(first).Shape.common(
            doc.getObject(second).Shape).Volume
        if overlap > 1e-5:
            raise RuntimeError(
                f"assembly collision: {first} / {second} = {overlap} mm^3")
    plate_clearance = doc.getObject("LeftPlate").Shape.distToShape(
        doc.getObject("RightPlate").Shape)[0]
    if plate_clearance < 0.25:
        raise RuntimeError(
            f"interior gasket clearance is only {plate_clearance} mm")
    daughter = doc.getObject("DaughterboardPCB").Shape.BoundBox
    daughter_centre_x = (daughter.XMin + daughter.XMax) / 2.0
    if abs(daughter_centre_x - layout["axis_x"]) > TOLERANCE_MM:
        raise RuntimeError(
            f"daughterboard is not centered: {daughter_centre_x} vs "
            f"axis {layout['axis_x']}")
    if daughter.YMax > 25.0:
        raise RuntimeError(
            f"daughterboard is not in the rear envelope: YMax={daughter.YMax}")
    if (layout["tent_deg"] != 3.0 or layout["typing_deg"] != 7.0 or
            layout["typing_rotation_deg"] != -7.0):
        raise RuntimeError("Fusion reference must retain 3 degrees of tent "
                           "per half and a rear-up 7 degree typing angle")
    print("assembly placement verified: centered rear daughterboard;",
          round(plate_clearance, 3), "mm minimum interior gasket clearance;",
          "3 deg per-half tent / rear-up 7 deg typing")
    App.closeDocument(doc.Name)
    imported_primary_shape(OUT / "Symm60HE-reference-assembly.step",
                           "AssemblyStepCheck")
    print("Fusion assembly verified", len(ASSEMBLY_OBJECTS), "named bodies")


main()
