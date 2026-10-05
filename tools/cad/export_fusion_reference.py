#!/usr/bin/env python3
"""Create a Fusion-ready PCB, plate, switch and keycap reference assembly.

Run with FreeCAD's bundled ``freecadcmd`` after prepare_fusion_reference.py.
The objects are intentionally separate named bodies and are positioned on the
same tented/typed planes they occupy in the future enclosure.
"""
from pathlib import Path
from hashlib import sha256
import json
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import FreeCAD as App
import Import
import Mesh
import Part

from geom import KEYS, U

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "case/fusion360"
GEN = OUT / "generated"
OFFICIAL_MODELS = OUT / "models/official"
REFERENCE_MODELS = OUT / "models/reference"
GMK_CYL_MODEL = REFERENCE_MODELS / "gmk-cyl/Cherry-MX-keycaps.step"
GMK_CYL_LICENSE = REFERENCE_MODELS / "gmk-cyl/LICENSE-MIT.txt"
GATERON_JADE_SPEC = (REFERENCE_MODELS /
                     "gateron-ks20-magnetic-jade/"
                     "GATERON-Magnetic-Jade-KS20-specification.pdf")
KEYCAP_SKIRT_Z = 6.15
_keycap_library = None
_step_shape_cache = {}


# Exact fitted-part model selection.  The STEP assets are either published by
# the manufacturer or linked to the exact LCSC ordering code in the
# JLCEDA/EasyEDA Official Library.  Shared passive/package assets are only
# reused where the exact part records themselves point at the same model UUID.
COMPONENT_MODELS = {
    "ffc": {
        "file": "BOOMELE_1.0-12P_C20111.step", "rotations": (),
        "seat": True, "source": "JLCEDA/EasyEDA Official Library",
    },
    "mux": {
        "file": "TI_SN74LV4051APWR_C7793.step", "rotations": (),
        "seat": True, "source": "JLCEDA/EasyEDA Official Library",
    },
    "hall": {
        "file": "NOVOSENSE_MT9102ET_C5447698.step",
        "rotations": (("z", 90),), "seat": True,
        "source": "JLCEDA/EasyEDA Official Library",
    },
    "led": {
        "file": "OPSCO_SK6812MINI-E_C5149201.step", "rotations": (),
        # This reverse-mount model deliberately straddles B.Cu: 0.84 mm enters
        # the board aperture and 0.94 mm remains below the board.
        "seat": False, "source": "JLCEDA/EasyEDA Official Library",
    },
    "mcu": {
        "file": "ARTERY_AT32F405RCT7_C47090415.step", "rotations": (),
        "seat": True, "source": "JLCEDA/EasyEDA Official Library",
    },
    "esd": {
        "file": "ST_USBLC6-2SC6_C7519.step",
        "rotations": (("z", 90),), "seat": True,
        "source": "JLCEDA/EasyEDA Official Library",
    },
    "tlv757": {
        "file": "TI_TLV75733PDBVR_C485517.step",
        "rotations": (("z", 90),), "seat": True,
        "source": "JLCEDA/EasyEDA Official Library",
    },
    "xc6206": {
        "file": "NOVOSENSE_MT9102ET_C5447698.step",
        "rotations": (("z", 90),), "seat": True,
        "source": "JLCEDA/EasyEDA Official Library",
    },
    "crystal": {
        "file": "YXC_X322512MSB4SI_C9002.step", "rotations": (),
        "seat": True, "source": "JLCEDA/EasyEDA Official Library",
    },
    "fuse": {
        "file": "BHFUSE_BSMD0805-050-24V_C910822.step", "rotations": (),
        "seat": True, "source": "JLCEDA/EasyEDA Official Library",
    },
    "buffer": {
        "file": "TI_SN74AHCT1G125DBVR_C7484.step",
        "rotations": (("z", 180),), "seat": True,
        "source": "JLCEDA/EasyEDA Official Library",
    },
    "c0402": {
        "file": "SAMSUNG_CL05B104KO5NNNC_C1525.step", "rotations": (),
        "seat": True, "source": "JLCEDA/EasyEDA Official Library",
    },
    "r0402": {
        "file": "UNI-ROYAL_0402WGF1202TCE_C25752.step", "rotations": (),
        "seat": True, "source": "JLCEDA/EasyEDA Official Library",
    },
    "c0603": {
        "file": "CCTC_TCC0603X5R106M6R3CT_C380318.step", "rotations": (),
        "seat": True, "source": "JLCEDA/EasyEDA Official Library",
    },
    "button": {
        "file": "XKB_TS-1187A-B-A-B_C318884.stp",
        "rotations": (("x", 90),), "seat": True,
        "source": "XKB manufacturer STEP",
    },
}

