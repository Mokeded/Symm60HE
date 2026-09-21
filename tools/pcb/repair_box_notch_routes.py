#!/usr/bin/env python3
"""Repair the two local routes displaced by the rectangular FPC notch."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from route import seg, via  # noqa: E402
from sexp import dumps, first, loads  # noqa: E402


BOARD_DIR = (ROOT / "work" /
             "enclosure-style-hotswap-freerouting-candidate" /
             "routed-final")


def segment_key(item):
    start, end = first(item, "start"), first(item, "end")
    return tuple(round(float(value), 4) for value in
                 (start[1], start[2], end[1], end[2]))


def via_key(item):
    position = first(item, "at")
    return (round(float(position[1]), 4), round(float(position[2]), 4))


def remove_route_items(board, net, segments=(), vias=()):
    segments = {tuple(round(value, 4) for value in item)
                for item in segments}
    segments |= {(x1, y1, x0, y0) for x0, y0, x1, y1 in segments}
    vias = {tuple(round(value, 4) for value in item) for item in vias}
    kept = [board[0]]
    for item in board[1:]:
        if not isinstance(item, list) or not item:
            kept.append(item)
            continue
        kind = str(item[0])
        item_net = first(item, "net")
        if not item_net or str(item_net[1]) != net:
            kept.append(item)
        elif kind == "segment" and segment_key(item) in segments:
            continue
        elif kind == "via" and via_key(item) in vias:
            continue
        else:
            kept.append(item)
    board[:] = kept


def append(board, items):
    insert = next((index for index in range(len(board) - 1, 0, -1)
                   if isinstance(board[index], list) and board[index] and
                   str(board[index][0]) == "embedded_fonts"), len(board))
    board[insert:insert] = items


def repair_left(board):
    # Remove the first automatic repair's branch to the wrong end of the old
    # vertical run, plus any prior copy of the deterministic replacement.
    remove_route_items(board, "ADC_L4", segments=(
        (130.7970, 71.0543, 138.2970, 63.5543),
        (138.2970, 63.5543, 138.2970, 55.0543),
        (138.2970, 55.0543, 138.2129, 53.2690),
        (130.7970, 71.0543, 130.7970, 69.8043),
        (130.7970, 69.8043, 135.5470, 65.0543),
        (135.5470, 65.0543, 138.2129, 65.0027),
    ))
    append(board, [
        seg((130.7970, 71.0543), (130.7970, 69.8043), "ADC_L4", "F.Cu"),
        seg((130.7970, 69.8043), (135.5470, 65.0543), "ADC_L4", "F.Cu"),
        seg((135.5470, 65.0543), (138.2129, 65.0027), "ADC_L4", "F.Cu"),
    ])

    # The spacebar-parallel upper rail removes the former diagonal +3V3A
    # shortcut through the cutout.  Stay above the sloped edge while crossing
    # the FPC shoulder, then turn down only after reaching the board side of
    # the vertical pocket wall.
    power_segments = (
        (139.1090, 63.5000, 135.0000, 63.5000),
        (135.0000, 63.5000, 131.1000, 67.4000),
        (131.1000, 67.4000, 130.2987, 72.3103),
    )
    remove_route_items(board, "+3V3A", segments=power_segments)
    append(board, [
        seg(item[:2], item[2:], "+3V3A", "B.Cu")
        for item in power_segments
    ])


def repair_right(board):
    # The compact passage beside the mirrored notch requires a short two-via
    # layer change. Re-emit the proven path deterministically and idempotently.
    segments = (
        (169.7982, 68.2954, 169.9796, 68.3043),
        (169.9796, 68.3043, 170.4796, 68.3043),
        (170.4796, 68.3043, 171.2296, 69.0543),
        (171.2296, 69.0543, 171.2296, 70.0543),
        (171.2296, 70.0543, 171.4796, 70.3043),
        (171.4796, 70.3043, 175.4796, 74.3043),
        (175.4796, 74.3043, 176.9003, 75.2272),
    )
    vias = ((169.9796, 68.3043), (171.4796, 70.3043))
    remove_route_items(board, "+3V3A", segments=segments, vias=vias)
    append(board, [
        seg(segments[0][:2], segments[0][2:], "+3V3A", "B.Cu"),
        seg(segments[1][:2], segments[1][2:], "+3V3A", "F.Cu"),
        seg(segments[2][:2], segments[2][2:], "+3V3A", "F.Cu"),
        seg(segments[3][:2], segments[3][2:], "+3V3A", "F.Cu"),
        seg(segments[4][:2], segments[4][2:], "+3V3A", "F.Cu"),
        seg(segments[5][:2], segments[5][2:], "+3V3A", "B.Cu"),
        seg(segments[6][:2], segments[6][2:], "+3V3A", "B.Cu"),
        via(vias[0], "+3V3A"),
        via(vias[1], "+3V3A"),
    ])

    # Keep ADC_R4 on F.Cu through the narrow shoulder.  It passes above the
    # local +3V3A dogleg, then bends through the controlled gap between MUX_A0
    # and the rounded rail corner before descending on the board side of the
    # pocket wall.
    old_adc_segments = (
        (163.8578, 69.0448, 164.5000, 67.5000),
        (164.5000, 67.5000, 173.4000, 67.5000),
        (173.4000, 67.5000, 173.4000, 70.0000),
        (173.4000, 70.0000, 176.0392, 75.9481),
        (163.8578, 69.0448, 164.5000, 68.5000),
        (164.5000, 68.5000, 168.5000, 68.5000),
        (168.5000, 68.5000, 172.3000, 67.9000),
        (172.3000, 67.9000, 173.5000, 68.8000),
        (173.5000, 68.8000, 173.5000, 72.0000),
        (173.5000, 72.0000, 176.0392, 75.9481),
        (168.5000, 67.4000, 172.3000, 67.4000),
        (172.3000, 67.4000, 172.9000, 68.0000),
        (172.9000, 68.0000, 173.5000, 68.8000),
        (173.5000, 68.8000, 173.5000, 72.0000),
    )
    adc_segments = (
        (163.8578, 69.0448, 164.5000, 67.4000),
        (164.5000, 67.4000, 168.5000, 67.4000),
        (168.5000, 67.4000, 172.3000, 67.5000),
        (172.3000, 67.5000, 172.9000, 68.1000),
        (172.9000, 68.1000, 173.5000, 68.9000),
        (173.5000, 68.9000, 173.5000, 72.0000),
        (173.5000, 72.0000, 176.0392, 75.9481),
    )
    remove_route_items(board, "ADC_R4",
                       segments=old_adc_segments + adc_segments,
                       vias=((173.5000, 68.8000),))
    ground_taps = (
        (176.6031, 73.3506, 170.7560, 68.3614),
        (173.8775, 66.2901, 170.7560, 68.3614),
    )
    ground_escape = (170.7560, 68.3614, 170.7560, 66.5000)
    ground_via = (170.7560, 66.5000)
    # JR1 pad 8 formerly relied on the old B.Cu fill shape.  Give it an
    # explicit short escape and stitching via so outline refills cannot leave
    # the connector ground pad isolated.
    connector_ground = (165.3090, 56.5000, 163.8000, 56.5000)
    connector_ground_via = (163.8000, 56.5000)
    remove_route_items(board, "GND", segments=ground_taps)
    remove_route_items(board, "GND", segments=(
        (170.4883, 69.5300, 170.5103, 69.6990),
        (170.5103, 69.6990, 170.7560, 68.3614),
        ground_escape,
    ), vias=((170.4883, 69.5300), ground_via,
             (302.2000, 90.0000), connector_ground_via))
    remove_route_items(board, "GND", segments=(connector_ground,))
    append(board, [
        *[seg(item[:2], item[2:], "ADC_R4", "F.Cu")
          for item in adc_segments],
        *[seg(item[:2], item[2:], "GND", "B.Cu")
          for item in ground_taps],
        seg(ground_escape[:2], ground_escape[2:], "GND", "B.Cu"),
        via(ground_via, "GND"),
        seg(connector_ground[:2], connector_ground[2:], "GND", "B.Cu"),
        via(connector_ground_via, "GND"),
    ])


def main():
    for side, repair in (("Left", repair_left), ("Right", repair_right)):
        path = BOARD_DIR / f"Symm60HE-{side}.kicad_pcb"
        board = loads(path.read_text())
        repair(board)
        path.write_text(dumps(board) + "\n")
        print(path.name, "box-notch route repaired")


if __name__ == "__main__":
    main()
