#!/usr/bin/env python3
"""Mirror daughterboard FPC connectors and case mounts about board center."""

import argparse

import wx
import pcbnew


CENTER_X = 187.209
CENTER_Y = 6.7367


def move(board, reference, x, y):
    footprint = board.FindFootprintByReference(reference)
    if footprint is None:
        raise RuntimeError("missing footprint " + reference)
    footprint.SetPosition(pcbnew.VECTOR2I_MM(x, y))


def expand_side_edges(board):
    """Add 0.5 mm of FR-4 beyond each FPC while preserving rounded corners."""
    left_corner_center = 163.709
    right_corner_center = 210.709

    def shifted(point):
        x = pcbnew.ToMM(point.x)
        y = pcbnew.ToMM(point.y)
        if x <= left_corner_center + 0.0001:
            x -= 0.5
        elif x >= right_corner_center - 0.0001:
            x += 0.5
        return pcbnew.VECTOR2I_MM(x, y)

    for drawing in board.GetDrawings():
        if drawing.GetLayer() != pcbnew.Edge_Cuts:
            continue
        drawing.SetStart(shifted(drawing.GetStart()))
        drawing.SetEnd(shifted(drawing.GetEnd()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)

    # Expand the 49 mm outline symmetrically to 50 mm.  Connector positions
    # stay fixed, leaving 0.5 mm of laminate beyond both sets of FPC fingers.
    expand_side_edges(board)

    # Side connector pad tips meet the board edges equally.  Their centers are
    # exact mirrors about the USB/outline centerline.
    move(board, "J2", 164.909, 8.7367)
    move(board, "J3", 209.509, 8.7367)

    # Initial compact-board mounting rectangle.  The finished routed board is
    # subsequently enlarged at the bottom and moved to its 44 mm-wide
    # perimeter rectangle by `relocate_daughterboard_mounts.py`.
    left = 175.500
    right = 2 * CENTER_X - left
    top = -3.7633
    bottom = 2 * CENTER_Y - top
    move(board, "MHD1", left, top)
    move(board, "MHD3", right, top)
    move(board, "MHD4", left, bottom)
    move(board, "MHD2", right, bottom)

    # Clear the symmetric mounting rectangle while retaining short local
    # routes for the reset/boot controls and RGB buffers.
    relocations = {
        "SW1": (175.0, 3.5),
        "SW2": (181.5, 16.2),
        "U4": (180.0, 11.0),
        "R5": (176.0, 0.0),
        "U6": (200.0, 0.0),
        # Clear J3's complete assembly courtyard, not only its plastic body.
        "U3": (204.3, 8.0),
        "C13": (209.909, 0.2367),
        # Give the back-side VBUS decoupler room for an ordinary through-via
        # escape instead of forcing a via-in-pad connection beneath C17.
        "C17": (205.5, -4.5),
        # Shift the bottom decoupling row left as one group to clear MHD2.
        "C3": (186.8, 18.5367),
        "C4": (189.1, 18.5367),
        "C11": (191.4, 18.5367),
        "C9": (193.7, 18.5367),
        "C10": (196.0, 18.5367),
    }
    for reference, (x, y) in relocations.items():
        move(board, reference, x, y)

    if not pcbnew.SaveBoard(args.output, board):
        raise RuntimeError("board save failed")
    print("FPC centers", 164.909, 209.509,
          "mount rectangle", left, right, top, bottom)


if __name__ == "__main__":
    main()
