#!/usr/bin/env python3
"""Tie every filled B.Cu GND island to filled F.Cu GND with safe vias."""

import argparse

import wx
import pcbnew


def safely_inside(bottom, top, bottom_outline, top_outline, point,
                  margin_mm=0.55):
    delta = pcbnew.FromMM(margin_mm)
    probes = (
        point,
        pcbnew.VECTOR2I(point.x + delta, point.y),
        pcbnew.VECTOR2I(point.x - delta, point.y),
        pcbnew.VECTOR2I(point.x, point.y + delta),
        pcbnew.VECTOR2I(point.x, point.y - delta),
    )
    return all(bottom.Contains(probe) and top.Contains(probe)
               and bottom_outline.PointInside(probe)
               and top_outline.PointInside(probe)
               for probe in probes)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    ground_zones = [zone for zone in board.Zones()
                    if zone.GetNetname() == "GND"]
    top_zone = next(zone for zone in ground_zones
                    if zone.GetLayerSet().Contains(pcbnew.F_Cu))
    bottom_zone = next(zone for zone in ground_zones
                       if zone.GetLayerSet().Contains(pcbnew.B_Cu))
    top = top_zone.GetFilledPolysList(pcbnew.F_Cu)
    bottom = bottom_zone.GetFilledPolysList(pcbnew.B_Cu)
    ground = board.FindNet("GND")
    existing = [track.GetPosition() for track in board.GetTracks()
                if isinstance(track, pcbnew.PCB_VIA)]
    placed = []
    step = pcbnew.FromMM(0.75)
    for bottom_index in range(bottom.OutlineCount()):
        bottom_outline = bottom.Outline(bottom_index)
        bottom_box = bottom_outline.BBox()
        for top_index in range(top.OutlineCount()):
            top_outline = top.Outline(top_index)
            top_box = top_outline.BBox()
            x0 = max(bottom_box.GetX(), top_box.GetX())
            y0 = max(bottom_box.GetY(), top_box.GetY())
            x1 = min(bottom_box.GetRight(), top_box.GetRight())
            y1 = min(bottom_box.GetBottom(), top_box.GetBottom())
            if x1 <= x0 or y1 <= y0:
                continue
            found = None
            y = y0 + step
            while y < y1 - step and found is None:
                x = x0 + step
                while x < x1 - step:
                    point = pcbnew.VECTOR2I(x, y)
                    if (safely_inside(bottom, top, bottom_outline,
                                      top_outline, point)
                            and all((point - via_point).EuclideanNorm()
                                    > pcbnew.FromMM(0.80)
                                    for via_point in existing + placed)):
                        found = point
                        break
                    x += step
                y += step
            if found is None:
                continue
            via = pcbnew.PCB_VIA(board)
            via.SetNet(ground)
            via.SetPosition(found)
            via.SetWidth(pcbnew.FromMM(0.60))
            via.SetDrill(pcbnew.FromMM(0.30))
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            board.Add(via)
            placed.append(found)

    if not pcbnew.ZONE_FILLER(board).Fill(board.Zones()):
        raise RuntimeError("zone refill failed")
    if not pcbnew.SaveBoard(args.output, board):
        raise RuntimeError("board save failed")
    print("placed", len(placed), "island vias")


if __name__ == "__main__":
    main()
