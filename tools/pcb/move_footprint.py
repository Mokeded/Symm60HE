#!/usr/bin/env python3
"""Move one footprint in a board candidate to an explicit position."""

import argparse

import wx
import pcbnew


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    parser.add_argument("reference")
    parser.add_argument("x", type=float)
    parser.add_argument("y", type=float)
    parser.add_argument("--rotation", type=float)
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    footprint = board.FindFootprintByReference(args.reference)
    if footprint is None:
        raise RuntimeError(f"missing footprint {args.reference}")
    footprint.SetPosition(pcbnew.VECTOR2I_MM(args.x, args.y))
    if args.rotation is not None:
        footprint.SetOrientationDegrees(args.rotation)
    if not pcbnew.SaveBoard(args.output, board):
        raise RuntimeError("board save failed")
    print(args.reference, args.x, args.y,
          footprint.GetOrientationDegrees())


if __name__ == "__main__":
    main()
