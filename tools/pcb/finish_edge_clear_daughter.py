#!/usr/bin/env python3
"""Finish the symmetric daughterboard's isolated J3 +3V3A escape."""

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
    net = board.FindNet("+3V3A")
    if net is None:
        raise RuntimeError("missing +3V3A net")

    # J3 pin 1 already escapes through a normal via at (211.3415, 2.4308),
    # but the autorouter could not join that small island to the main +3V3A
    # tree.  Add a normal through-via on the J2 branch and use the clear outer
    # B.Cu perimeter above the USB connector.
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I_MM(168.0, 13.8375))
    via.SetWidth(pcbnew.FromMM(0.60))
    via.SetDrill(pcbnew.FromMM(0.30))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNet(net)
    board.Add(via)

    points = (
        (168.0000, 13.8375),
        (163.0000, 13.8375),
        (163.0000, -5.3000),
        (163.8500, -6.1400),
        (210.6000, -6.1400),
        (211.4615, -5.3000),
        (211.4615, 2.4308),
        (211.3415, 2.4308),
    )
    for start, end in zip(points, points[1:]):
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(pcbnew.VECTOR2I_MM(*start))
        track.SetEnd(pcbnew.VECTOR2I_MM(*end))
        track.SetWidth(pcbnew.FromMM(0.20))
        track.SetLayer(pcbnew.B_Cu)
        track.SetNet(net)
        board.Add(track)

    if not pcbnew.SaveBoard(args.output, board):
        raise RuntimeError("board save failed")
    print("joined J3 +3V3A escape around the upper B.Cu perimeter")


if __name__ == "__main__":
    main()
