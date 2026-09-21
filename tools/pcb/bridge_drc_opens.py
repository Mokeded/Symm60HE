#!/usr/bin/env python3
"""Create a diagnostic candidate by bridging non-GND DRC open pairs.

This deliberately writes to a separate board.  KiCad DRC remains the
acceptance gate: direct bridges that cross occupied copper are evidence for a
needed dogleg, not routes to keep.
"""

import argparse
import math
import re

import wx
import pcbnew


ITEM = re.compile(
    r"@\(([-0-9.]+) mm, ([-0-9.]+) mm\): .* \[([^]]+)\].* on ([FB]\.Cu)")

# Local doglegs around the bottom-row sensor ground pads and the right-side
# RGB/LED corridor.  Coordinates are tied to the approved component placement;
# every result is still checked by KiCad DRC before it can be promoted.
OVERRIDES = {
    ("Symm60HE-Left", "+3V3A"): [
        (40.1661, 77.6911, "B.Cu"),
        (40.1661, 77.6911, "F.Cu"),
        (33.0550, 77.0500, "F.Cu"),
        (33.0550, 77.0500, "B.Cu"),
    ],
    ("Symm60HE-Left", "HE_L27"): [
        (7.4345, 85.7250, "B.Cu"),
        (7.5000, 84.0000, "B.Cu"),
        (7.5000, 84.0000, "F.Cu"),
        (13.0000, 93.5000, "F.Cu"),
        (13.0000, 93.5000, "B.Cu"),
        (14.6920, 92.2266, "B.Cu"),
    ],
    ("Symm60HE-Left", "HE_L33"): [
        (40.7725, 85.7250, "B.Cu"),
        (40.7725, 88.5000, "B.Cu"),
        (40.7725, 88.5000, "F.Cu"),
        (39.0000, 90.5000, "F.Cu"),
        (39.0000, 90.5000, "B.Cu"),
        (38.9932, 89.9765, "B.Cu"),
    ],
    ("Symm60HE-Right", "HE_R29"): [
        (252.2275, 85.7250, "B.Cu"),
        (250.5000, 88.5000, "B.Cu"),
        (253.0000, 93.5000, "B.Cu"),
        (259.4850, 91.7399, "B.Cu"),
    ],
    ("Symm60HE-Right", "HE_R36"): [
        (285.5655, 85.7250, "B.Cu"),
        (283.8000, 88.5000, "B.Cu"),
        (286.0000, 95.0000, "B.Cu"),
        (298.2000, 95.0000, "B.Cu"),
        (298.1941, 91.7482, "B.Cu"),
    ],
    ("Symm60HE-Right", "RGB_R_06"): [
        (170.8684, 11.3521, "B.Cu"),
        (172.5000, 13.0000, "B.Cu"),
        (172.5000, 13.0000, "F.Cu"),
        (193.0000, 9.0000, "F.Cu"),
        (193.0000, 9.0000, "B.Cu"),
        (194.8203, 6.0263, "B.Cu"),
    ],
}


def segment(board, net, layer, start, end):
    track = pcbnew.PCB_TRACK(board)
    track.SetNet(net)
    track.SetLayer(pcbnew.F_Cu if layer == "F.Cu" else pcbnew.B_Cu)
    track.SetWidth(pcbnew.FromMM(0.20))
    track.SetStart(pcbnew.VECTOR2I_MM(*start))
    track.SetEnd(pcbnew.VECTOR2I_MM(*end))
    board.Add(track)


def add_path(board, net, points):
    for first, second in zip(points, points[1:]):
        p0, layer0 = first[:2], first[2]
        p1, layer1 = second[:2], second[2]
        if p0 == p1 and layer0 != layer1:
            via = pcbnew.PCB_VIA(board)
            via.SetNet(net)
            via.SetPosition(pcbnew.VECTOR2I_MM(*p0))
            via.SetWidth(pcbnew.FromMM(0.60))
            via.SetDrill(pcbnew.FromMM(0.30))
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            board.Add(via)
        elif layer0 == layer1:
            segment(board, net, layer0, p0, p1)
        else:
            raise RuntimeError("layer change requires coincident path points")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("drc_report")
    parser.add_argument("output")
    parser.add_argument("--no-overrides", action="store_true")
    parser.add_argument("--max-distance", type=float)
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    board_name = board.GetFileName().rsplit("/", 1)[-1].split(".kicad_pcb")[0]
    for canonical in ("Symm60HE-Left", "Symm60HE-Right",
                      "Symm60HE-Daughterboard"):
        if board_name.startswith(canonical):
            board_name = canonical
            break
    lines = open(args.drc_report).read().splitlines()
    bridged = []
    for index, line in enumerate(lines):
        if not line.startswith("[unconnected_items]"):
            continue
        found = []
        for item_line in lines[index + 1:index + 5]:
            match = ITEM.search(item_line)
            if match:
                x, y, netname, layer = match.groups()
                found.append(((float(x), float(y)), netname, layer))
        if len(found) != 2 or found[0][1] != found[1][1]:
            continue
        netname = found[0][1]
        if netname == "GND":
            continue
        net = board.FindNet(netname)
        if net is None:
            raise RuntimeError("missing net " + netname)
        p0, _, layer0 = found[0]
        p1, _, layer1 = found[1]
        if (args.max_distance is not None
                and math.dist(p0, p1) > args.max_distance):
            continue
        override = None if args.no_overrides else OVERRIDES.get((board_name, netname))
        if override:
            add_path(board, net, override)
        elif layer0 == layer1:
            segment(board, net, layer0, p0, p1)
        else:
            mid = ((p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0)
            segment(board, net, layer0, p0, mid)
            via = pcbnew.PCB_VIA(board)
            via.SetNet(net)
            via.SetPosition(pcbnew.VECTOR2I_MM(*mid))
            via.SetWidth(pcbnew.FromMM(0.60))
            via.SetDrill(pcbnew.FromMM(0.30))
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            board.Add(via)
            segment(board, net, layer1, mid, p1)
        bridged.append(netname)

    if not pcbnew.SaveBoard(args.output, board):
        raise SystemExit("board save failed")
    print("bridged", len(bridged), ", ".join(bridged))


if __name__ == "__main__":
    main()
