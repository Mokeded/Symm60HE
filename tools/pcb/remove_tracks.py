#!/usr/bin/env python3
"""Remove tracks with explicitly identified endpoint pairs from a board copy."""

import argparse
import math

import wx
import pcbnew


def point_mm(vector):
    return (pcbnew.ToMM(vector.x), pcbnew.ToMM(vector.y))


def same_pair(track, coords):
    a = point_mm(track.GetStart())
    b = point_mm(track.GetEnd())
    c = tuple(coords[:2])
    d = tuple(coords[2:])
    return ((math.dist(a, c) < 0.01 and math.dist(b, d) < 0.01)
            or (math.dist(a, d) < 0.01 and math.dist(b, c) < 0.01))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    parser.add_argument("--ends", nargs=4, type=float, action="append", required=True)
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    removed = []
    for item in list(board.GetTracks()):
        if isinstance(item, pcbnew.PCB_VIA):
            continue
        for coords in args.ends:
            if same_pair(item, coords):
                removed.append(coords)
                board.Remove(item)
                break
    if len(removed) != len(args.ends):
        raise RuntimeError(f"expected {len(args.ends)} tracks, removed {len(removed)}")
    if not pcbnew.ZONE_FILLER(board).Fill(board.Zones()):
        raise RuntimeError("zone refill failed")
    if not pcbnew.SaveBoard(args.output, board):
        raise RuntimeError("board save failed")
    print("removed", len(removed), "tracks")


if __name__ == "__main__":
    main()
