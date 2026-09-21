#!/usr/bin/env python3
"""Reroute the remaining right-half copper away from alignment holes."""

import argparse
import math

import wx
import pcbnew


REMOVE_SEGMENTS = {
    frozenset(((291.8090, 82.5000), (291.8090, 81.4856))),
    frozenset(((291.8090, 81.4856), (288.3234, 78.0000))),
    frozenset(((251.9326, 80.7611), (252.6616, 80.0321))),
    frozenset(((252.6616, 80.0321), (252.6616, 78.4242))),
    frozenset(((253.0210, 84.0000), (251.9326, 82.9116))),
    frozenset(((251.9326, 82.9116), (251.9326, 80.7611))),
    frozenset(((252.6616, 78.4242), (249.7406, 75.5032))),
    frozenset(((229.4562, 89.5945), (277.4220, 89.5945))),
}


def point(vector):
    return (round(pcbnew.ToMM(vector.x), 4),
            round(pcbnew.ToMM(vector.y), 4))


def add_track(board, net, layer, start, end):
    track = pcbnew.PCB_TRACK(board)
    track.SetNet(net)
    track.SetLayer(layer)
    track.SetWidth(pcbnew.FromMM(0.20))
    track.SetStart(pcbnew.VECTOR2I_MM(*start))
    track.SetEnd(pcbnew.VECTOR2I_MM(*end))
    board.Add(track)


def add_path(board, net_name, layer, points):
    net = board.FindNet(net_name)
    for start, end in zip(points, points[1:]):
        add_track(board, net, layer, start, end)


def add_via(board, net_name, at):
    via = pcbnew.PCB_VIA(board)
    via.SetNet(board.FindNet(net_name))
    via.SetPosition(pcbnew.VECTOR2I_MM(*at))
    via.SetWidth(pcbnew.FromMM(0.60))
    via.SetDrill(pcbnew.FromMM(0.30))
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(via)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    parser.add_argument("--leave-rgb28-open", action="store_true")
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    removed_segments = 0
    removed_vias = 0
    for item in list(board.GetTracks()):
        if isinstance(item, pcbnew.PCB_VIA):
            if item.GetNetname() == "GND" and any(math.dist(
                    point(item.GetPosition()), target) < 0.01 for target in (
                        (272.9883, 8.5300), (252.9883, 82.5300))):
                board.Remove(item)
                removed_vias += 1
            continue
        endpoints = frozenset((point(item.GetStart()), point(item.GetEnd())))
        if endpoints in REMOVE_SEGMENTS:
            board.Remove(item)
            removed_segments += 1
    if removed_segments != len(REMOVE_SEGMENTS) or removed_vias != 2:
        raise RuntimeError(
            f"removed {removed_segments}/{len(REMOVE_SEGMENTS)} segments "
            f"and {removed_vias}/2 vias")

    add_path(board, "RGB_R_31", pcbnew.B_Cu, [
        (291.8090, 82.5000), (290.0000, 83.2000),
        (289.8000, 80.0000), (288.3234, 78.0000),
    ])
    if not args.leave_rgb28_open:
        add_path(board, "RGB_R_28", pcbnew.B_Cu,
                 [(253.0210, 84.0000), (251.8000, 84.0000)])
        add_via(board, "RGB_R_28", (251.8000, 84.0000))
        add_path(board, "RGB_R_28", pcbnew.F_Cu,
                 [(251.8000, 84.0000), (250.3000, 84.0000)])
        add_via(board, "RGB_R_28", (250.3000, 84.0000))
        add_path(board, "RGB_R_28", pcbnew.B_Cu, [
            (250.3000, 84.0000), (249.0000, 84.0000),
            (249.0000, 80.5000), (245.5000, 80.5000),
        ])
        add_via(board, "RGB_R_28", (245.5000, 80.5000))
        add_path(board, "RGB_R_28", pcbnew.F_Cu,
                 [(245.5000, 80.5000), (248.7000, 81.0000),
                  (248.7000, 78.7000)])
        add_via(board, "RGB_R_28", (248.7000, 78.7000))
        add_path(board, "RGB_R_28", pcbnew.B_Cu, [
            (248.7000, 78.7000), (248.7000, 75.5032),
            (249.7406, 75.5032),
        ])
    add_path(board, "HE_R30", pcbnew.F_Cu, [
        (229.4562, 89.5945), (250.0000, 89.5945),
        (251.0000, 89.2000), (260.0000, 89.2000),
        (261.0000, 89.5945), (277.4220, 89.5945),
    ])

    if not pcbnew.ZONE_FILLER(board).Fill(board.Zones()):
        raise RuntimeError("zone refill failed")
    if not pcbnew.SaveBoard(args.output, board):
        raise RuntimeError("board save failed")
    print("removed", removed_segments, "segments and", removed_vias, "vias")


if __name__ == "__main__":
    main()
