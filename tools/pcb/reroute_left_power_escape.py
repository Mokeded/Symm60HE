#!/usr/bin/env python3
"""Free the HE_L33 escape by moving one local +3V3A branch to F.Cu."""

import argparse
import math

import wx
import pcbnew


REMOVE = {
    frozenset(((40.1661, 77.6911), (39.6270, 78.2302))),
    frozenset(((39.6270, 78.2302), (39.6270, 85.9960))),
    frozenset(((39.6270, 85.9960), (41.9362, 88.3052))),
    frozenset(((41.9362, 88.3052), (45.5355, 88.3052))),
}


def mm_point(vector):
    return (round(pcbnew.ToMM(vector.x), 4), round(pcbnew.ToMM(vector.y), 4))


def add_track(board, net, layer, start, end):
    track = pcbnew.PCB_TRACK(board)
    track.SetNet(net)
    track.SetLayer(layer)
    track.SetWidth(pcbnew.FromMM(0.20))
    track.SetStart(pcbnew.VECTOR2I_MM(*start))
    track.SetEnd(pcbnew.VECTOR2I_MM(*end))
    board.Add(track)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    removed = 0
    for track in list(board.GetTracks()):
        if not isinstance(track, pcbnew.PCB_TRACK) or isinstance(track, pcbnew.PCB_VIA):
            continue
        if track.GetNetname() != "+3V3A" or track.GetLayer() != pcbnew.B_Cu:
            continue
        endpoints = frozenset((mm_point(track.GetStart()), mm_point(track.GetEnd())))
        if endpoints in REMOVE:
            board.Remove(track)
            removed += 1
    if removed != len(REMOVE):
        raise RuntimeError(f"expected to remove {len(REMOVE)} tracks, removed {removed}")

    power = board.FindNet("+3V3A")
    via = pcbnew.PCB_VIA(board)
    via.SetNet(power)
    via.SetPosition(pcbnew.VECTOR2I_MM(41.6991, 77.6911))
    via.SetWidth(pcbnew.FromMM(0.60))
    via.SetDrill(pcbnew.FromMM(0.30))
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(via)
    add_track(board, power, pcbnew.F_Cu,
              (41.6991, 77.6911), (45.5355, 88.3052))

    if not pcbnew.SaveBoard(args.output, board):
        raise SystemExit("board save failed")
    print("moved local +3V3A escape to F.Cu")


if __name__ == "__main__":
    main()