VALUE_MODELS = {
    "FFC_12P": ("ffc", "C20111", "BOOMELE 1.0-12P top-contact"),
    "SN74LV4051A": ("mux", "C7793", "TI SN74LV4051APWR"),
    "MT9102ET": ("hall", "C5447698", "NOVOSENSE MT9102ET"),
    "SK6812MINI-E": ("led", "C5149201", "OPSCO SK6812MINI-E"),
    "AT32F405RCT7": ("mcu", "C47090415", "Artery AT32F405RCT7"),
    "USBLC6-2SC6": ("esd", "C7519", "ST USBLC6-2SC6"),
    "TLV75733PDBV": ("tlv757", "C485517", "TI TLV75733PDBVR"),
    "XC6206P332MR": ("xc6206", "C5446", "Torex XC6206P332MR-G"),
    "12MHz": ("crystal", "C9002", "YXC X322512MSB4SI"),
    "0.5A": ("fuse", "C910822", "BHFUSE BSMD0805-050-24V"),
    "SN74AHCT1G125": ("buffer", "C7484", "TI SN74AHCT1G125DBVR"),
    "100n": ("c0402", "C1525", "Samsung CL05B104KO5NNNC"),
    "4.7n": ("c0402", "C1518204", "Murata GRM1555C1H472JE01D"),
    "30p": ("c0402", "C466228", "CCTC TCC0402C0G300J500AT"),
    "12k": ("r0402", "C25752", "UNI-ROYAL 0402WGF1202TCE"),
    "5.1k": ("r0402", "C25905", "UNI-ROYAL 0402WGF5101TCE"),
    "470R": ("r0402", "C25117", "UNI-ROYAL 0402WGF4700TCE"),
    "10u": ("c0603", "C380318", "CCTC TCC0603X5R106M6R3CT"),
    "2.2u": ("c0603", "C3905270", "Samsung CL10B225KP8NFNC"),
    "1u": ("c0603", "C97888", "Murata GRM188R71A105KA61D"),
    "TS-1187A": ("button", "C318884", "XKB TS-1187A-B-A-B"),
}


def import_step_shape(path):
    path = Path(path).resolve()
    if path in _step_shape_cache:
        return _step_shape_cache[path].copy()
    temp = App.newDocument("ImportTemp")
    Import.insert(str(path), temp.Name)
    shapes = [obj.Shape for obj in temp.Objects
              if (hasattr(obj, "Shape") and not obj.Shape.isNull() and
                  obj.Shape.Solids and 1e-6 < abs(obj.Shape.Volume) < 1e12)]
    if not shapes:
        raise RuntimeError(f"STEP contained no shapes: {path}")
    # KiCad's STEP hierarchy exposes the same board solid through both its
    # product and child object; keep one physical solid, not both duplicates or
    # FreeCAD's infinite origin planes.
    result = max(shapes, key=lambda shape: abs(shape.Volume)).copy()
    App.closeDocument(temp.Name)
    _step_shape_cache[path] = result.copy()
    return result.copy()


def solid_from_stl(path):
    mesh = Mesh.Mesh(str(path))
    shape = Part.Shape()
    shape.makeShapeFromMesh(mesh.Topology, 0.02)
    solids = []
    for shell in shape.Shells:
        solid = Part.makeSolid(shell)
        if not solid.isNull() and solid.Volume > 1e-5:
            solids.append(solid)
    if not solids:
        raise RuntimeError(f"STL conversion produced no solid: {path}")
    return Part.makeCompound(solids).removeSplitter()


def align_xy(shape, desired_centre, mirror_y=False):
    result = shape.copy()
    if mirror_y:
        # KiCad STEP uses conventional Y-up coordinates while the board/DXF
        # sources use KiCad's screen-space Y-down coordinates. A 180 degree
        # rigid rotation about X corrects Y without the invalid negative-scale
        # transform that corrupts analytic STEP surfaces.
        result.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 180)
    bb = result.BoundBox
    result.translate(App.Vector(desired_centre[0] - (bb.XMin + bb.XMax)/2,
                                desired_centre[1] - (bb.YMin + bb.YMax)/2, 0))
    return result


def align_board_coordinates(shape, source_centre, desired_centre):
    """Align board-coordinate geometry without recentering its own bounds.

    A populated component compound rarely has the same bounding-box centre as
    Edge.Cuts.  Translating from that compound centre would visibly slide all
    parts away from their pads, so use the recorded board centre as the datum.
    """
    result = shape.copy()
    result.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 180)
    # KiCad STEP has already converted screen-space +Y-down coordinates to
    # conventional -Y.  The X-axis rotation restores +Y-down, after which the
    # recorded source centre can be translated directly to the assembly datum.
    result.translate(App.Vector(desired_centre[0] - source_centre[0],
                                desired_centre[1] - source_centre[1], 0))
    return result


def place(shape, layout, side, z):
    result = shape.copy()
    pivot = App.Vector(layout["axis_x"], layout["front_y"], 0)
    # Establish the split's lateral tent first, then tilt the entire assembled
    # keyboard toward the user. Reversing these rotations swings the rear
    # centre edges inward and makes otherwise separated gasket tongues collide.
    result.rotate(pivot, App.Vector(0, 1, 0),
                  -layout["tent_deg"] if side == "left" else layout["tent_deg"])
    result.rotate(pivot, App.Vector(1, 0, 0),
                  layout["typing_rotation_deg"])
    result.translate(App.Vector(0, 0, z))
    return result


def place_centre(shape, layout, z):
    """Place a centre component on the common typing plane without tent."""
    result = shape.copy()
    pivot = App.Vector(layout["axis_x"], layout["front_y"], 0)
    result.rotate(pivot, App.Vector(1, 0, 0),
                  layout["typing_rotation_deg"])
    result.translate(App.Vector(0, 0, z))
    return result


def placed_point(point, layout, side, z):
    """Apply the same rigid transforms used for a PCB or centre component."""
    result = App.Vector(*point)
    pivot = App.Vector(layout["axis_x"], layout["front_y"], 0)
    if side in ("left", "right"):
        angle = -layout["tent_deg"] if side == "left" else layout["tent_deg"]
        result = App.Rotation(App.Vector(0, 1, 0), angle).multVec(
            result - pivot) + pivot
    result = App.Rotation(App.Vector(1, 0, 0),
                          layout["typing_rotation_deg"]).multVec(
                              result - pivot) + pivot
    result.z += z
    return result


