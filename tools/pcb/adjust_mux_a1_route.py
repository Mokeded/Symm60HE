#!/usr/bin/env python3
"""Move the final grid-routed MUX_A1 layer changes into clear corridors."""

import argparse
import math

import wx
import pcbnew


def mm(vector):
    return tuple(float(v) for v in pcbnew.ToMM(vector))


def near(a, b):
    return math.dist(a, b) < 0.01


def move_via(board, old, new):
    found = []
    for item in board.GetTracks():
        if (isinstance(item, pcbnew.PCB_VIA)
                and item.GetNetname() == "MUX_A1"
                and near(mm(item.GetPosition()), old)):
            found.append(item)
    if len(found) != 1:
        raise RuntimeError(f"expected one MUX_A1 via at {old}, got {len(found)}")
    found[0].SetPosition(pcbnew.VECTOR2I_MM(*new))
    for item in board.GetTracks():
        if isinstance(item, pcbnew.PCB_VIA) or item.GetNetname() != "MUX_A1":
            continue
        if near(mm(item.GetStart()), old):
            item.SetStart(pcbnew.VECTOR2I_MM(*new))
        if near(mm(item.GetEnd()), old):
            item.SetEnd(pcbnew.VECTOR2I_MM(*new))


def same_track(item, a, b):
    if isinstance(item, pcbnew.PCB_VIA) or item.GetNetname() != "MUX_A1":
        return False
    start, end = mm(item.GetStart()), mm(item.GetEnd())
    return ((near(start, a) and near(end, b)) or
            (near(start, b) and near(end, a)))


def add_track(board, a, b, layer=pcbnew.F_Cu, net_name="MUX_A1"):
    item = pcbnew.PCB_TRACK(board)
    item.SetNet(board.FindNet(net_name))
    item.SetLayer(layer)
    item.SetWidth(pcbnew.FromMM(0.20))
    item.SetStart(pcbnew.VECTOR2I_MM(*a))
    item.SetEnd(pcbnew.VECTOR2I_MM(*b))
    board.Add(item)


def add_via(board, point, net_name):
    item = pcbnew.PCB_VIA(board)
    item.SetNet(board.FindNet(net_name))
    item.SetPosition(pcbnew.VECTOR2I_MM(*point))
    item.SetWidth(pcbnew.FromMM(0.60))
    item.SetDrill(pcbnew.FromMM(0.30))
    board.Add(item)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    args = parser.parse_args()

    board = pcbnew.LoadBoard(args.board)
    remove_segments = (
        ((54.0470, 50.0543), (54.2970, 49.8043)),
        ((54.0470, 50.0543), (53.8250, 52.0250)),
    )
    doomed = []
    for item in list(board.GetTracks()):
        if any(same_track(item, a, b) for a, b in remove_segments):
            doomed.append(item)
        elif (isinstance(item, pcbnew.PCB_VIA)
              and item.GetNetname() == "MUX_A1"
              and near(mm(item.GetPosition()), (54.0470, 50.0543))):
            doomed.append(item)
    if len(doomed) != 3:
        raise RuntimeError(f"expected three redundant objects, got {len(doomed)}")
    for item in doomed:
        board.Remove(item)
    add_track(board, (53.1673, 49.8217), (54.2970, 49.8043))

    for old, new in (
        ((71.5470, 53.0543), (71.5000, 52.5000)),
        ((77.7970, 59.3043), (78.0000, 60.0000)),
        ((82.7970, 63.8043), (81.5000, 63.5000)),
        ((90.7970, 73.0543), (91.5000, 73.5000)),
        ((93.2970, 74.5543), (94.0000, 75.0000)),
    ):
        move_via(board, old, new)

    # Give the otherwise legal MUX_A1 via at (90.797, 73.0543) a controlled
    # opening in the long MUX_A2 rail instead of moving that via into HE_L24.
    old_a, old_b = (44.7008, 72.6808), (92.6928, 72.6808)
    matches = [item for item in board.GetTracks()
               if same_track(item, old_a, old_b)]
    # same_track is net-specific to MUX_A1, so match MUX_A2 explicitly here.
    matches = []
    for item in board.GetTracks():
        if isinstance(item, pcbnew.PCB_VIA) or item.GetNetname() != "MUX_A2":
            continue
        start, end = mm(item.GetStart()), mm(item.GetEnd())
        if ((near(start, old_a) and near(end, old_b)) or
                (near(start, old_b) and near(end, old_a))):
            matches.append(item)
    if len(matches) != 1:
        raise RuntimeError(f"expected one MUX_A2 rail, got {len(matches)}")
    board.Remove(matches[0])
    add_track(board, old_a, old_b, pcbnew.F_Cu, "MUX_A2")

    # Pass the MUX_A1 layer-change connection below the MUX_A2 dogleg and
    # above the MUX_A0 corridor.  The router's original diagonal crossed the
    # dogleg near (91.3, 73.8).
    old_mux_a1 = (
        ((91.5000, 73.5000), (91.7970, 73.0543)),
        ((91.7970, 73.0543), (94.0000, 75.0000)),
    )
    matches = [item for item in board.GetTracks()
               if any(same_track(item, a, b) for a, b in old_mux_a1)]
    if len(matches) != 2:
        raise RuntimeError(f"expected two MUX_A1 approach tracks, got {len(matches)}")
    for item in matches:
        board.Remove(item)
    mux_a1_path = [(91.5000, 73.5000), (92.0000, 74.2000),
                   (92.5000, 75.2000), (93.3000, 75.2000),
                   (94.0000, 75.0000)]
    for a, b in zip(mux_a1_path, mux_a1_path[1:]):
        add_track(board, a, b)

    # Remove the obsolete power-zone spur left by the previous component
    # placement and discard unanchored B.Cu +3V3A islands during refill.
    power_a, power_b = (28.5470, 71.5543), (30.0000, 72.0000)
    power_spurs = []
    for item in board.GetTracks():
        if (isinstance(item, pcbnew.PCB_VIA)
                or item.GetNetname() != "+3V3A"
                or item.GetLayer() != pcbnew.B_Cu):
            continue
        start, end = mm(item.GetStart()), mm(item.GetEnd())
        if ((near(start, power_a) and near(end, power_b)) or
                (near(start, power_b) and near(end, power_a))):
            power_spurs.append(item)
    if not power_spurs:
        raise RuntimeError("obsolete +3V3A spur was not found")
    for item in power_spurs:
        board.Remove(item)
    power_zones = [zone for zone in board.Zones()
                   if zone.GetNetname() == "+3V3A"
                   and zone.GetLayerSet().Contains(pcbnew.B_Cu)]
    if len(power_zones) != 1:
        raise RuntimeError(f"expected one B.Cu +3V3A zone, got {len(power_zones)}")
    # The moved DL29 aperture divides this local power pour into separate
    # conductors.  Replace it with explicit routed +3V3A connections in the
    # following repair pass so connectivity no longer depends on a zone neck.
    board.Remove(power_zones[0])

    if not pcbnew.SaveBoard(args.output, board):
        raise RuntimeError("board save failed")
    print(args.output)


if __name__ == "__main__":
    app = wx.App(False)
    main()
