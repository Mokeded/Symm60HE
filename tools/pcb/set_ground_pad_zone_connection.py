#!/usr/bin/env python3
"""Set GND pads to solid or no-pour connection and refill existing zones."""

import argparse

import wx
import pcbnew


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    parser.add_argument("--mode", choices=("none", "solid"), required=True)
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    mode = (pcbnew.ZONE_CONNECTION_NONE if args.mode == "none"
            else pcbnew.ZONE_CONNECTION_FULL)
    changed = 0
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if pad.GetNetname() == "GND":
                pad.SetLocalZoneConnection(mode)
                changed += 1

    if not pcbnew.ZONE_FILLER(board).Fill(board.Zones()):
        raise RuntimeError("zone refill failed")
    if not pcbnew.SaveBoard(args.output, board):
        raise RuntimeError("board save failed")
    print("updated", changed, "GND pads")


if __name__ == "__main__":
    main()