def cable_segment(start, end, width=12.0, thickness=0.30):
    delta = end.sub(start)
    if delta.Length < 1e-6:
        raise ValueError("zero-length ribbon segment")
    body = Part.makeBox(delta.Length, width, thickness,
                        App.Vector(0, -width / 2, -thickness / 2))
    body.Placement = App.Placement(
        start, App.Rotation(App.Vector(1, 0, 0), delta))
    return body


def cable_path(points):
    return Part.makeCompound([
        cable_segment(start, end) for start, end in zip(points, points[1:])
    ])


def connector_xy(layout, body, reference):
    record = layout[body]
    x, y = record["reference_footprints"][reference]["position"]
    target = record.get("assembly_centre", record["centre"])
    return (x + target[0] - record["centre"][0],
            y + target[1] - record["centre"][1])


def centred_box(width, depth, height, z):
    return Part.makeBox(width, depth, height,
                        App.Vector(-width / 2, -depth / 2, z))


def native_component(shape, position, rotation):
    """Place a component solid in KiCad's native board coordinate frame."""
    result = shape.copy()
    # STEP export uses conventional Y-up while pcbnew records screen-space
    # Y-down coordinates.  Mirror both the coordinate and planar rotation so
    # this procedural fallback follows the same frame as KiCad's real models.
    result.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), -rotation)
    result.translate(App.Vector(position[0], -position[1], 0))
    return result


def official_component_shape(record, model_path, board_thickness,
                             rotations=(), offset=(0.0, 0.0, 0.0),
                             seat_on_board=False):
    """Place an unmodified supplier/manufacturer STEP on a KiCad footprint.

    ``align_board_coordinates`` later applies a 180 degree X rotation to the
    complete KiCad component compound.  Front-side additions therefore get
    the inverse rotation here.  For a back-side footprint that inverse cancels
    KiCad's physical board-side flip, leaving the source STEP translated to the
    far face of the configured stackup.  This preserves the downloaded model
    bytes while keeping the final assembly in KiCad's screen-space frame.
    """
    local = import_step_shape(model_path)
    axes = {
        "x": App.Vector(1, 0, 0),
        "y": App.Vector(0, 1, 0),
        "z": App.Vector(0, 0, 1),
    }
    for axis, angle in rotations:
        local.rotate(App.Vector(0, 0, 0), axes[axis], angle)
    if seat_on_board:
        # Supplier STEP origins are not consistent: some passives are centred
        # on Z=0 while most ICs use the pad seating plane.  A rigid Z shift to
        # the lowest model point preserves the exact geometry while placing the
        # fitted SMD body on its physical board face.
        local.translate(App.Vector(0, 0, -local.BoundBox.ZMin))
    local.translate(App.Vector(*offset))
    if record["side"] == "F.Cu":
        local.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 180)
    elif record["side"] == "B.Cu":
        local.translate(App.Vector(0, 0, board_thickness))
    else:
        raise ValueError(f"unsupported footprint side: {record['side']}")
    return native_component(local, record["position"],
                            record["rotation_deg"])


def official_component_shapes(layout, body):
    """Return exact-part models for every fitted electrical component."""
    references = layout[body]["reference_footprints"]
    board_thickness = layout[body]["configured_board_thickness_mm"]
    shapes = []
    coverage = []
    for record in layout[body]["fitted_footprints"]:
        reference = record["reference"]
        value = record["value"]
        base = {key: record[key] for key in
                ("reference", "value", "footprint", "side", "dnp")}
        if record["dnp"]:
            coverage.append({**base, "status": "not fitted (DNP)"})
            continue
        if value == "M2_NPTH":
            coverage.append({**base, "status": "board aperture; no fitted body"})
            continue
        if value == "STAB_MX":
            coverage.append({
                **base,
                "status": "unresolved mechanical identity",
                "reason": "BOM says Cherry PCB-mount stabiliser but gives no "
                          "manufacturer part number",
            })
            continue
        if body == "DaughterboardPCB" and reference == "J1":
            continue
        if value not in VALUE_MODELS:
            raise RuntimeError(
                f"{body} {reference}: no exact model mapping for {value}")
        model_key, lcsc, identity = VALUE_MODELS[value]
        spec = COMPONENT_MODELS[model_key]
        shapes.append(official_component_shape(
            record, OFFICIAL_MODELS / spec["file"], board_thickness,
            rotations=spec["rotations"], seat_on_board=spec["seat"]))
        coverage.append({
            **base, "status": "exact part-linked model",
            "identity": identity, "lcsc": lcsc,
            "model": spec["file"], "source": spec["source"],
        })
    if body == "DaughterboardPCB" and "J1" in references:
        # Reuse the exact HRO solid and native coordinate frame from the first
        # validated assembly (f18a949).  That assembly explicitly rotated this
        # vendor body through J1's 180-degree angle before aligning its mating
        # mouth with the rear wall.  The current generic component pipeline also
        # applies J1's footprint angle, so this pre-rotation counteracts that
        # frame conversion and leaves the original body facing outward.  Its
        # 0.6 mm datum shift preserves the requested projection through the
        # daughterboard wall after the later board-coordinate inversion.
        usb_shape = official_component_shape(
            references["J1"],
            OFFICIAL_MODELS / "HRO_TYPE-C-31-M-12_C165948.step",
            board_thickness, rotations=(("z", 180),),
            offset=(0.0, 0.6, 0.0))
        # Check the un-tilted assembly frame, where the rear wall is the
        # daughterboard's minimum-Y edge.  This makes both the direction and
        # the intended case-wall projection explicit rather than relying on a
        # camera view of the finished assembly.
        checked_usb = align_board_coordinates(
            usb_shape, layout[body]["centre"], layout[body]["centre"])
        rear_edge_y = layout[body]["bounds"][1]
        overhang = rear_edge_y - checked_usb.BoundBox.YMin
        if abs(overhang - 0.6) > 0.02:
            raise RuntimeError(
                f"USB-C rear projection is {overhang:.3f} mm; expected 0.600")
        (GEN / "usb-placement.json").write_text(json.dumps({
            "model": "HRO_TYPE-C-31-M-12_C165948.step",
            "model_body_rotation_deg": 180.0,
            "opening_edge": "rear/min-y",
            "rear_edge_y_mm": rear_edge_y,
            "shell_min_y_mm": checked_usb.BoundBox.YMin,
            "overhang_mm": overhang,
        }, indent=2) + "\n")
        shapes.append(usb_shape)
        record = next(item for item in layout[body]["fitted_footprints"]
                      if item["reference"] == "J1")
        coverage.append({
            **{key: record[key] for key in
               ("reference", "value", "footprint", "side", "dnp")},
            "status": "exact vendor model", "identity": "HRO TYPE-C-31-M-12",
            "lcsc": "C165948",
            "model": "HRO_TYPE-C-31-M-12_C165948.step",
            "source": "validated exact vendor solid",
        })
    # Special-case bodies such as the USB connector are constructed after the
    # general loop, but the audit manifest must retain the PCB's authoritative
    # footprint order so it can be compared record-for-record.
    footprint_order = {
        item["reference"]: index
        for index, item in enumerate(layout[body]["fitted_footprints"])
    }
    coverage.sort(key=lambda item: footprint_order[item["reference"]])
    return shapes, coverage


