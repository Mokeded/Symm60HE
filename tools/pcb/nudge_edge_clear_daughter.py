#!/usr/bin/env python3
"""Nudge normalized autorouter corners to restore the full 0.20 mm clearance."""

import argparse

import wx
import pcbnew


MOVES = {
    (210.1957, 11.8234): (210.1957, 11.8534),
    (206.4991, 10.6359): (206.4991, 10.6059),
    (181.9129, 10.4867): (181.9129, 10.4820),
    # Center the USB-to-MCU GND escape in the 0.63 mm pad-row channel.
    (189.3365, 1.9717): (189.3365, 1.9800),
    (187.8652, 1.9717): (187.8652, 1.9800),
    (187.8266, 2.0103): (187.8266, 1.9800),
    (187.6704, 2.0103): (187.6704, 1.9800),
    (206.9684, -0.0313): (206.9384, -0.0613),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    moved = {old: 0 for old in MOVES}
    for item in board.GetTracks():
        if isinstance(item, pcbnew.PCB_VIA):
            continue
        for getter, setter in ((item.GetStart, item.SetStart),
                               (item.GetEnd, item.SetEnd)):
            point = getter()
            key = (round(pcbnew.ToMM(point.x), 4),
                   round(pcbnew.ToMM(point.y), 4))
            if key in MOVES:
                setter(pcbnew.VECTOR2I_MM(*MOVES[key]))
                moved[key] += 1
    missing = [key for key, count in moved.items() if not count]
    if missing:
        raise RuntimeError(f"route corners not found: {missing}")
    if not pcbnew.ZONE_FILLER(board).Fill(board.Zones()):
        raise RuntimeError("zone refill failed")
    if not pcbnew.SaveBoard(args.output, board):
        raise RuntimeError("board save failed")
    print("moved endpoints", moved)


if __name__ == "__main__":
    main()
