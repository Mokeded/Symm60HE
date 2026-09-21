#!/usr/bin/env python3
"""Remove explicitly identified diagnostic vias from a KiCad board copy."""

import argparse
import math

import wx
import pcbnew


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    parser.add_argument("--at", nargs=2, type=float, action="append", required=True)
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    removed = []
    for item in list(board.GetTracks()):
        if not isinstance(item, pcbnew.PCB_VIA):
            continue
        point = (pcbnew.ToMM(item.GetPosition().x),
                 pcbnew.ToMM(item.GetPosition().y))
        if any(math.dist(point, target) < 0.01 for target in args.at):
            removed.append(point)
            board.Remove(item)
    if len(removed) != len(args.at):
        raise RuntimeError(f"expected {len(args.at)} vias, removed {len(removed)}")
    if not pcbnew.ZONE_FILLER(board).Fill(board.Zones()):
        raise RuntimeError("zone refill failed")
    if not pcbnew.SaveBoard(args.output, board):
        raise RuntimeError("board save failed")
    print("removed", removed)


if __name__ == "__main__":
    main()
