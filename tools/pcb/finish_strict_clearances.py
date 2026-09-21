#!/usr/bin/env python3
"""Apply the final NPTH-to-copper clearance moves to the universal halves.

The edits are deliberately coordinate-specific.  Track endpoints attached to a
moved via or footprint pad are moved with it so the operation cannot silently
create an open connection.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import wx
import pcbnew


def mm(point):
    return tuple(float(value) for value in pcbnew.ToMM(point))


def close(a, b, tolerance=0.002):
    return abs(a[0] - b[0]) <= tolerance and abs(a[1] - b[1]) <= tolerance


def move_endpoint(track, old, new):
    changed = False
    if close(mm(track.GetStart()), old):
        track.SetStart(pcbnew.VECTOR2I_MM(*new))
        changed = True
    if close(mm(track.GetEnd()), old):
        track.SetEnd(pcbnew.VECTOR2I_MM(*new))
        changed = True
    return changed


def move_via(board, net_name, old, new):
    matches = [item for item in board.GetTracks()
               if isinstance(item, pcbnew.PCB_VIA)
               and item.GetNetname() == net_name
               and close(mm(item.GetPosition()), old)]
    if len(matches) != 1:
        raise RuntimeError(f"expected one {net_name} via at {old}, found {len(matches)}")
    matches[0].SetPosition(pcbnew.VECTOR2I_MM(*new))
    for item in board.GetTracks():
        if not isinstance(item, pcbnew.PCB_VIA) and item.GetNetname() == net_name:
            move_endpoint(item, old, new)


def move_footprint(board, reference, destination):
    footprint = board.FindFootprintByReference(reference)
    if footprint is None:
        raise RuntimeError(f"missing footprint {reference}")
    before = [(pad.GetNetname(), mm(pad.GetPosition())) for pad in footprint.Pads()]
    footprint.SetPosition(pcbnew.VECTOR2I_MM(*destination))
    after = [(pad.GetNetname(), mm(pad.GetPosition())) for pad in footprint.Pads()]
    for (old_net, old), (new_net, new) in zip(before, after):
        if old_net != new_net:
            raise RuntimeError(f"{reference}: pad order changed while moving")
        for item in board.GetTracks():
            if not isinstance(item, pcbnew.PCB_VIA) and item.GetNetname() == old_net:
                move_endpoint(item, old, new)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    board = pcbnew.LoadBoard(str(args.board))
    if board is None:
        raise RuntimeError(f"cannot load {args.board}")
    name = args.board.name.lower()
    if "left" in name:
        move_via(board, "HE_L26", (99.4470, 90.6043), (99.4100, 90.5110))
        move_via(board, "RGB_L_29", (50.3970, 80.5043), (50.4470, 80.5043))
        move_via(board, "RGB_L_26", (9.7470, 81.3043), (9.7380, 81.3090))
        move_footprint(board, "AML4", (75.4180, 82.4250))
    elif "right" in name:
        move_footprint(board, "AMR4", (227.0000, 82.4250))
    else:
        raise RuntimeError("board filename must contain Left or Right")
    if not pcbnew.SaveBoard(str(args.output), board):
        raise RuntimeError(f"failed to save {args.output}")
    print(f"{args.board.name}: applied strict NPTH-clearance moves")


if __name__ == "__main__":
    app = wx.App(False)
    main()