def at_key(shape, key):
    """Place a local solid at a key centre in the un-tented plate plane."""
    result = shape.copy()
    result.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), key["rot"])
    result.translate(App.Vector(key["cx"] * U, key["cy"] * U, 0))
    return result


_ks20_local_parts = None


def rounded_prism(width, depth, height, z, radius):
    """A fillet-like rounded rectangular prism using exact analytic solids."""
    horizontal = Part.makeBox(
        width - 2 * radius, depth, height,
        App.Vector(-width / 2 + radius, -depth / 2, z))
    vertical = Part.makeBox(
        width, depth - 2 * radius, height,
        App.Vector(-width / 2, -depth / 2 + radius, z))
    corners = [
        Part.makeCylinder(radius, height, App.Vector(x, y, z))
        for x in (-width / 2 + radius, width / 2 - radius)
        for y in (-depth / 2 + radius, depth / 2 - radius)
    ]
    return horizontal.multiFuse([vertical, *corners])


def ks20_local_parts():
    """Detailed production-form KS-20 solids in the switch's local frame.

    Gateron does not publish its mold/production STEP.  This model therefore
    combines the exact DS-02-001-A0 mounting envelope with the separate bottom
    housing, transparent top housing, wall stem, spring and centre magnet shown
    in Gateron's official product and exploded views.  Keeping those real
    manufactured subassemblies separate produces useful visual and case-fit
    geometry without falsely presenting reverse-engineered internal surfaces
    as confidential OEM CAD.
    """
    global _ks20_local_parts
    if _ks20_local_parts is not None:
        return {name: shape.copy()
                for name, shape in _ks20_local_parts.items()}

    # Local Z=0 is the switch flange/plate-top seating plane. The main bottom
    # housing spans exactly five millimetres to the PCB top at Z=-5.
    bottom_body = rounded_prism(13.97, 13.97, 4.55, -5.00, 0.70)
    bottom_lip = rounded_prism(15.00, 14.70, 0.70, -0.70, 1.00)
    # Fuse the flange to the principal lower housing so one verifiable solid
    # spans the complete official five-millimetre PCB-to-plate datum. The
    # detailed ribs, clips, boss and locating pins remain separate solids.
    bottom_main = bottom_body.fuse(bottom_lip)
    bottom = Part.makeCompound([
        bottom_main,
        centred_box(11.6, 1.10, 2.8, -3.90),
        centred_box(1.10, 11.2, 2.8, -3.90),
        # Four side retention blocks and the visible closed-back acoustic boss.
        Part.makeBox(1.15, 4.20, 3.00, App.Vector(-7.50, -2.10, -3.80)),
        Part.makeBox(1.15, 4.20, 3.00, App.Vector(6.35, -2.10, -3.80)),
        Part.makeBox(4.20, 0.85, 2.80, App.Vector(-2.10, -7.35, -3.70)),
        Part.makeBox(4.20, 0.85, 2.80, App.Vector(-2.10, 6.50, -3.70)),
        Part.makeCylinder(3.05, 0.45, App.Vector(0, -7.35, -3.25),
                          App.Vector(0, 1, 0)),
        # The two 1.70 mm locating pins use the board's exact +/-5.08 centres.
        Part.makeCylinder(0.85, 2.70, App.Vector(-5.08, 0, -7.70)),
        Part.makeCylinder(0.85, 2.70, App.Vector(5.08, 0, -7.70)),
    ])

    # Sloped transparent upper housing. A central opening, front/back windows,
    # corner ears and diagonal ribs reproduce the manufactured top housing
    # instead of the earlier single closed loft.
    outer_top = Part.makeLoft([
        rectangle_wire(15.40, 15.10, 0.00),
        rectangle_wire(14.70, 14.40, 5.65),
    ], True)
    inner_opening = centred_box(8.70, 8.70, 6.20, 0.15)
    top_shell = outer_top.cut(inner_opening)
    windows = [
        Part.makeBox(7.6, 5.0, 3.2, App.Vector(-3.8, -9.0, 1.45)),
        Part.makeBox(7.6, 5.0, 3.2, App.Vector(-3.8, 4.0, 1.45)),
        Part.makeBox(5.0, 7.6, 3.2, App.Vector(-9.0, -3.8, 1.45)),
        Part.makeBox(5.0, 7.6, 3.2, App.Vector(4.0, -3.8, 1.45)),
    ]
    for window in windows:
        top_shell = top_shell.cut(window)
    top = Part.makeCompound([
        top_shell,
        rounded_prism(15.40, 15.10, 0.45, 0.00, 1.05),
        # Retention ears and four tall structural ribs visible in product views.
        Part.makeBox(2.8, 1.1, 1.2, App.Vector(-6.9, -7.55, 0.15)),
        Part.makeBox(2.8, 1.1, 1.2, App.Vector(4.1, -7.55, 0.15)),
        Part.makeBox(2.8, 1.1, 1.2, App.Vector(-6.9, 6.45, 0.15)),
        Part.makeBox(2.8, 1.1, 1.2, App.Vector(4.1, 6.45, 0.15)),
        Part.makeBox(0.75, 2.3, 4.10, App.Vector(-6.1, -1.15, 0.65)),
        Part.makeBox(0.75, 2.3, 4.10, App.Vector(5.35, -1.15, 0.65)),
        Part.makeBox(2.3, 0.75, 4.10, App.Vector(-1.15, -6.1, 0.65)),
        Part.makeBox(2.3, 0.75, 4.10, App.Vector(-1.15, 5.35, 0.65)),
    ])

    # White wall stem: guide shaft and broad paddle remain visible through the
    # clear housing, while the cap-facing cross keeps the drawing's exact
    # 4.00 x 1.30 mm dimensions and 11.10 mm maximum height.
    stem = Part.makeCompound([
        rounded_prism(9.10, 9.10, 1.35, 5.40, 0.65),
        Part.makeCylinder(2.25, 6.60, App.Vector(0, 0, -0.20)),
        centred_box(4.00, 1.30, 4.35, 6.75),
        centred_box(1.30, 4.00, 4.35, 6.75),
        Part.makeBox(1.05, 2.4, 3.6, App.Vector(-3.95, -1.2, 5.75)),
        Part.makeBox(1.05, 2.4, 3.6, App.Vector(2.90, -1.2, 5.75)),
    ])

    # A true swept helix gives the visible spring one continuous solid rather
    # than a stack of decorative toroids.
    spring_path = Part.makeHelix(0.90, 5.10, 3.05)
    spring_profile = Part.Wire([
        Part.makeCircle(0.22, App.Vector(3.05, 0, 0), App.Vector(0, 1, 0))
    ])
    spring = Part.Wire(spring_path.Edges).makePipeShell(
        [spring_profile], True, False)
    # Seat the spring inside the housing around the magnet/stem guide instead
    # of letting its visual envelope protrude through the transparent lid.
    spring.translate(App.Vector(0, 0, -3.70))
    magnet = Part.makeCylinder(2.05, 2.35, App.Vector(0, 0, -4.35))

    _ks20_local_parts = {
        "BottomHousing": bottom,
        "TopHousing": top,
        "Stem": stem,
        "Spring": spring,
        "Magnet": magnet,
    }
    return {name: shape.copy() for name, shape in _ks20_local_parts.items()}


