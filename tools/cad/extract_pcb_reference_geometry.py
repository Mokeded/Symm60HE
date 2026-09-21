#!/usr/bin/env python3
"""Extract authoritative Edge.Cuts bounds for Fusion reference generation.

This helper must run under KiCad's bundled Python because it imports pcbnew.
The reported physical outline follows the Edge.Cuts centreline; KiCad's board
edge bounding box includes half of the drawing stroke on every side, so the
uniform stroke is removed from that box before it is written.
"""
from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path

import wx
import pcbnew


REFERENCE_FOOTPRINTS = {
    "LeftPCB": ("JL1",),
    "RightPCB": ("JR1",),
    "DaughterboardPCB": ("J1", "J2", "J3", "SW1", "SW2"),
}


def mm(value):
    return value / 1_000_000.0


def board_geometry(name, path):
    board = pcbnew.LoadBoard(str(path))
    edges = [drawing for drawing in board.GetDrawings()
             if drawing.GetLayer() == pcbnew.Edge_Cuts]
    if not edges:
        raise RuntimeError(f"{path}: no Edge.Cuts geometry")
    widths = {drawing.GetWidth() for drawing in edges}
    if len(widths) != 1:
        raise RuntimeError(f"{path}: Edge.Cuts uses mixed stroke widths")
    half_stroke = mm(next(iter(widths))) / 2.0
    box = board.GetBoardEdgesBoundingBox()
    xmin = mm(box.GetX()) + half_stroke
    ymin = mm(box.GetY()) + half_stroke
    xmax = mm(box.GetRight()) - half_stroke
    ymax = mm(box.GetBottom()) - half_stroke
    footprints = {}
    for reference in REFERENCE_FOOTPRINTS.get(name, ()):
        footprint = board.FindFootprintByReference(reference)
        if footprint is None:
            raise RuntimeError(f"{path}: missing reference footprint {reference}")
        position = footprint.GetPosition()
        footprints[reference] = {
            "position": [mm(position.x), mm(position.y)],
            "rotation_deg": footprint.GetOrientationDegrees(),
            "side": footprint.GetLayerName(),
            "value": footprint.GetValue(),
        }
    return {
        "name": name,
        "source": str(path),
        "sha256": sha256(path.read_bytes()).hexdigest(),
        "centre": [(xmin + xmax) / 2.0, (ymin + ymax) / 2.0],
        "bounds": [xmin, ymin, xmax, ymax],
        "size": [xmax - xmin, ymax - ymin],
        "edge_item_count": len(edges),
        "edge_stroke_mm": half_stroke * 2.0,
        "configured_board_thickness_mm": mm(
            board.GetDesignSettings().GetBoardThickness()),
        "reference_footprints": footprints,
    }


def main():
    parser = ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("boards", nargs="+", metavar="NAME=PATH")
    args = parser.parse_args()
    app = wx.App(False)
    result = {}
    for spec in args.boards:
        name, separator, raw_path = spec.partition("=")
        if not separator or not name or not raw_path:
            parser.error(f"invalid board specification: {spec}")
        path = Path(raw_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        result[name] = board_geometry(name, path)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    del app


if __name__ == "__main__":
    main()
