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
EXPECTED_PCB_SOURCES = {
    "LeftPCB": "Symm60HE-Left.kicad_pcb",
    "RightPCB": "Symm60HE-Right.kicad_pcb",
    "DaughterboardPCB": "Symm60HE-Daughterboard.kicad_pcb",
}
EXPECTED_DAUGHTERBOARD_SIZE_MM = (49.5, 29.2)
EXPECTED_PLATE_THICKNESS_MM = 1.5
EXPECTED_PLATE_TO_PCB_TOP_MM = 5.0
EXPECTED_PLATE_UNDERSIDE_TO_PCB_TOP_MM = 3.5
EXPECTED_DAUGHTERBOARD_BELOW_HALL_PCB_MM = 7.0


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


def flatten_half_shape(shape, layout, side, z):
    """Undo the assembly tilt while retaining the object's absolute Z datum."""
    result = shape.copy()
    pivot = App.Vector(layout["axis_x"], layout["front_y"], 0)
    result.translate(App.Vector(0, 0, -z))
    result.rotate(pivot, App.Vector(1, 0, 0),
                  -layout["typing_rotation_deg"])
    tent_angle = (-layout["tent_deg"] if side == "Left"
                  else layout["tent_deg"])
    result.rotate(pivot, App.Vector(0, 1, 0), -tent_angle)
    result.translate(App.Vector(0, 0, z))
    return result


