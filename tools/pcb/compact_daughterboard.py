#!/usr/bin/env python3
"""Compact the daughterboard, center USB-C, and provide four case mounts."""

import argparse
import math

import wx
import pcbnew


X0 = 162.709
X1 = 211.709
Y0 = -6.7633
Y1 = 20.2367
RADIUS = 1.0


def mm_point(x, y):
    return pcbnew.VECTOR2I_MM(x, y)


def rounded_rectangle_points(x0, y0, x1, y1, radius, steps=16):
    points = [(x0 + radius, y0), (x1 - radius, y0)]
    corners = (
        (x1 - radius, y0 + radius, -90, 0),
        (x1 - radius, y1 - radius, 0, 90),
        (x0 + radius, y1 - radius, 90, 180),
        (x0 + radius, y0 + radius, 180, 270),
    )
    for cx, cy, start, end in corners:
        for index in range(1, steps + 1):
            angle = math.radians(start + (end - start) * index / steps)
            points.append((cx + radius * math.cos(angle),
                           cy + radius * math.sin(angle)))
        if (cx, cy) == (x1 - radius, y0 + radius):
            points.append((x1, y1 - radius))
        elif (cx, cy) == (x1 - radius, y1 - radius):
            points.append((x0 + radius, y1))
        elif (cx, cy) == (x0 + radius, y1 - radius):
            points.append((x0, y0 + radius))
    return points


def set_position(board, reference, x, y, rotation=None):
    footprint = board.FindFootprintByReference(reference)
    if footprint is None:
        raise RuntimeError("missing footprint " + reference)
    footprint.SetPosition(mm_point(x, y))
    if rotation is not None:
        footprint.SetOrientationDegrees(rotation)
    return footprint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)

    # The new outline center is exactly 187.209 mm.
    set_position(board, "J1", 187.209, -3.1133, 180.0)

    # Four 2.2 mm NPTH case mounts.  J2 and J3 occupy the side edges, so the
    # right pair is inset enough to clear J3's mechanical pads.
    mount = set_position(board, "MHD1", 164.5, -3.7633)
    set_position(board, "MHD2", 206.0, 17.5)
    for reference, x, y in (("MHD3", 206.0, -3.7633),
                            ("MHD4", 164.5, 17.5)):
        duplicate = pcbnew.Cast_to_FOOTPRINT(mount.Duplicate(False))
        duplicate.SetReference(reference)
        duplicate.SetPosition(mm_point(x, y))
        board.Add(duplicate)

    # Clear the new USB position and the upper-right mounting hole.  These are
    # placement-only changes; all affected nets are rerouted afterward.
    moves = {
        "SW1": (175.5, -3.2633),
        "R4": (195.0, -0.5),
        "U6": (201.0, -3.8),
        "F1": (207.5, -1.6),
        "R6": (204.0, -1.0),
        "C17": (205.5, 0.0),
        "C12": (203.0, 0.0),
        "C1": (204.5, 1.0),
    }
    for reference, position in moves.items():
        set_position(board, reference, *position)

    # Replace the old 57 mm-wide outline with a 49 mm-wide rounded rectangle.
    # Do this after footprint edits: pcbnew's SWIG ownership for newly added
    # drawing items can otherwise invalidate later footprint proxy objects.
    # The right edge and full 27 mm height stay fixed; the left FPC body is now
    # nearly flush with the new left edge.
    for drawing in list(board.GetDrawings()):
        if drawing.GetLayer() == pcbnew.Edge_Cuts:
            board.Remove(drawing)
    points = rounded_rectangle_points(X0, Y0, X1, Y1, RADIUS)
    edges = []
    for start, end in zip(points, points[1:]):
        edge = pcbnew.PCB_SHAPE(board)
        edge.SetShape(pcbnew.SHAPE_T_SEGMENT)
        edge.SetLayer(pcbnew.Edge_Cuts)
        edge.SetWidth(pcbnew.FromMM(0.10))
        edge.SetStart(mm_point(*start))
        edge.SetEnd(mm_point(*end))
        board.Add(edge)
        edges.append(edge)

    if not pcbnew.SaveBoard(args.output, board):
        raise RuntimeError("board save failed")
    print("wrote compact 49.0 x 27.0 mm daughterboard with four mounts")


if __name__ == "__main__":
    main()
