#!/usr/bin/env python3
"""Print FreeCAD geometry bounds for one or more STEP reference models."""
from pathlib import Path
import sys

import FreeCAD as App
import Import


def inspect(path):
    doc = App.newDocument("InspectSTEP")
    Import.insert(str(path), doc.Name)
    shapes = [obj.Shape for obj in doc.Objects
              if hasattr(obj, "Shape") and not obj.Shape.isNull()]
    solids = [solid for shape in shapes for solid in shape.Solids]
    if not solids:
        raise RuntimeError(f"STEP contained no solids: {path}")
    compound = solids[0] if len(solids) == 1 else __import__("Part").makeCompound(solids)
    bb = compound.BoundBox
    print(f"{path}: solids={len(solids)} "
          f"size={bb.XLength:.6f} x {bb.YLength:.6f} x {bb.ZLength:.6f} mm "
          f"min=({bb.XMin:.6f}, {bb.YMin:.6f}, {bb.ZMin:.6f}) "
          f"max=({bb.XMax:.6f}, {bb.YMax:.6f}, {bb.ZMax:.6f})")
    App.closeDocument(doc.Name)


for argument in sys.argv[1:]:
    inspect(Path(argument).resolve())
