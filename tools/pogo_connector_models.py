"""Exact Mill-Max 854/856 connector geometry for FreeCAD references.

The source solids are the exact 12-position supplier STEP configurations. The
854 file describes the uncompressed contact position, so the visible assembly
uses that geometry with only the exposed moving ends translated into the
selected working position. The housing and board-side portions are unchanged.
"""
from functools import lru_cache
from pathlib import Path

import FreeCAD as App
import Import
import Part

CONTACTS = 12
PITCH = 1.27
BODY_LENGTH = 15.621
BODY_DEPTH = 2.2098

# Values measured from the exact configured supplier STEP files. Native Y=0
# is the housing/PCB seating plane and negative Y points toward the mate.
SPRING_INITIAL_HEIGHT = 3.0480
SPRING_STROKE = 1.0160
TARGET_PROJECTION = 2.2098

# A 5.0 mm board-surface separation preloads the spring by 0.2578 mm while
# retaining 0.7582 mm of its published 1.016 mm travel. The former 6.0 mm
# placeholder spacing left a 0.7422 mm open contact gap with the exact models.
BOARD_SPACING = 5.0
SPRING_WORKING_HEIGHT = BOARD_SPACING - TARGET_PROJECTION
SPRING_COMPRESSION = SPRING_INITIAL_HEIGHT - SPRING_WORKING_HEIGHT

VENDOR = (Path(__file__).resolve().parent.parent / "case" / "fusion360" /
          "models" / "vendor")
SPRING_STEP = VENDOR / "Mill-Max_854-22-012-30-004101.step"
TARGET_STEP = VENDOR / "Mill-Max_856-10-012-30-051000.step"


def cbox(width, depth, height, z=0.0):
    return Part.makeBox(width, depth, height,
                        App.Vector(-width / 2, -depth / 2, z))


@lru_cache(maxsize=2)
def _supplier_shape(path_text):
    path = Path(path_text)
    if not path.exists():
        raise FileNotFoundError(
            f"exact Mill-Max STEP is required for the Fusion reference: {path}")
    doc = App.newDocument("MillMaxImport")
    Import.insert(str(path), doc.Name)
    candidates = [obj.Shape for obj in doc.Objects
                  if (hasattr(obj, "Shape") and not obj.Shape.isNull() and
                      obj.Shape.Solids and 1e-6 < abs(obj.Shape.Volume) < 1e12)]
    if not candidates:
        App.closeDocument(doc.Name)
        raise RuntimeError(f"STEP contained no solid assembly: {path}")
    # 3D ContentCentral includes individual occurrences and one complete
    # assembly. Taking the greatest solid count avoids duplicating both.
    result = max(candidates,
                 key=lambda shape: (len(shape.Solids), abs(shape.Volume))).copy()
    App.closeDocument(doc.Name)
    return result


def _centred_native(path):
    """Centre the supplier row/depth axes while retaining its Y seating datum."""
    result = _supplier_shape(str(path)).copy()
    bb = result.BoundBox
    result.translate(App.Vector(-bb.Center.x, 0, -bb.Center.z))
    return result


def spring_connector(z=0.0, height=SPRING_WORKING_HEIGHT):
    """854 exact supplier model in a derived, physically seated working pose.

    The imported housing is stationary. Only each pin's portion beyond the
    housing face moves into the body, preserving all supplier cross-sections
    and the exact 12-position pitch instead of scaling the connector.
    """
    if not SPRING_INITIAL_HEIGHT - SPRING_STROKE <= height <= SPRING_INITIAL_HEIGHT:
        raise ValueError("spring height is outside the published stroke")
    native = _centred_native(SPRING_STEP)
    solids = sorted(native.Solids,
                    key=lambda solid: abs(solid.Volume), reverse=True)
    housing, pins = solids[0], solids[1:]
    split_y = housing.BoundBox.YMin
    amount = SPRING_INITIAL_HEIGHT - height
    pieces = [housing.copy()]
    margin = 10.0
    for pin in pins:
        bb = pin.BoundBox
        fixed_box = Part.makeBox(
            bb.XLength + 2*margin, bb.YMax - split_y + margin,
            bb.ZLength + 2*margin,
            App.Vector(bb.XMin-margin, split_y, bb.ZMin-margin))
        moving_box = Part.makeBox(
            bb.XLength + 2*margin, split_y - bb.YMin + margin,
            bb.ZLength + 2*margin,
            App.Vector(bb.XMin-margin, bb.YMin-margin, bb.ZMin-margin))
        fixed = pin.common(fixed_box)
        moving = pin.common(moving_box)
        moving.translate(App.Vector(0, amount, 0))
        pieces.extend([fixed, moving])
    result = Part.makeCompound(pieces)
    # Supplier -Y becomes assembly +Z; the exact PCB/housing datum stays at z.
    result.rotate(App.Vector(), App.Vector(1, 0, 0), -90)
    result.translate(App.Vector(0, 0, z))
    return result

def spring_motion_envelope(z=0.0):
    """Maximum free-height envelope of the exact 854 supplier model."""
    result = _centred_native(SPRING_STEP)
    result.rotate(App.Vector(), App.Vector(1, 0, 0), -90)
    result.translate(App.Vector(0, 0, z))
    return result


def target_connector(z=0.0, height=TARGET_PROJECTION):
    """Exact 856 supplier model with its mating face at assembly ``z``."""
    if abs(height - TARGET_PROJECTION) > 1e-6:
        raise ValueError("exact target model has a fixed projection")
    result = _centred_native(TARGET_STEP)
    # Supplier -Y becomes assembly -Z. Native Y=0 is the housing seat, so the
    # mating face lands at -TARGET_PROJECTION before the final translation.
    result.rotate(App.Vector(), App.Vector(1, 0, 0), 90)
    result.translate(App.Vector(0, 0, z + TARGET_PROJECTION))
    return result