def switch_part_shapes(key):
    """Place each real KS-20 subassembly at one physical key location."""
    return {name: at_key(shape, key)
            for name, shape in ks20_local_parts().items()}


def switch_shape(key):
    """Complete detailed Gateron KS-20 Magnetic Jade model at one key."""
    return Part.makeCompound(list(switch_part_shapes(key).values()))


def rectangle_wire(width, depth, z):
    points = [
        App.Vector(-width / 2, -depth / 2, z),
        App.Vector(width / 2, -depth / 2, z),
        App.Vector(width / 2, depth / 2, z),
        App.Vector(-width / 2, depth / 2, z),
        App.Vector(-width / 2, -depth / 2, z),
    ]
    return Part.makePolygon(points)


def keycap_row(key):
    """Map the five physical rows to GMK/Cherry's R1-R4 sculpt."""
    y = key["cy"]
    if y < 1.2:
        return 1
    if y < 2.2:
        return 2
    if y < 3.2:
        return 3
    return 4


def keycap_width_name(width):
    text = f"{width:.2f}".rstrip("0").rstrip(".")
    return text


def load_keycap_library():
    """Load the licensed row/width-specific Cherry-profile reference CAD."""
    global _keycap_library
    if _keycap_library is not None:
        return _keycap_library
    if not GMK_CYL_MODEL.is_file() or not GMK_CYL_LICENSE.is_file():
        raise RuntimeError("missing Cherry-profile keycap model or MIT license")
    temp = App.newDocument("GMKCYLReferenceImport")
    Import.insert(str(GMK_CYL_MODEL), temp.Name)
    library = {}
    pattern = re.compile(r"^(1x(?:1|1\.25|1\.5|1\.75|2|2\.25)) R([1-4])")
    for obj in temp.Objects:
        match = pattern.match(obj.Label)
        if (not match or not hasattr(obj, "Shape") or obj.Shape.isNull() or
                not obj.Shape.Solids):
            continue
        width = float(match.group(1)[2:])
        row = int(match.group(2))
        shape = obj.Shape.copy()
        # The source library uses +Y as keycap height and +Z as key depth.
        # Rotate into the assembly's Z-up frame, centre the cap on its stem,
        # and retain a realistic skirt height around the 11.10 mm KS-20 stem.
        shape.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 90)
        bb = shape.BoundBox
        shape.translate(App.Vector(-(bb.XMin + bb.XMax) / 2,
                                   -(bb.YMin + bb.YMax) / 2,
                                   KEYCAP_SKIRT_Z - bb.ZMin))
        library[(width, row)] = shape
    App.closeDocument(temp.Name)
    expected = {(width, row)
                for width in (1.0, 1.25, 1.5, 1.75, 2.0, 2.25)
                for row in range(1, 5)}
    missing = sorted(expected - set(library))
    if missing:
        raise RuntimeError(f"Cherry-profile CAD missing keys: {missing}")
    _keycap_library = library
    return library


