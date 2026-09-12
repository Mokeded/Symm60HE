#!/usr/bin/env python3
"""Extend the copper planes into the two removed U-shaped board notches.

Run with KiCad's bundled Python so pcbnew can persist freshly calculated zone
fills.  Both the B.Cu GND plane and F.Cu +3V3A plane previously retained the
old cutout in their zone polygons.  The 0.5 mm overlap joins the added region
to each existing zone outline; KiCad clips the resulting fill to Edge.Cuts.
"""
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent.parent
NOTCHES = {
    "Left": [(58.1980, 97.2500), (58.1980, 78.2011),
             (69.0157, 78.2067), (68.4268, 97.1781)],
    "Right": [(231.6102, 97.1771), (231.0214, 78.2067),
              (241.8395, 78.2011), (241.8395, 97.2500)],
}
TEST_POINTS = {"Left": (63.5, 88.0), "Right": (236.5, 88.0)}
OVERLAP = 0.5
PLANE_NETS = ("GND", "+3V3A")


def expanded(points):
    x0 = min(x for x, _ in points) - OVERLAP
    x1 = max(x for x, _ in points) + OVERLAP
    y0 = min(y for _, y in points) - OVERLAP
    y1 = max(y for _, y in points) + OVERLAP
    return [(x0, y1), (x0, y0), (x1, y0), (x1, y1)]


for side, points in NOTCHES.items():
    path = ROOT / "pcb" / f"Symm60HE-{side}.kicad_pcb"
    board = pcbnew.LoadBoard(str(path))
    before = (len(board.GetTracks()), len(board.GetFootprints()),
              len(board.GetDrawings()))
    planes = {}
    for netname in PLANE_NETS:
        matching = [zone for zone in board.Zones()
                    if zone.GetNetname() == netname]
        if len(matching) != 1:
            raise RuntimeError(
                f"{side}: expected one {netname} zone, found {len(matching)}")
        planes[netname] = matching[0]

        chain = pcbnew.SHAPE_LINE_CHAIN()
        for x, y in expanded(points):
            chain.Append(pcbnew.VECTOR2I_MM(x, y))
        chain.SetClosed(True)
        addition = pcbnew.SHAPE_POLY_SET()
        addition.AddOutline(chain)
        matching[0].Outline().BooleanAdd(addition)
        matching[0].Outline().SimplifyOutlines()

    if not pcbnew.ZONE_FILLER(board).Fill(board.Zones()):
        raise RuntimeError(f"{side}: KiCad zone refill failed")
    point = pcbnew.VECTOR2I_MM(*TEST_POINTS[side])
    for netname, zone in planes.items():
        filled = zone.GetFilledPolysList(zone.GetLayer())
        if not filled.Contains(point):
            raise RuntimeError(f"{side}: {netname} did not fill the removed notch")
    after = (len(board.GetTracks()), len(board.GetFootprints()),
             len(board.GetDrawings()))
    if before != after:
        raise RuntimeError(f"{side}: non-zone PCB object counts changed")
    if not pcbnew.SaveBoard(str(path), board):
        raise RuntimeError(f"{side}: board save failed")

    check = pcbnew.LoadBoard(str(path))
    for netname in PLANE_NETS:
        zone = [z for z in check.Zones() if z.GetNetname() == netname][0]
        persisted = zone.GetFilledPolysList(zone.GetLayer()).Contains(point)
        if not persisted:
            raise RuntimeError(f"{side}: saved {netname} fill did not persist")
    print(f"{side}: GND and +3V3A filled through removed notch")
