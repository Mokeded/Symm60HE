#!/usr/bin/env python3
"""Restore the proven RGB_L26 trunk before routing its moved DL27 endpoint."""

import argparse
from pathlib import Path

import wx
import pcbnew


def mm(vector):
    return tuple(float(value) for value in pcbnew.ToMM(vector))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    parser.add_argument("--source", default=str(
        Path(__file__).resolve().parents[2] / "pcb/Symm60HE-Left.kicad_pcb"))
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    source = pcbnew.LoadBoard(args.source)
    net_name = "RGB_L_26"
    existing = [item for item in board.GetTracks()
                if item.GetNetname() == net_name]
    for item in existing:
        board.Remove(item)

    restored = 0
    target_net = board.FindNet(net_name)
    for original in source.GetTracks():
        if original.GetNetname() != net_name:
            continue
        if isinstance(original, pcbnew.PCB_VIA):
            item = pcbnew.PCB_VIA(board)
            item.SetPosition(original.GetPosition())
            item.SetWidth(original.GetWidth(pcbnew.F_Cu))
            item.SetDrill(original.GetDrillValue())
            item.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        else:
            item = pcbnew.PCB_TRACK(board)
            item.SetStart(original.GetStart())
            item.SetEnd(original.GetEnd())
            item.SetWidth(original.GetWidth())
            item.SetLayer(original.GetLayer())
        item.SetNet(target_net)
        board.Add(item)
        restored += 1
    if restored == 0:
        raise RuntimeError("the universal RGB_L26 trunk was not found")

    if not pcbnew.SaveBoard(args.output, board):
        raise RuntimeError("board save failed")
    print(f"{args.output}: restored {restored} RGB_L26 copper objects")


if __name__ == "__main__":
    main()
