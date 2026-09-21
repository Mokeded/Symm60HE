#!/usr/bin/env python3
"""Collapse a sub-micron HE_R06 endpoint mismatch into one clean junction."""

import argparse

import wx
import pcbnew


def close_mm(a, b, tolerance=0.0002):
    return abs(pcbnew.ToMM(a) - b) <= tolerance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    junction = pcbnew.VECTOR2I_MM(200.0383, 19.6836)
    removed = 0
    snapped = 0
    for track in list(board.GetTracks()):
        if (isinstance(track, pcbnew.PCB_VIA)
                or track.GetNetname() != "HE_R06"
                or track.GetLayer() != pcbnew.B_Cu):
            continue
        start = track.GetStart()
        end = track.GetEnd()
        if (track.GetLength() < pcbnew.FromMM(0.001)
                and close_mm(start.x, 200.0382)
                and close_mm(start.y, 19.6836)
                and close_mm(end.x, 200.0383)
                and close_mm(end.y, 19.6836)):
            board.Remove(track)
            removed += 1
            continue
        if (close_mm(end.x, 200.0382) and close_mm(end.y, 19.6836)):
            track.SetEnd(junction)
            snapped += 1
        if (close_mm(start.x, 200.0382) and close_mm(start.y, 19.6836)):
            track.SetStart(junction)
            snapped += 1

    # Widen the existing short branch at the T junction.  This supplies a full
    # copper neck where KiCad otherwise evaluates the rounded 0.20 mm track
    # endcaps as a sub-minimum connection.
    widened = 0
    for track in board.GetTracks():
        if (isinstance(track, pcbnew.PCB_VIA)
                or track.GetNetname() != "HE_R06"
                or track.GetLayer() != pcbnew.B_Cu):
            continue
        start = track.GetStart()
        end = track.GetEnd()
        if (close_mm(start.x, 200.0383) and close_mm(start.y, 19.6836)
                and close_mm(end.x, 200.4283) and close_mm(end.y, 19.6836)):
            track.SetWidth(pcbnew.FromMM(0.30))
            widened += 1

    if not pcbnew.ZONE_FILLER(board).Fill(board.Zones()):
        raise RuntimeError("zone refill failed")
    if not pcbnew.SaveBoard(args.output, board):
        raise RuntimeError("board save failed")
    print("removed", removed, "sub-micron segment; snapped", snapped,
          "track endpoint(s); widened", widened, "junction branch")


if __name__ == "__main__":
    main()
