#!/usr/bin/env python3
"""Dogleg compact-daughterboard VBUS around the left FPC mount pad."""

import argparse

import wx
import pcbnew


def near(point, x, y, tolerance=0.0002):
    return (abs(pcbnew.ToMM(point.x) - x) <= tolerance
            and abs(pcbnew.ToMM(point.y) - y) <= tolerance)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    removed = 0
    for item in list(board.GetTracks()):
        if (isinstance(item, pcbnew.PCB_VIA)
                or item.GetNetname() != "VBUS"
                or item.GetLayer() != pcbnew.F_Cu):
            continue
        start, end = item.GetStart(), item.GetEnd()
        if ((near(start, 170.8039, -2.4693)
             and near(end, 166.1686, 2.1660))
                or (near(end, 170.8039, -2.4693)
                    and near(start, 166.1686, 2.1660))):
            board.Remove(item)
            removed += 1

    if removed != 1:
        raise RuntimeError("expected to replace exactly one VBUS segment")
    net = board.FindNet("VBUS")
    points = ((170.8039, -2.4693), (167.0, -2.4693),
              (166.1686, -1.6380), (166.1686, 2.1660))
    for a, b in zip(points, points[1:]):
        track = pcbnew.PCB_TRACK(board)
        track.SetNet(net)
        track.SetLayer(pcbnew.F_Cu)
        track.SetWidth(pcbnew.FromMM(0.20))
        track.SetStart(pcbnew.VECTOR2I_MM(*a))
        track.SetEnd(pcbnew.VECTOR2I_MM(*b))
        board.Add(track)

    if not pcbnew.SaveBoard(args.output, board):
        raise RuntimeError("board save failed")
    print("replaced VBUS diagonal with checked left-side dogleg")


if __name__ == "__main__":
    main()