def keycap_shape(key):
    """Row- and width-correct GMK CYL/Cherry-profile reference keycap."""
    lookup = (float(key["w"]), keycap_row(key))
    cap = load_keycap_library()[lookup].copy()
    return at_key(cap, key)


def minimum_pair_clearance(shapes):
    clearance = float("inf")
    collisions = []
    for index, first in enumerate(shapes):
        for other_index, second in enumerate(shapes[index + 1:], index + 1):
            distance = first.distToShape(second)[0]
            clearance = min(clearance, distance)
            if first.common(second).Volume > 1e-5:
                collisions.append((index, other_index))
    if collisions:
        raise RuntimeError(f"keycap collisions after GMK CYL placement: {collisions}")
    return clearance


def add_reference(doc, root, internal, label, shape, role, colour,
                  transparency=0):
    obj = doc.addObject("PartDesign::Feature", internal)
    obj.Label = label
    obj.Shape = shape
    obj.addProperty("App::PropertyString", "Role", "Reference")
    obj.Role = role
    # freecadcmd has no GUI ViewObject. Preserve intended display metadata as
    # ordinary properties so Fusion/FreeCAD users can style the groups after
    # import without making headless release generation depend on a GUI.
    obj.addProperty("App::PropertyString", "SuggestedColour", "Reference")
    obj.SuggestedColour = "%.3f, %.3f, %.3f" % colour
    obj.addProperty("App::PropertyInteger", "SuggestedTransparency",
                    "Reference")
    obj.SuggestedTransparency = transparency
    root.addObject(obj)
    return obj


def export_mesh_shape(doc, internal, shape, path):
    """Export one render-only shape without retaining duplicate FCStd bodies."""
    obj = doc.addObject("PartDesign::Feature", internal)
    obj.Shape = shape
    Mesh.export([obj], str(path))
    doc.removeObject(obj.Name)


