#!/usr/bin/env python3
"""Nudge one autorouted GND corner clear of U4 after width normalization."""

import argparse

import wx
import pcbnew


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    old = pcbnew.VECTOR2I_MM(181.9129, 10.4867)
    new = pcbnew.VECTOR2I_MM(181.9129, 10.4767)
    changed = 0
    for item in board.GetTracks():
        if isinstance(item, pcbnew.PCB_VIA) or item.GetNetname() != "GND":
            continue
        if item.GetStart() == old:
            item.SetStart(new)
            changed += 1
        if item.GetEnd() == old:
            item.SetEnd(new)
            changed += 1
    if changed != 2:
        raise RuntimeError(f"expected two connected endpoints, changed {changed}")
    if not pcbnew.ZONE_FILLER(board).Fill(board.Zones()):
        raise RuntimeError("zone refill failed")
    if not pcbnew.SaveBoard(args.output, board):
        raise RuntimeError("board save failed")
    print("nudged", changed, "GND endpoints")


if __name__ == "__main__":
    main()
