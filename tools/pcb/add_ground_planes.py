#!/usr/bin/env python3
"""Add and fill full-board GND zones on both copper layers."""

import argparse

import wx
import pcbnew


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    args = parser.parse_args()

    app = wx.App(False)
    board = pcbnew.LoadBoard(args.board)
    ground = board.FindNet("GND")
    if ground is None:
        raise SystemExit("board has no GND net")

    outline = pcbnew.SHAPE_POLY_SET()
    if not board.GetBoardPolygonOutlines(outline, False, None, False, False):
        raise SystemExit("could not construct a closed board outline")

    # SetOutline does not take ownership in the Python bindings.  Retain the
    # cloned polygons until after fill/save or SWIG can free them too early.
    zone_outlines = []
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        zone = pcbnew.ZONE(board)
        zone.SetNet(ground)
        zone_outline = outline.CloneDropTriangulation()
        zone_outlines.append(zone_outline)
        zone.SetOutline(zone_outline)
        # Zones serialize their layer set, not only BOARD_ITEM::m_layer.
        layer_set = pcbnew.LSET()
        layer_set.AddLayer(layer)
        zone.SetLayerSet(layer_set)
        zone.SetLocalClearance(pcbnew.FromMM(0.20))
        zone.SetMinThickness(pcbnew.FromMM(0.20))
        # The dense Hall/LED fields do not leave room for four thermal spokes
        # on every 0402 and sensor pad.  Solid GND joins avoid starved pads and
        # are appropriate for these small ground terminals.
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        zone.SetThermalReliefGap(pcbnew.FromMM(0.30))
        zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.30))
        zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        board.Add(zone)

    if not pcbnew.ZONE_FILLER(board).Fill(board.Zones()):
        raise SystemExit("zone fill failed")
    if not pcbnew.SaveBoard(args.output, board):
        raise SystemExit("board save failed")
    print(args.output)


if __name__ == "__main__":
    main()
