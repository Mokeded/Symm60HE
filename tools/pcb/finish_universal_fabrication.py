#!/usr/bin/env python3
"""Deterministic finishing routes for the aperture-safe universal halves."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import wx
import pcbnew


def point(vector):
    return tuple(float(v) for v in pcbnew.ToMM(vector))


def near(a, b, tolerance=0.01):
    return math.dist(a, b) < tolerance


def remove_track(board, net_name, a, b, required=True):
    for item in list(board.GetTracks()):
        if isinstance(item, pcbnew.PCB_VIA) or item.GetNetname() != net_name:
            continue
        start, end = point(item.GetStart()), point(item.GetEnd())
        if (near(start, a) and near(end, b)) or (near(start, b) and near(end, a)):
            board.Remove(item)
            return True
    if required:
        raise RuntimeError(f"missing {net_name} track {a} -> {b}")
    return False


def remove_tracks(board, specs):
    pending = [(net, a, b) for net, a, b in specs]
    removed = []
    for item in list(board.GetTracks()):
        if isinstance(item, pcbnew.PCB_VIA):
            continue
        start, end = point(item.GetStart()), point(item.GetEnd())
        for spec in pending:
            net, a, b = spec
            if item.GetNetname() == net and (
                    (near(start, a) and near(end, b)) or
                    (near(start, b) and near(end, a))):
                removed.append((item, spec))
                pending.remove(spec)
                break
    if pending:
        raise RuntimeError(f"missing tracks: {pending}")
    for item, _ in removed:
        board.Remove(item)


def add_track(board, net, layer, a, b):
    item = pcbnew.PCB_TRACK(board)
    item.SetNet(net)
    item.SetLayer(layer)
    item.SetWidth(pcbnew.FromMM(0.20))
    item.SetStart(pcbnew.VECTOR2I_MM(*a))
    item.SetEnd(pcbnew.VECTOR2I_MM(*b))
    board.Add(item)


def add_path(board, net_name, layer, points):
    net = board.FindNet(net_name)
    if net is None:
        raise RuntimeError(f"missing net {net_name}")
    for a, b in zip(points, points[1:]):
        add_track(board, net, layer, a, b)


def add_via(board, net_name, at):
    net = board.FindNet(net_name)
    via = pcbnew.PCB_VIA(board)
    via.SetNet(net)
    via.SetPosition(pcbnew.VECTOR2I_MM(*at))
    via.SetWidth(pcbnew.FromMM(0.60))
    via.SetDrill(pcbnew.FromMM(0.30))
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(via)


def move_via(board, net_name, old, new):
    matches = [item for item in board.GetTracks()
               if isinstance(item, pcbnew.PCB_VIA)
               and item.GetNetname() == net_name
               and near(point(item.GetPosition()), old)]
    if len(matches) != 1:
        raise RuntimeError(f"expected one {net_name} via at {old}, got {len(matches)}")
    matches[0].SetPosition(pcbnew.VECTOR2I_MM(*new))
    for item in board.GetTracks():
        if isinstance(item, pcbnew.PCB_VIA) or item.GetNetname() != net_name:
            continue
        if near(point(item.GetStart()), old):
            item.SetStart(pcbnew.VECTOR2I_MM(*new))
        if near(point(item.GetEnd()), old):
            item.SetEnd(pcbnew.VECTOR2I_MM(*new))


def finish_left(board):
    # Remove the long stretched stubs left by moving the inboard LEDs.
    remove_tracks(board, [
        ("GND", (8.2285, 77.2500), (2.4520, 78.8250)),
        ("VBUS", (15.2680, 84.0000), (13.6785, 78.7500)),
        ("RGB_L_28", (41.5665, 78.7500), (40.2991, 82.7326)),
        ("MUX_A1", (40.6750, 75.4613), (40.0470, 75.8043)),
        ("MUX_A1", (40.0470, 75.8043), (42.9674, 75.6916)),
        ("MUX_A1", (42.9674, 75.5011), (42.9674, 75.6916)),
    ])

    # The old MUX_A1 dogleg passed through the relocated aperture and grazed
    # AML5 pin 9.  Cross the local pinch point on F.Cu, then reconnect the
    # separated long run by staying above the bottom-row apertures.
    add_via(board, "MUX_A1", (40.6750, 75.4613))
    add_via(board, "MUX_A1", (42.9674, 75.5011))
    add_path(board, "MUX_A1", pcbnew.F_Cu,
             [(40.6750, 75.4613), (41.0000, 73.9000),
              (42.6000, 73.9000), (42.9674, 75.5011)])
    # Short, aperture-following LED routes.  All B.Cu paths stay outside the
    # 0.20 mm opening halo; the existing vias carry the longer RGB runs.
    add_path(board, "RGB_L_27", pcbnew.B_Cu,
             [(13.6785, 77.2500), (14.6000, 76.3000)])
    add_via(board, "RGB_L_27", (14.6000, 76.3000))
    add_path(board, "RGB_L_27", pcbnew.F_Cu,
             [(14.6000, 76.3000), (16.0000, 78.0000),
              (16.0000, 80.5000), (14.7477, 81.6359)])
    add_path(board, "VBUS", pcbnew.B_Cu,
             [(13.6785, 78.7500), (15.5000, 80.0000),
              (15.5000, 82.9000), (15.9140, 83.3540)])


def finish_right(board):
    # The automatic repair found a valid alternate Hall route but left a via
    # too close to AMR3 pin 3.  Move that layer change into the open corridor.
    move_via(board, "HE_R24", (235.7296, 76.8043), (234.5000, 77.5000))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board_dir", type=Path)
    parser.add_argument("--side", choices=("Left", "Right"))
    args = parser.parse_args()
    jobs = (("Left", finish_left), ("Right", finish_right))
    if args.side:
        jobs = tuple(job for job in jobs if job[0] == args.side)
    for side, fn in jobs:
        path = args.board_dir / f"Symm60HE-{side}.kicad_pcb"
        board = pcbnew.LoadBoard(str(path))
        if board is None:
            raise RuntimeError(f"cannot load {path}")
        fn(board)
        if not pcbnew.SaveBoard(str(path), board):
            raise RuntimeError(f"failed to save {path}")
        print(f"{path.name}: deterministic fabrication routes applied")


if __name__ == "__main__":
    app = wx.App(False)
    main()
