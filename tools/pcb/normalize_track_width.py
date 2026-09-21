#!/usr/bin/env python3
"""Raise copper tracks below the project minimum width to that minimum."""

import argparse

import wx
import pcbnew


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    parser.add_argument("--minimum", type=float, default=0.20)
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    minimum = pcbnew.FromMM(args.minimum)
    changed = 0
    for item in board.GetTracks():
        if isinstance(item, pcbnew.PCB_VIA):
            continue
        if item.GetWidth() < minimum:
            item.SetWidth(minimum)
            changed += 1
    if not pcbnew.ZONE_FILLER(board).Fill(board.Zones()):
        raise RuntimeError("zone refill failed")
    if not pcbnew.SaveBoard(args.output, board):
        raise RuntimeError("board save failed")
    print("widened", changed, "tracks")


if __name__ == "__main__":
    main()
