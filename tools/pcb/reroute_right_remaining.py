#!/usr/bin/env python3
"""Join the three final right-half opens through local free corridors.

This produces a candidate only.  KiCad DRC is the acceptance gate.
"""

import argparse

import wx
import pcbnew


def add_track(board, net, layer, start, end):
    track = pcbnew.PCB_TRACK(board)
    track.SetNet(net)
    track.SetLayer(layer)
    track.SetWidth(pcbnew.FromMM(0.20))
    track.SetStart(pcbnew.VECTOR2I_MM(*start))
    track.SetEnd(pcbnew.VECTOR2I_MM(*end))
    board.Add(track)


def add_via(board, net, point):
    via = pcbnew.PCB_VIA(board)
    via.SetNet(net)
    via.SetPosition(pcbnew.VECTOR2I_MM(*point))
    via.SetWidth(pcbnew.FromMM(0.60))
    via.SetDrill(pcbnew.FromMM(0.30))
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(via)


def add_path(board, net_name, layer, points):
    net = board.FindNet(net_name)
    if net is None:
        raise RuntimeError(f"missing net {net_name}")
    for start, end in zip(points, points[1:]):
        add_track(board, net, layer, start, end)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)

    # Escape both bottom-row Hall power pads toward the open space above the
    # sensors instead of crossing their signal/ground pads.
    power = board.FindNet("+3V3A")
    left_escape = (255.5000, 83.5000)
    add_path(board, "+3V3A", pcbnew.B_Cu,
             [(254.5025, 84.7750), left_escape])
    add_via(board, power, left_escape)
    add_path(board, "+3V3A", pcbnew.F_Cu,
             [left_escape, (251.4517, 84.8418)])

    right_escape = (287.8405, 82.0000)
    right_return = (288.7000, 87.6000)
    add_path(board, "+3V3A", pcbnew.B_Cu,
             [(287.8405, 84.7750), right_escape])
    add_via(board, power, right_escape)
    add_path(board, "+3V3A", pcbnew.F_Cu,
             [right_escape, (286.8000, 86.0000), right_return])
    add_via(board, power, right_return)
    add_path(board, "+3V3A", pcbnew.B_Cu,
             [right_return, (290.3275, 86.6750)])

    # HE_R35 already has a via at the mux-side endpoint.  Move the sensor-side
    # component to F.Cu and use the otherwise open perimeter corridor.
    hall = board.FindNet("HE_R35")
    sensor_end = (264.2380, 94.0300)
    add_via(board, hall, sensor_end)
    add_path(board, "HE_R35", pcbnew.F_Cu, [
        sensor_end, (267.0000, 96.5000), (299.5000, 96.5000),
        (303.5000, 92.5000), (303.5000, 60.0000),
        (294.1279, 56.5534),
    ])

    if not pcbnew.SaveBoard(args.output, board):
        raise SystemExit("board save failed")
    print(args.output)


if __name__ == "__main__":
    main()
