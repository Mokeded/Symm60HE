#!/usr/bin/env python3
"""Add explicit GND pad-to-via taps at reviewed coordinates."""

import argparse

import wx
import pcbnew


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    parser.add_argument("--tap", nargs=4, type=float, action="append",
                        metavar=("PAD_X", "PAD_Y", "VIA_X", "VIA_Y"), required=True)
    parser.add_argument("--reuse-existing", action="store_true",
                        help="join an existing GND via instead of adding one")
    parser.add_argument("--top-link", nargs=4, type=float, action="append",
                        default=[], metavar=("X0", "Y0", "X1", "Y1"),
                        help="add a GND track on F.Cu between two vias")
    parser.add_argument("--via-only", nargs=2, type=float, action="append",
                        default=[], metavar=("X", "Y"),
                        help="add a GND via without a tap track")
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    ground = board.FindNet("GND")
    for pad_x, pad_y, via_x, via_y in args.tap:
        track = pcbnew.PCB_TRACK(board)
        track.SetNet(ground)
        track.SetLayer(pcbnew.B_Cu)
        track.SetWidth(pcbnew.FromMM(0.20))
        track.SetStart(pcbnew.VECTOR2I_MM(pad_x, pad_y))
        track.SetEnd(pcbnew.VECTOR2I_MM(via_x, via_y))
        board.Add(track)
        if not args.reuse_existing:
            via = pcbnew.PCB_VIA(board)
            via.SetNet(ground)
            via.SetPosition(pcbnew.VECTOR2I_MM(via_x, via_y))
            via.SetWidth(pcbnew.FromMM(0.60))
            via.SetDrill(pcbnew.FromMM(0.30))
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            board.Add(via)
    for x0, y0, x1, y1 in args.top_link:
        track = pcbnew.PCB_TRACK(board)
        track.SetNet(ground)
        track.SetLayer(pcbnew.F_Cu)
        track.SetWidth(pcbnew.FromMM(0.20))
        track.SetStart(pcbnew.VECTOR2I_MM(x0, y0))
        track.SetEnd(pcbnew.VECTOR2I_MM(x1, y1))
        board.Add(track)
    for x, y in args.via_only:
        via = pcbnew.PCB_VIA(board)
        via.SetNet(ground)
        via.SetPosition(pcbnew.VECTOR2I_MM(x, y))
        via.SetWidth(pcbnew.FromMM(0.60))
        via.SetDrill(pcbnew.FromMM(0.30))
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        board.Add(via)
    if not pcbnew.ZONE_FILLER(board).Fill(board.Zones()):
        raise RuntimeError("zone refill failed")
    if not pcbnew.SaveBoard(args.output, board):
        raise RuntimeError("board save failed")
    print("added", len(args.tap), "ground taps")


if __name__ == "__main__":
    main()
