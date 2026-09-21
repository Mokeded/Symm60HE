#!/usr/bin/env python3
"""Clear the final explicit +3V3A layer transition on the left half."""

import argparse
import math

import wx
import pcbnew


def mm(vector):
    return tuple(float(value) for value in pcbnew.ToMM(vector))


def near(a, b):
    return math.dist(a, b) < 0.01


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    old = (40.0470, 76.0543)
    new = (40.0400, 76.1600)
    vias = [item for item in board.GetTracks()
            if isinstance(item, pcbnew.PCB_VIA)
            and item.GetNetname() == "+3V3A"
            and near(mm(item.GetPosition()), old)]
    if len(vias) != 1:
        raise RuntimeError(f"expected one +3V3A via at {old}, got {len(vias)}")
    vias[0].SetPosition(pcbnew.VECTOR2I_MM(*new))
    vias[0].SetWidth(pcbnew.FromMM(0.60))
    vias[0].SetDrill(pcbnew.FromMM(0.30))
    connected = 0
    for item in board.GetTracks():
        if isinstance(item, pcbnew.PCB_VIA) or item.GetNetname() != "+3V3A":
            continue
        if near(mm(item.GetStart()), old):
            item.SetStart(pcbnew.VECTOR2I_MM(*new))
            connected += 1
        if near(mm(item.GetEnd()), old):
            item.SetEnd(pcbnew.VECTOR2I_MM(*new))
            connected += 1
    if connected != 2:
        raise RuntimeError(f"expected two attached +3V3A tracks, got {connected}")

    if not pcbnew.SaveBoard(args.output, board):
        raise RuntimeError("board save failed")
    print(args.output)


if __name__ == "__main__":
    main()
