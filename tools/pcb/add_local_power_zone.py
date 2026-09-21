#!/usr/bin/env python3
"""Add a bounded +3V3A copper zone for a congested local power corridor."""

import argparse

import wx
import pcbnew


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    parser.add_argument("--layer", choices=("F.Cu", "B.Cu"), default="B.Cu")
    parser.add_argument("--rect", nargs=4, type=float, metavar=("X0", "Y0", "X1", "Y1"),
                        required=True)
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    power = board.FindNet("+3V3A")
    if power is None:
        raise SystemExit("board has no +3V3A net")
    x0, y0, x1, y1 = args.rect
    chain = pcbnew.SHAPE_LINE_CHAIN()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        chain.Append(pcbnew.VECTOR2I_MM(x, y))
    chain.SetClosed(True)
    outline = pcbnew.SHAPE_POLY_SET()
    outline.AddOutline(chain)

    zone = pcbnew.ZONE(board)
    zone.SetNet(power)
    zone.SetOutline(outline)
    layer_set = pcbnew.LSET()
    layer_set.AddLayer(pcbnew.F_Cu if args.layer == "F.Cu" else pcbnew.B_Cu)
    zone.SetLayerSet(layer_set)
    zone.SetAssignedPriority(10)
    zone.SetLocalClearance(pcbnew.FromMM(0.20))
    zone.SetMinThickness(pcbnew.FromMM(0.20))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    zone.SetThermalReliefGap(pcbnew.FromMM(0.30))
    zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.30))
    board.Add(zone)
    if not pcbnew.ZONE_FILLER(board).Fill(board.Zones()):
        raise SystemExit("zone fill failed")
    if not pcbnew.SaveBoard(args.output, board):
        raise SystemExit("board save failed")
    print(args.output)


if __name__ == "__main__":
    main()