def main():
    provenance = json.loads(
        (OFFICIAL_MODEL_DIR / "provenance.json").read_text())
    notice = (OFFICIAL_MODEL_DIR /
              "JLCEDA-EasyEDA-OFFICIAL-LIBRARY-NOTICE.md").read_text()
    for required in ("JLCEDA/EasyEDA Official Library", "https://lceda.cn/",
                     "https://easyeda.com/"):
        if required not in notice:
            raise RuntimeError("official-library attribution notice incomplete")
    provenance_files = set()
    for model in provenance["models"]:
        path = OFFICIAL_MODEL_DIR / model["file"]
        provenance_files.add(model["file"])
        model_bytes = path.read_bytes()
        digest = sha256(model_bytes).hexdigest()
        # BOOMELE and XKB publish their text STEP assets with CRLF endings.
        # Git may materialize the same geometry with LF endings on macOS/Linux,
        # so also compare the canonical source-line-ending representation.
        crlf_bytes = model_bytes.replace(b"\r\n", b"\n").replace(
            b"\n", b"\r\n")
        source_digest = sha256(crlf_bytes).hexdigest()
        if model["sha256"] not in (digest, source_digest):
            raise RuntimeError(
                f"official component model changed: {path.name}")
        shape = imported_primary_shape(path, model["lcsc"] + "ModelCheck")
        if not shape.Solids or shape.Volume <= 1e-6:
            raise RuntimeError(f"official component model is empty: {path.name}")
        print(model["lcsc"], model["manufacturer_part"],
              "official model verified", model["sha256"][:12])

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
    detailed_path = ROOT / model_record["switch"]["detailed_model"]
    detailed_digest = sha256(detailed_path.read_bytes()).hexdigest()
    if detailed_digest != model_record["switch"]["detailed_model_sha256"]:
        raise RuntimeError("generated multi-part KS-20 model changed")
    detailed_shape = imported_primary_shape(
        detailed_path, "DetailedKS20ModelCheck")
    if (detailed_shape.BoundBox.XLength < 13.9 or
            detailed_shape.BoundBox.YLength < 13.9 or
            detailed_shape.BoundBox.ZLength < 5.0):
        raise RuntimeError("generated multi-part KS-20 model is incomplete")
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
    coverage = json.loads((GEN / "component-model-coverage.json").read_text())
    fitted_electrical = 0
    unresolved_mechanical = 0
    used_model_files = set()
    for board_name in PCB_NAMES:
        expected = layout[board_name]["fitted_footprints"]
        actual = coverage["boards"][board_name]
        expected_refs = [item["reference"] for item in expected]
        actual_refs = [item["reference"] for item in actual]
        if expected_refs != actual_refs or len(actual_refs) != len(set(actual_refs)):
            raise RuntimeError(
                f"{board_name}: component coverage does not match PCB footprints")
        for item in actual:
            status = item["status"]
            if item["dnp"]:
                if status != "not fitted (DNP)":
                    raise RuntimeError(
                        f"{board_name} {item['reference']}: DNP was modeled")
            elif item["value"] == "M2_NPTH":
                if status != "board aperture; no fitted body":
                    raise RuntimeError(
                        f"{board_name} {item['reference']}: aperture coverage wrong")
            elif item["value"] == "STAB_MX":
                unresolved_mechanical += 1
                if status != "unresolved mechanical identity":
                    raise RuntimeError(
                        f"{board_name} {item['reference']}: stabilizer falsely certified")
            else:
                fitted_electrical += 1
                if status not in ("exact part-linked model", "exact vendor model"):
                    raise RuntimeError(
                        f"{board_name} {item['reference']}: fitted part not exact")
                if item["model"] not in provenance_files:
                    raise RuntimeError(
                        f"{board_name} {item['reference']}: unverified model file")
                used_model_files.add(item["model"])
    if used_model_files != provenance_files:
        raise RuntimeError(
            "official model provenance contains unused or missing assets: "
            f"used={sorted(used_model_files)} recorded={sorted(provenance_files)}")
    if unresolved_mechanical != 5:
        raise RuntimeError(
            f"expected five unspecified stabilizers, found {unresolved_mechanical}")
    print("component coverage verified:", fitted_electrical,
          "fitted electrical parts use exact part-linked/vendor models;",
          unresolved_mechanical, "stabilizers explicitly unresolved")
    stack_checks = {
        "plate thickness": (
            layout["plate_thickness_mm"], EXPECTED_PLATE_THICKNESS_MM),
        "plate seating plane to PCB top": (
            layout["plate_to_pcb_top_mm"], EXPECTED_PLATE_TO_PCB_TOP_MM),
        "plate underside to PCB top": (
            layout["plate_underside_to_pcb_top_mm"],
            EXPECTED_PLATE_UNDERSIDE_TO_PCB_TOP_MM),
        "daughterboard below Hall PCB": (
            layout["daughterboard_below_hall_pcb_mm"],
            EXPECTED_DAUGHTERBOARD_BELOW_HALL_PCB_MM),
    }
    for label, (actual, expected) in stack_checks.items():
        if not close_enough(actual, expected):
            raise RuntimeError(
                f"incorrect {label}: {actual} mm; expected {expected} mm")
    if not close_enough(
            layout["plate_seating_z"] - layout["pcb_z"],
            EXPECTED_PLATE_TO_PCB_TOP_MM):
        raise RuntimeError("plate seating and PCB Z datums do not make 5.00 mm")
    if not close_enough(
            layout["plate_seating_z"] - layout["plate_z"],
            EXPECTED_PLATE_THICKNESS_MM):
        raise RuntimeError("plate solid is not below its top seating datum")
    if not close_enough(
            layout["plate_z"] - layout["pcb_z"],
            EXPECTED_PLATE_UNDERSIDE_TO_PCB_TOP_MM):
        raise RuntimeError("plate underside and PCB top do not make 3.50 mm")
    if not close_enough(
            layout["pcb_z"] - layout["daughterboard_z"],
            EXPECTED_DAUGHTERBOARD_BELOW_HALL_PCB_MM):
        raise RuntimeError("daughterboard did not follow the corrected PCB datum")
    print("Gateron KS-20 stack verified: 5.00 mm plate seating plane to PCB "
          "top; 1.50 mm plate; 3.50 mm underside gap")
    for name in PCB_NAMES:
        record = layout[name]
        source = Path(record["source"])
        if source.name != EXPECTED_PCB_SOURCES[name]:
            raise RuntimeError(
                f"{name}: stale case-reference source {source.name}; expected "
                f"{EXPECTED_PCB_SOURCES[name]}")
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
    daughter_size = tuple(layout["DaughterboardPCB"]["size"])
    if not all(close_enough(actual, expected) for actual, expected in zip(
            daughter_size, EXPECTED_DAUGHTERBOARD_SIZE_MM)):
        raise RuntimeError(
            "case reference must use the compact 49.5 x 29.2 mm "
            f"daughterboard, not {daughter_size}")

    assembly_source = OUT / "Symm60HE-reference-assembly.FCStd"
    doc = App.openDocument(str(assembly_source))
    for name in ASSEMBLY_OBJECTS:
        obj = doc.getObject(name)
        if obj is None or not hasattr(obj, "Shape") or obj.Shape.isNull():
            raise RuntimeError(f"assembly missing valid {name} body")
    for side in ("Left", "Right"):
        plate = flatten_half_shape(
            doc.getObject(side + "Plate").Shape, layout, side,
            layout["plate_z"])
        pcb = flatten_half_shape(
            doc.getObject(side + "PCB").Shape, layout, side,
            layout["pcb_z"])
        switches = flatten_half_shape(
            doc.getObject(side + "Switches").Shape, layout, side,
            layout["plate_seating_z"])
        if (not close_enough(plate.BoundBox.ZMin, layout["plate_z"]) or
                not close_enough(
                    plate.BoundBox.ZMax, layout["plate_seating_z"])):
            raise RuntimeError(f"{side}: generated plate solid has wrong Z faces")
        if not close_enough(pcb.BoundBox.ZMax, layout["pcb_z"]):
            raise RuntimeError(f"{side}: generated PCB top has wrong Z datum")
        lower_housings = [
            solid for solid in switches.Solids
            if (solid.BoundBox.XLength > 13.0 and
                solid.BoundBox.YLength > 13.0 and
                close_enough(solid.BoundBox.ZMin, layout["pcb_z"]) and
                close_enough(
                    solid.BoundBox.ZMax, layout["plate_seating_z"]))
        ]
        if len(lower_housings) != 30:
            raise RuntimeError(
                f"{side}: found {len(lower_housings)} KS-20 lower housings, "
                "expected 30")
        for housing in lower_housings:
            if (not close_enough(housing.BoundBox.ZMin, layout["pcb_z"]) or
                    not close_enough(
                        housing.BoundBox.ZMax, layout["plate_seating_z"])):
                raise RuntimeError(
                    f"{side}: a switch lower housing does not seat on PCB")
    print("generated solids verified: 3.50 mm plate underside clearance; "
          "switch bases seated on both PCB tops")
    expected_roles = {
        "LeftSwitches": (
            "Gateron KS-20 Magnetic Jade detailed multi-part real-form model"),
        "RightSwitches": (
            "Gateron KS-20 Magnetic Jade detailed multi-part real-form model"),
        "LeftKeycaps": "GMK CYL / Cherry-profile full thin-wall CAD model",
        "RightKeycaps": "GMK CYL / Cherry-profile full thin-wall CAD model",
    }
    for name, role in expected_roles.items():
        if getattr(doc.getObject(name), "Role", "") != role:
            raise RuntimeError(f"{name}: wrong model role")
    for name in ("LeftPCBComponents", "RightPCBComponents",
                 "DaughterboardPCBComponents"):
        if getattr(doc.getObject(name), "Role", "") != (
                "exact part-number-linked fitted component models"):
            raise RuntimeError(f"{name}: generic or unverified component role")
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
        ("LeftPlate", "DaughterboardPCB"),
        ("RightPlate", "DaughterboardPCB"),
        ("LeftPlate", "DaughterboardPCBComponents"),
        ("RightPlate", "DaughterboardPCBComponents"),
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


if __name__ == "__main__":
    main()