def main():
    layout = json.loads((GEN / "reference-layout.json").read_text())
    doc = App.newDocument("Symm60HE_Reference_Assembly")
    root = doc.addObject("App::Part", "Symm60HEReferenceAssembly")
    root.Label = "Symm60HE case-design reference assembly"
    specs = [
        ("LeftPCB", "Left PCB", "LeftPCB.step", "left", layout["pcb_z"], True),
        ("RightPCB", "Right PCB", "RightPCB.step", "right", layout["pcb_z"], True),
        ("DaughterboardPCB", "Daughterboard PCB", "DaughterboardPCB.step",
         "centre", layout["daughterboard_z"], True),
        ("LeftPlate", "Left universal plate", "LeftPlate.stl", "left",
         layout["plate_z"], False),
        ("RightPlate", "Right universal plate", "RightPlate.stl", "right",
         layout["plate_z"], False),
    ]
    objects = []
    for internal, label, filename, side, z, is_step in specs:
        raw = (import_step_shape(GEN / filename) if is_step
               else solid_from_stl(GEN / filename))
        desired_centre = layout[internal].get(
            "assembly_centre", layout[internal]["centre"])
        aligned = align_xy(raw, desired_centre, mirror_y=is_step)
        colour = ((0.10, 0.34, 0.17) if "PCB" in internal
                  else (0.68, 0.70, 0.73))
        placed = (place_centre(aligned, layout, z) if side == "centre"
                  else place(aligned, layout, side, z))
        obj = add_reference(
            doc, root, internal, label, placed,
            "PCB reference" if "PCB" in internal else "plate reference",
            colour, 0 if "PCB" in internal else 25)
        objects.append(obj)
        Import.export([obj], str(OUT / f"Symm60HE-{internal}.step"))
        Mesh.export([obj], str(GEN / f"{internal}-placed.stl"))
        print(label, "volume", round(obj.Shape.Volume, 2), "mm^3")

    # Build every populated electrical component from an exact part-linked or
    # manufacturer STEP.  Do not layer these over KiCad's generic package
    # bodies: that would create doubled, intersecting components.
    component_specs = (
        ("LeftPCBComponents", "Left PCB components", "LeftPCB", "left",
         layout["pcb_z"]),
        ("RightPCBComponents", "Right PCB components", "RightPCB", "right",
         layout["pcb_z"]),
        ("DaughterboardPCBComponents", "Daughterboard components",
         "DaughterboardPCB", "centre", layout["daughterboard_z"]),
    )
    component_coverage = {}
    for internal, label, body, side, z in component_specs:
        exact_shapes, coverage = official_component_shapes(layout, body)
        if not exact_shapes:
            raise RuntimeError(f"{body}: no fitted component solids")
        raw = Part.makeCompound(exact_shapes)
        component_coverage[body] = coverage
        desired_centre = layout[body].get(
            "assembly_centre", layout[body]["centre"])
        aligned = align_board_coordinates(
            raw, layout[body]["centre"], desired_centre)
        placed = (place_centre(aligned, layout, z) if side == "centre"
                  else place(aligned, layout, side, z))
        obj = add_reference(
            doc, root, internal, label, placed,
            "exact part-number-linked fitted component models",
            (0.24, 0.25, 0.27))
        objects.append(obj)
        Import.export([obj], str(OUT / f"Symm60HE-{internal}.step"))
        Mesh.export([obj], str(GEN / f"{internal}-placed.stl"))
        print(label, "volume", round(obj.Shape.Volume, 2), "mm^3",
              "solids", len(obj.Shape.Solids))
    (GEN / "component-model-coverage.json").write_text(json.dumps({
        "policy": "Every fitted electrical footprint uses an exact "
                  "manufacturer or exact LCSC-part-linked model.",
        "boards": component_coverage,
        "known_non_electrical_exception": {
            "value": "STAB_MX",
            "reason": "The BOM does not specify a stabilizer manufacturer "
                      "part number, so no production solid can be certified."
        },
    }, indent=2) + "\n")

    # Visible 12-way ribbon clearance envelopes connect the actual current FPC
    # coordinates. They drop below the gasket-loaded plate planes before
    # crossing toward the centered rear daughterboard.
    ribbon_specs = (
        ("Left", "LeftPCB", "JL1", "left", "J2"),
        ("Right", "RightPCB", "JR1", "right", "J3"),
    )
    for label, half_body, half_ref, side, daughter_ref in ribbon_specs:
        hx, hy = connector_xy(layout, half_body, half_ref)
        dx, dy = connector_xy(layout, "DaughterboardPCB", daughter_ref)
        # The half-board connectors are on B.Cu, so the cable starts just
        # below each Hall PCB. The daughterboard connectors are top-contact
        # parts on F.Cu; rise outside the board outline, then land across the
        # upper surface from each connector's outward-facing side.
        half_end = placed_point((hx, hy, -1.35), layout, side,
                                layout["pcb_z"])
        daughter_top = placed_point((dx, dy, 0.35), layout, "centre",
                                    layout["daughterboard_z"])
        service_z = min(half_end.z, daughter_top.z) - 3.0
        outside_x = dx - 10.0 if side == "left" else dx + 10.0
        outside_top = placed_point((outside_x, dy, 0.35), layout, "centre",
                                   layout["daughterboard_z"])
        points = [
            half_end,
            App.Vector(half_end.x, half_end.y - 4.0, service_z),
            App.Vector(outside_top.x, outside_top.y + 4.0, service_z),
            outside_top,
        ]
        # Build the final connector entry directly in the daughterboard's
        # local top plane. This keeps the complete landing strip above F.Cu
        # instead of allowing an arbitrarily rolled 3D segment to clip FR-4.
        landing = Part.makeBox(
            abs(dx - outside_x), 12.0, 0.30,
            App.Vector(min(dx, outside_x), dy - 6.0, 0.20))
        landing = place_centre(landing, layout, layout["daughterboard_z"])
        ribbon = Part.makeCompound([cable_path(points), landing])
        internal = label + "RibbonCable"
        obj = add_reference(
            doc, root, internal, label + " 12-way ribbon cable",
            ribbon,
            "0.3 mm FFC route and service-loop clearance envelope",
            (0.20, 0.55, 0.90), 25)
        objects.append(obj)
        Import.export([obj], str(OUT / f"Symm60HE-{internal}.step"))
        Mesh.export([obj], str(GEN / f"{internal}-placed.stl"))
        length = (sum(end.sub(start).Length
                      for start, end in zip(points, points[1:])) +
                  abs(dx - outside_x))
        print(label, "ribbon length path", round(length, 2), "mm")

    selected = [key for key in KEYS
                if layout["visual_layout"] in key["builds"]]
    # Emit one inspectable, multi-solid KS-20 model beside the source drawing.
    # Every switch bank below is made from rigid copies of these same solids.
    switch_model_path = (
        REFERENCE_MODELS / "gateron-ks20-magnetic-jade" /
        "Gateron-KS20-Magnetic-Jade-detailed-reference.step")
    prototype_parts = ks20_local_parts()
    prototype_objects = []
    prototype_names = {
        "BottomHousing": "KS20 bottom housing",
        "TopHousing": "KS20 transparent top housing",
        "Stem": "KS20 wall stem",
        "Spring": "KS20 spring",
        "Magnet": "KS20 centre magnet",
    }
    for part_name, shape in prototype_parts.items():
        obj = doc.addObject("PartDesign::Feature", "KS20Prototype" + part_name)
        obj.Label = prototype_names[part_name]
        obj.Shape = shape
        prototype_objects.append(obj)
    Import.export(prototype_objects, str(switch_model_path))
    for obj in prototype_objects:
        doc.removeObject(obj.Name)
    switch_model_sha256 = sha256(switch_model_path.read_bytes()).hexdigest()
    model_record = {
        "visual_layout": layout["visual_layout"],
        "switch": {
            "manufacturer": "Gateron",
            "part": "KS-20 Magnetic Jade KS-20TF10B045NW-Y89",
            "source_type": "detailed multi-part production-form reconstruction "
                           "from official drawing and product views",
            "source": "https://www.gateron.com/u_file/2406/28/file/"
                      "GATERONMagneticJadeSwitch-KS-20TF10B045NW-Y89.pdf",
            "drawing": "DS-02-001-A0",
            "local_source": str(GATERON_JADE_SPEC.relative_to(ROOT)),
            "sha256": sha256(GATERON_JADE_SPEC.read_bytes()).hexdigest(),
            "detailed_model": str(switch_model_path.relative_to(ROOT)),
            "detailed_model_sha256": switch_model_sha256,
            "subassemblies": list(prototype_names.values()),
            "dimensions_mm": {
                "upper_envelope": [15.40, 15.10],
                "plate_body": 13.97,
                "height_above_pcb": 11.10,
                "lower_body": 5.00,
                "mx_cross": [4.00, 1.30],
                "alignment_pin_diameter": 1.70,
                "alignment_pin_centres": [-5.08, 5.08],
                "travel": 3.50,
                "plate_seating_plane_to_pcb_top": 5.00,
            },
        },
        "keycaps": {
            "target": "GMK CYL (original Cherry profile)",
            "source_type": "licensed full thin-wall Cherry-profile CAD "
                           "measured from molded keycaps",
            "source": "https://github.com/ConstantinoSchillebeeckx/"
                      "cherry-mx-keycaps",
            "source_revision": "2fa89ef205e4b1529d82fd33cef4e46f057760b1",
            "local_source": str(GMK_CYL_MODEL.relative_to(ROOT)),
            "sha256": sha256(GMK_CYL_MODEL.read_bytes()).hexdigest(),
            "license": "MIT",
            "license_file": str(GMK_CYL_LICENSE.relative_to(ROOT)),
            "gmk_public_specification": {
                "profile": "CYL / original Cherry profile",
                "material": "double-shot ABS",
                "wall_thickness_mm": 1.5,
                "mount": "MX cross",
            },
            "rows": "R1, R2, R3, R4, R4",
        },
        "sides": {},
    }
    for side_name, side_code in (("Left", "L"), ("Right", "R")):
        keys = [key for key in selected if key["half"] == side_code]
        side = side_name.lower()
        switch_parts = {name: [] for name in prototype_names}
        switch_shapes = []
        for key in keys:
            placed_parts = switch_part_shapes(key)
            for name, shape in placed_parts.items():
                switch_parts[name].append(shape)
            switch_shapes.append(Part.makeCompound(list(placed_parts.values())))
        keycap_shapes = [keycap_shape(key) for key in keys]
        cap_clearance = minimum_pair_clearance(keycap_shapes)
        switches = Part.makeCompound(switch_shapes)
        keycaps = Part.makeCompound(keycap_shapes)
        switch_obj = add_reference(
            doc, root, side_name + "Switches", side_name + " switches",
            place(switches, layout, side, layout["plate_seating_z"]),
            "Gateron KS-20 Magnetic Jade detailed multi-part real-form model",
            (0.42, 0.78, 0.69), 4)
        keycap_obj = add_reference(
            doc, root, side_name + "Keycaps", side_name + " keycaps",
            place(keycaps, layout, side, layout["plate_seating_z"]),
            "GMK CYL / Cherry-profile full thin-wall CAD model",
            (0.83, 0.84, 0.80), 0)
        objects.extend((switch_obj, keycap_obj))
        Import.export([switch_obj],
                      str(OUT / f"Symm60HE-{side_name}Switches.step"))
        Import.export([keycap_obj],
                      str(OUT / f"Symm60HE-{side_name}Keycaps.step"))
        Mesh.export([switch_obj],
                    str(GEN / f"{side_name}Switches-placed.stl"))
        # Preserve manufactured subassemblies as separate colored render
        # meshes while keeping one switch-bank body in the editable assembly.
        for part_name, part_shapes in switch_parts.items():
            part_bank = Part.makeCompound(part_shapes)
            part_bank = place(
                part_bank, layout, side, layout["plate_seating_z"])
            export_mesh_shape(
                doc, f"{side_name}{part_name}Render", part_bank,
                GEN / f"{side_name}Switch{part_name}s-placed.stl")
        Mesh.export([keycap_obj],
                    str(GEN / f"{side_name}Keycaps-placed.stl"))
        model_record["sides"][side_name] = {
            "switch_count": len(keys),
            "keycap_count": len(keys),
            "keycap_minimum_clearance_mm": cap_clearance,
            "row_counts": {
                f"R{row}": sum(keycap_row(key) == row for key in keys)
                for row in range(1, 5)
            },
            "width_counts": {
                keycap_width_name(width): sum(key["w"] == width for key in keys)
                for width in sorted({key["w"] for key in keys})
            },
        }
        print(side_name, len(keys), "detailed Gateron KS-20 models and",
              len(keys), "full Cherry-profile keycap CAD models; minimum clearance",
              round(cap_clearance, 3), "mm")
    (GEN / "switch-keycap-model-provenance.json").write_text(
        json.dumps(model_record, indent=2) + "\n")
    doc.recompute()
    Import.export(objects, str(OUT / "Symm60HE-reference-assembly.step"))
    source = OUT / "Symm60HE-reference-assembly.FCStd"
    # This is a generated handoff, so replace it cleanly instead of asking
    # FreeCAD to create timestamped .FCBak files in the active case directory.
    if source.exists():
        source.unlink()
    doc.saveAs(str(source))
    print("wrote", OUT / "Symm60HE-reference-assembly.step")
    print("wrote", OUT / "Symm60HE-reference-assembly.FCStd")


if __name__ == "__main__":
    main()
