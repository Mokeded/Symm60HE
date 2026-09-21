#!/usr/bin/env python3
"""Resolve the remaining universal-half fabrication clearances.

The bottom-row layout alternatives place two Hall centres only 4.7625 mm
apart.  Their one shared reverse-mount LED is moved farther toward the inside
of both keycap envelopes so its full manufacturer/KiCad aperture clears both
sets of alignment holes.  Nearby Hall bypass capacitors move with their
attached traces.  A few pre-existing outer-edge vias/vertices are also nudged
inboard to satisfy the configured 0.20 mm copper-to-edge rule.

This script deliberately moves connected track endpoints with a footprint or
via.  Copper crossing a relocated LED aperture is removed in a separate,
explicit ``clear_variant_led_apertures.py`` pass and then rerouted from DRC
opens.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import wx
import pcbnew


LED_POSITIONS = {
    "Left": {
        "DL27": (10.9535, 78.0000),
        "DL29": (44.2915, 78.0000),
    },
    "Right": {
        "DR29": (255.7460, 78.0000),
        "DR31": (289.0840, 78.0000),
    },
}

# Kept as a separate map so future mechanical revisions can move a nearby
# bypass part through the same connected-endpoint-safe path when necessary.
CAP_POSITIONS = {
    "Left": {
        "CL28A": (6.3350, 78.8250),
        "RBPL29": (44.5000, 81.5000),
    },
    "Right": {"CR31A": (251.1270, 78.8250)},
}


def mm(point):
    return tuple(float(value) for value in pcbnew.ToMM(point))


def close(a, b, tolerance=0.002):
    return abs(a[0] - b[0]) <= tolerance and abs(a[1] - b[1]) <= tolerance


def set_track_endpoint(track, old, new):
    changed = False
    if close(mm(track.GetStart()), old):
        track.SetStart(pcbnew.VECTOR2I_MM(*new))
        changed = True
    if close(mm(track.GetEnd()), old):
        track.SetEnd(pcbnew.VECTOR2I_MM(*new))
        changed = True
    return changed


def move_footprint_with_tracks(board, reference, destination):
    footprint = board.FindFootprintByReference(reference)
    if footprint is None:
        raise RuntimeError(f"missing footprint {reference}")
    before = [(pad.GetNetname(), mm(pad.GetPosition()))
              for pad in footprint.Pads()]
    footprint.SetPosition(pcbnew.VECTOR2I_MM(*destination))
    after = [(pad.GetNetname(), mm(pad.GetPosition()))
             for pad in footprint.Pads()]
    for (old_net, old), (new_net, new) in zip(before, after):
        if old_net != new_net:
            raise RuntimeError(f"{reference}: pad order changed while moving")
        if close(old, new):
            continue
        for track in board.GetTracks():
            if isinstance(track, pcbnew.PCB_VIA):
                continue
            if track.GetNetname() == old_net:
                set_track_endpoint(track, old, new)


def rotate_component_keep_npth(board, reference, rotation=90.0):
    """Rotate the Hall package while preserving its switch-alignment holes."""
    footprint = board.FindFootprintByReference(reference)
    if footprint is None:
        raise RuntimeError(f"missing footprint {reference}")
    npth = [(pad, pad.GetPosition()) for pad in footprint.Pads()
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH]
    copper_before = [(pad, pad.GetNetname(), mm(pad.GetPosition()))
                     for pad in footprint.Pads()
                     if pad.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH]
    footprint.SetOrientationDegrees(rotation)
    for pad, position in npth:
        pad.SetPosition(position)
    for pad, net, old in copper_before:
        new = mm(pad.GetPosition())
        if close(old, new):
            continue
        for track in board.GetTracks():
            if not isinstance(track, pcbnew.PCB_VIA) and track.GetNetname() == net:
                set_track_endpoint(track, old, new)


def move_via_with_tracks(board, net, old, new):
    matches = []
    for item in board.GetTracks():
        if (isinstance(item, pcbnew.PCB_VIA) and item.GetNetname() == net
                and close(mm(item.GetPosition()), old)):
            matches.append(item)
    if len(matches) != 1:
        raise RuntimeError(f"expected one {net} via at {old}, found {len(matches)}")
    matches[0].SetPosition(pcbnew.VECTOR2I_MM(*new))
    for track in board.GetTracks():
        if isinstance(track, pcbnew.PCB_VIA):
            continue
        if track.GetNetname() == net:
            set_track_endpoint(track, old, new)


def move_vertices(board, net, point_map):
    changed = 0
    for track in board.GetTracks():
        if isinstance(track, pcbnew.PCB_VIA) or track.GetNetname() != net:
            continue
        for old, new in point_map:
            changed += int(set_track_endpoint(track, old, new))
    if not changed:
        raise RuntimeError(f"no {net} track vertices matched")


def edit(path, side):
    board = pcbnew.LoadBoard(str(path))
    if board is None:
        raise RuntimeError(f"cannot load {path}")

    for reference, destination in LED_POSITIONS[side].items():
        move_footprint_with_tracks(board, reference, destination)
    for reference, destination in CAP_POSITIONS[side].items():
        move_footprint_with_tracks(board, reference, destination)

    if side == "Left":
        move_via_with_tracks(board, "RGB_L_01", (14.1550, 0.9727),
                             (14.1550, 1.1500))
    else:
        move_via_with_tracks(board, "RGB_R_05", (288.3057, 0.9102),
                             (288.3057, 1.1500))
        move_via_with_tracks(board, "GND", (277.2383, 5.2800),
                             (277.0000, 7.0000))
        move_vertices(board, "RGB_R", [
            ((201.0468, 3.7620), (201.0468, 4.0500)),
            ((205.4850, 3.7620), (205.4850, 4.0500)),
        ])
        move_vertices(board, "RGB_R_06", [
            ((170.9883, 12.2800), (171.2000, 12.5000)),
        ])

    if not pcbnew.SaveBoard(str(path), board):
        raise RuntimeError(f"failed to save {path}")
    print(f"{path.name}: applied aperture-safe component and edge-copper moves")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board_dir", type=Path)
    args = parser.parse_args()
    for side in ("Left", "Right"):
        path = args.board_dir / f"Symm60HE-{side}.kicad_pcb"
        if not path.is_file():
            raise SystemExit(f"missing {path}")
        edit(path, side)


if __name__ == "__main__":
    app = wx.App(False)
    main()
