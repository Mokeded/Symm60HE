#!/usr/bin/env python3
"""Apply deterministic clearance detours for fixed-layout LED routes."""
from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import Sym, dumps, find, first, loads  # noqa: E402


def point(node):
    return (float(node[1]), float(node[2]))


def close(a, b, tolerance=0.002):
    return math.dist(a, b) <= tolerance


def segment(a, b, net, width="0.200", layer="B.Cu"):
    return [Sym("segment"),
            [Sym("start"), Sym(f"{a[0]:.6f}"), Sym(f"{a[1]:.6f}")],
            [Sym("end"), Sym(f"{b[0]:.6f}"), Sym(f"{b[1]:.6f}")],
            [Sym("width"), Sym(width)],
            [Sym("layer"), layer],
            [Sym("net"), net],
            [Sym("uuid"), str(uuid.uuid4())]]


def via(at, net):
    return [Sym("via"),
            [Sym("at"), Sym(f"{at[0]:.6f}"), Sym(f"{at[1]:.6f}")],
            [Sym("size"), Sym("0.600")],
            [Sym("drill"), Sym("0.300")],
            [Sym("layers"), "F.Cu", "B.Cu"],
            [Sym("net"), net],
            [Sym("uuid"), str(uuid.uuid4())]]


def compact_via(at, net):
    """Return a standard project via for a locally selected clear position."""
    return via(at, net)


def append_item(board, item):
    index = next((i for i in range(len(board) - 1, 0, -1)
                  if isinstance(board[i], list) and board[i] and
                  str(board[i][0]) == "embedded_fonts"), len(board))
    board.insert(index, item)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    board = loads(args.board.read_text())
    # WKL-left's recentered DL29 aperture makes the automatic repair choose a
    # short B.Cu run immediately below AML5.  The electrical path is valid but
    # misses the two mux pads' local clearance by less than 0.15 mm.  Put only
    # that exact run on F.Cu between its existing endpoint vias; the aperture
    # and the mux pads then remain clear on both layers.
    power_parts = []
    power_expected = (
        ((37.5470, 76.3043), (38.0470, 76.3043)),
        ((38.0470, 76.3043), (40.0470, 76.0543)),
        ((40.0470, 76.0543), (44.0470, 76.0543)),
    )
    for item in board[1:]:
        if not (isinstance(item, list) and item and
                str(item[0]) == "segment"):
            continue
        net, layer = first(item, "net"), first(item, "layer")
        if (not net or str(net[1]) != "+3V3A" or not layer or
                str(layer[1]) != "B.Cu"):
            continue
        a, b = point(first(item, "start")), point(first(item, "end"))
        if any((close(a, p) and close(b, q)) or
               (close(a, q) and close(b, p))
               for p, q in power_expected):
            power_parts.append(item)
    if len(power_parts) == len(power_expected):
        width = str(first(power_parts[0], "width")[1])
        for item in power_parts:
            board.remove(item)
        for item in list(board[1:]):
            if not (isinstance(item, list) and item and
                    str(item[0]) == "via"):
                continue
            net = first(item, "net")
            if (net and str(net[1]) == "+3V3A" and
                    any(close(point(first(item, "at")), endpoint)
                        for endpoint in (power_expected[0][0],
                                         power_expected[-1][1]))):
                board.remove(item)
        elbow = (37.7970, 76.0543)
        append_item(board, segment(power_expected[0][0], elbow, "+3V3A",
                                   width, "F.Cu"))
        append_item(board, segment(elbow, power_expected[-1][1], "+3V3A",
                                   width, "F.Cu"))

    # Centring split-Backspace DR5 puts its aperture close to the universal
    # RGB_R_05 escape.  Move the three-segment knee 0.25 mm farther from the
    # opening while preserving its two proven endpoints.
    backspace_expected = (
        ((287.4796, 6.0543), (288.9796, 4.5543)),
        ((288.9796, 4.5543), (290.7296, 4.5543)),
        ((290.7296, 4.5543), (291.2296, 4.0543)),
    )
    backspace_parts = []
    for item in board[1:]:
        if not (isinstance(item, list) and item and
                str(item[0]) == "segment"):
            continue
        net, layer = first(item, "net"), first(item, "layer")
        if (not net or str(net[1]) != "RGB_R_05" or not layer or
                str(layer[1]) != "F.Cu"):
            continue
        a, b = point(first(item, "start")), point(first(item, "end"))
        if any((close(a, p) and close(b, q)) or
               (close(a, q) and close(b, p))
               for p, q in backspace_expected):
            backspace_parts.append(item)
    if len(backspace_parts) == len(backspace_expected):
        width = str(first(backspace_parts[0], "width")[1])
        for item in backspace_parts:
            board.remove(item)
        knee_a = (288.9796, 4.8043)
        knee_b = (290.7296, 4.8043)
        append_item(board, segment(backspace_expected[0][0], knee_a,
                                   "RGB_R_05", width, "F.Cu"))
        append_item(board, segment(knee_a, knee_b, "RGB_R_05", width,
                                   "F.Cu"))
        append_item(board, segment(knee_b, backspace_expected[-1][1],
                                   "RGB_R_05", width, "F.Cu"))

    # This tiny GND-zone seed is unnecessary after DR31 is recentered and sits
    # 0.1689 mm from the milled aperture.  The surrounding two-layer pour
    # remains the actual connection.
    for item in list(board[1:]):
        if not (isinstance(item, list) and item and
                str(item[0]) == "segment"):
            continue
        net = first(item, "net")
        if not net or str(net[1]) != "GND":
            continue
        a, b = point(first(item, "start")), point(first(item, "end"))
        if ((close(a, (285.2383, 76.2800)) and
             close(b, (285.3450, 76.2400))) or
                (close(b, (285.2383, 76.2800)) and
                 close(a, (285.3450, 76.2400)))):
            board.remove(item)

    # The normal-position centre-arrow aperture separates DR36 pad 4 from the
    # universal RGB_R_30 tail below it.  Join them around the opening's right
    # side, but only when no routed segment already terminates on the LED pad.
    arrow_pad = (275.1400, 77.3750)
    arrow_tail = (273.9796, 80.5543)
    trial_path = [arrow_pad, (274.7500, 77.7650),
                  (274.7500, 80.0000), arrow_tail]
    trial_pairs = tuple(zip(trial_path, trial_path[1:]))
    for item in list(board[1:]):
        if not (isinstance(item, list) and item and
                str(item[0]) == "segment"):
            continue
        net = first(item, "net")
        if not net or str(net[1]) != "RGB_R_30":
            continue
        a, b = point(first(item, "start")), point(first(item, "end"))
        if any((close(a, p) and close(b, q)) or
               (close(a, q) and close(b, p)) for p, q in trial_pairs):
            board.remove(item)

    arrow_connected = False
    arrow_tail_present = False
    for item in board[1:]:
        if not (isinstance(item, list) and item and
                str(item[0]) == "segment"):
            continue
        net = first(item, "net")
        if not net or str(net[1]) != "RGB_R_30":
            continue
        a, b = point(first(item, "start")), point(first(item, "end"))
        arrow_connected |= close(a, arrow_pad) or close(b, arrow_pad)
        arrow_tail_present |= close(a, arrow_tail) or close(b, arrow_tail)
    if arrow_tail_present and not arrow_connected:
        via_a = (276.2400, 77.3750)
        via_b = (274.7800, 80.5543)
        append_item(board, segment(arrow_pad, via_a, "RGB_R_30",
                                   "0.200", "B.Cu"))
        append_item(board, via(via_a, "RGB_R_30"))
        append_item(board, segment(via_a, via_b, "RGB_R_30",
                                   "0.200", "F.Cu"))
        append_item(board, via(via_b, "RGB_R_30"))
        append_item(board, segment(via_b, arrow_tail, "RGB_R_30",
                                   "0.200", "B.Cu"))

    # With the obsolete zone-outline voids removed, KiCad can legally refill
    # and repair the lower RGB_R_30 branch farther to the right.  That newer
    # path ends at x=275.14 just below the aperture, leaving only a short
    # straight gap to DR36 pad 4.  Join that exact endpoint when present; it
    # stays outside the milled opening and avoids unnecessary layer changes.
    refilled_tail = (275.1400, 80.1012)
    # Remove the earlier straight trial, which crosses DR36's VBUS pad.
    removed_straight = False
    for item in list(board[1:]):
        if not (isinstance(item, list) and item and
                str(item[0]) == "segment"):
            continue
        net = first(item, "net")
        if not net or str(net[1]) != "RGB_R_30":
            continue
        a, b = point(first(item, "start")), point(first(item, "end"))
        if ((close(a, arrow_pad) and close(b, refilled_tail)) or
                (close(b, arrow_pad) and close(a, refilled_tail))):
            board.remove(item)
            removed_straight = True
    if removed_straight:
        arrow_connected = False

    # Remove the first two-via trial.  Its F.Cu vertical crossed RGB_R_31 and
    # its lower via approached the VBUS trunk on B.Cu.
    old_via_a = (276.2400, 77.3750)
    old_via_b = (276.2400, 80.1012)
    old_via_c = (277.2000, 77.3750)
    old_bend_c = (277.2000, 80.5000)
    old_via_d = (275.1400, 75.3000)
    old_bend_d1 = (277.0000, 75.3000)
    old_bend_d2 = (277.0000, 80.5000)
    old_via_e = (275.1400, 75.1500)
    old_bend_e1 = (277.0500, 75.1500)
    old_bend_e2 = (277.0500, 80.5000)
    existing_via = (275.2296, 81.0543)
    final_via_a = (277.1000, 76.8000)
    final_bend = (277.1000, 80.5000)
    final_escape_via = (274.7800, 80.5543)
    old_pairs = ((arrow_pad, old_via_a), (old_via_a, old_via_b),
                 (old_via_b, refilled_tail), (arrow_pad, old_via_c),
                 (old_via_c, old_bend_c), (old_bend_c, existing_via),
                 (arrow_pad, old_via_d), (old_via_d, old_bend_d1),
                 (old_bend_d1, old_bend_d2),
                 (old_bend_d2, existing_via), (arrow_pad, old_via_e),
                 (old_via_e, old_bend_e1),
                 (old_bend_e1, old_bend_e2),
                 (old_bend_e2, existing_via),
                 # Superseded final escape.  Its vertical F.Cu leg crossed
                 # the long RGB_R_31 diagonal produced by a fresh refill.
                 (arrow_pad, final_via_a), (final_via_a, final_bend),
                 (final_bend, existing_via),
                 (final_via_a, final_escape_via))
    removed_old_trial = False
    for item in list(board[1:]):
        if not (isinstance(item, list) and item and
                str(item[0]) in ("segment", "via")):
            continue
        net = first(item, "net")
        if not net or str(net[1]) != "RGB_R_30":
            continue
        if str(item[0]) == "via":
            if any(close(point(first(item, "at")), target)
                   for target in (old_via_a, old_via_b, old_via_c,
                                  old_via_d, old_via_e, final_via_a)):
                board.remove(item)
                removed_old_trial = True
            continue
        a, b = point(first(item, "start")), point(first(item, "end"))
        if any((close(a, p) and close(b, q)) or
               (close(a, q) and close(b, p)) for p, q in old_pairs):
            board.remove(item)
            removed_old_trial = True
    if removed_old_trial:
        arrow_connected = False

    # Restore the short RGB_R_31 diagonal to F.Cu if an earlier routing trial
    # moved it to B.Cu.  The final RGB_R_30 escape starts below/right of this
    # segment and does not require changing the neighbouring LED net.
    rgb31_a = (276.4796, 76.3043)
    rgb31_b = (277.4796, 75.5543)
    rgb31_back = None
    rgb31_front_present = False
    for item in list(board[1:]):
        if not (isinstance(item, list) and item and
                str(item[0]) == "segment"):
            continue
        net, layer = first(item, "net"), first(item, "layer")
        if not net or str(net[1]) != "RGB_R_31" or not layer:
            continue
        a, b = point(first(item, "start")), point(first(item, "end"))
        if ((close(a, rgb31_a) and close(b, rgb31_b)) or
                (close(b, rgb31_a) and close(a, rgb31_b))):
            if str(layer[1]) == "B.Cu":
                rgb31_back = item
            elif str(layer[1]) == "F.Cu":
                rgb31_front_present = True
    if rgb31_back is not None:
        width = str(first(rgb31_back, "width")[1])
        board.remove(rgb31_back)
        for item in list(board[1:]):
            if not (isinstance(item, list) and item and
                    str(item[0]) == "via"):
                continue
            net = first(item, "net")
            if (net and str(net[1]) == "RGB_R_31" and
                    any(close(point(first(item, "at")), target)
                        for target in (rgb31_a, rgb31_b))):
                board.remove(item)
        if not rgb31_front_present:
            append_item(board, segment(rgb31_a, rgb31_b, "RGB_R_31",
                                       width, "F.Cu"))

    if (not arrow_connected and
            os.environ.get("SYMM60_SKIP_RGB_R30_FALLBACK") != "1"):
        refilled_tail_present = False
        for item in board[1:]:
            if not (isinstance(item, list) and item and
                    str(item[0]) == "segment"):
                continue
            net = first(item, "net")
            if not net or str(net[1]) != "RGB_R_30":
                continue
            a, b = point(first(item, "start")), point(first(item, "end"))
            refilled_tail_present |= (close(a, refilled_tail) or
                                      close(b, refilled_tail))
        if refilled_tail_present:
            # The legal corridor is only 0.15 mm wide.  Leave DR36 on B.Cu,
            # cross the short clear vertical channel on F.Cu, then return to
            # the B.Cu tail below the aperture.  This exact five-object path
            # is fresh-DRC clean for both arrow representatives.
            proven_via_a = (275.0000, 77.5000)
            proven_via_b = (275.0000, 79.7500)
            append_item(board, segment(arrow_pad, proven_via_a, "RGB_R_30",
                                       "0.150", "B.Cu"))
            append_item(board, via(proven_via_a, "RGB_R_30"))
            append_item(board, segment(proven_via_a, proven_via_b,
                                       "RGB_R_30", "0.150", "F.Cu"))
            append_item(board, via(proven_via_b, "RGB_R_30"))
            append_item(board, segment(proven_via_b, refilled_tail,
                                       "RGB_R_30", "0.150", "B.Cu"))

    # The shifted grid retry uses this short horizontal run to join DR23 to
    # the recentered arrow-layout DR22.  Its direct position is marginal to
    # DR22's milled LED aperture, so dip it 0.50 mm before crossing.
    expected = ((269.6046, 57.1793), (274.6046, 57.1793))
    replaced = 0
    # Upgrade the earlier trial detours, if present, before looking for the
    # original one-piece route.  The 55.8 mm F.Cu trial collided with
    # RGB_R_21; 55.1 mm runs in the clear channel between RGB_R_21 and HE_R18.
    old_front = ((269.6046, 55.8000), (274.6046, 55.8000))
    old_front_items = []
    for item in board[1:]:
        if not (isinstance(item, list) and item and
                str(item[0]) in ("segment", "via")):
            continue
        net = first(item, "net")
        if not net or str(net[1]) != "RGB_R_22":
            continue
        if str(item[0]) == "via":
            if any(close(point(first(item, "at")), p) for p in old_front):
                old_front_items.append(item)
            continue
        a, b = point(first(item, "start")), point(first(item, "end"))
        candidates = ((expected[0], old_front[0]),
                      (old_front[0], old_front[1]),
                      (old_front[1], expected[1]))
        if any((close(a, p) and close(b, q)) or
               (close(a, q) and close(b, p)) for p, q in candidates):
            old_front_items.append(item)
    if len(old_front_items) == 5:
        width = next(str(first(item, "width")[1]) for item in old_front_items
                     if str(item[0]) == "segment")
        for item in old_front_items:
            board.remove(item)
        front_a = (expected[0][0], 55.1000)
        front_b = (expected[1][0], 55.1000)
        append_item(board, segment(expected[0], front_a, "RGB_R_22", width))
        append_item(board, via(front_a, "RGB_R_22"))
        append_item(board, segment(front_a, front_b, "RGB_R_22", width,
                                   "F.Cu"))
        append_item(board, via(front_b, "RGB_R_22"))
        append_item(board, segment(front_b, expected[1], "RGB_R_22", width))
        replaced += 1

    previous_low = ((269.6046, 56.6793), (274.6046, 56.6793))
    previous_parts = []
    for item in board[1:]:
        if not (isinstance(item, list) and item and
                str(item[0]) == "segment"):
            continue
        net, layer = first(item, "net"), first(item, "layer")
        if (not net or str(net[1]) != "RGB_R_22" or not layer or
                str(layer[1]) != "B.Cu"):
            continue
        a, b = point(first(item, "start")), point(first(item, "end"))
        candidates = ((expected[0], previous_low[0]),
                      (previous_low[0], previous_low[1]),
                      (previous_low[1], expected[1]))
        if any((close(a, p) and close(b, q)) or
               (close(a, q) and close(b, p)) for p, q in candidates):
            previous_parts.append(item)
    if len(previous_parts) == 3:
        width = str(first(previous_parts[0], "width")[1])
        for item in previous_parts:
            board.remove(item)
        front_a = (expected[0][0], 55.1000)
        front_b = (expected[1][0], 55.1000)
        append_item(board, segment(expected[0], front_a, "RGB_R_22", width))
        append_item(board, via(front_a, "RGB_R_22"))
        append_item(board, segment(front_a, front_b, "RGB_R_22", width,
                                   "F.Cu"))
        append_item(board, via(front_b, "RGB_R_22"))
        append_item(board, segment(front_b, expected[1], "RGB_R_22", width))
        replaced += 1

    for item in list(board[1:]):
        if not (isinstance(item, list) and item and
                str(item[0]) == "segment"):
            continue
        net, layer = first(item, "net"), first(item, "layer")
        if (not net or str(net[1]) != "RGB_R_22" or not layer or
                str(layer[1]) != "B.Cu"):
            continue
        a, b = point(first(item, "start")), point(first(item, "end"))
        if not ((close(a, expected[0]) and close(b, expected[1])) or
                (close(b, expected[0]) and close(a, expected[1]))):
            continue
        width = str(first(item, "width")[1])
        net_number = str(net[1])
        board.remove(item)
        # Drop below the nearby MUX_A2 via, cross on F.Cu, then return to the
        # existing B.Cu LED escape.  This clears both the milled aperture and
        # the diagonal MUX_A2 route beneath it.
        front_a = (expected[0][0], 55.1000)
        front_b = (expected[1][0], 55.1000)
        append_item(board, segment(expected[0], front_a, net_number, width))
        append_item(board, via(front_a, net_number))
        append_item(board, segment(front_a, front_b, net_number, width,
                                   "F.Cu"))
        append_item(board, via(front_b, net_number))
        append_item(board, segment(front_b, expected[1], net_number, width))
        replaced += 1

    # Removing the unused centre bottom-row key from the arrow variants also
    # removes the universal route which used to carry RGB_R_22 between DR23
    # and DR22.  Reconnect those two retained LEDs through the open channel
    # below RGB_R_21.  The upper via is pulled a further 0.25 mm away from the
    # neighbouring F.Cu trace than the automatic grid repair selected.
    arrow22_a = (250.6400, 59.8250)
    arrow22_b = (275.1400, 58.3250)
    arrow22_has_endpoint = False
    for item in board[1:]:
        if not (isinstance(item, list) and item and
                str(item[0]) == "segment"):
            continue
        net = first(item, "net")
        if not net or str(net[1]) != "RGB_R_22":
            continue
        a, b = point(first(item, "start")), point(first(item, "end"))
        arrow22_has_endpoint |= (close(a, arrow22_a) or close(b, arrow22_a) or
                                 close(a, arrow22_b) or close(b, arrow22_b))
    arrow22_variant = "arrows-right-Right.kicad_pcb" in args.board.name
    if arrow22_variant and not arrow22_has_endpoint:
        route = (arrow22_a, (251.7296, 61.5543),
                 (254.7296, 61.5543), (256.2296, 63.0543),
                 (261.7296, 63.0543))
        for a, b in zip(route, route[1:]):
            append_item(board, segment(a, b, "RGB_R_22", "0.150", "B.Cu"))
        append_item(board, via(route[-1], "RGB_R_22"))
        front_end = (272.9796, 55.3043)
        append_item(board, segment(route[-1], (269.2296, 55.5543),
                                   "RGB_R_22", "0.150", "F.Cu"))
        append_item(board, segment((269.2296, 55.5543), front_end,
                                   "RGB_R_22", "0.150", "F.Cu"))
        append_item(board, via(front_end, "RGB_R_22"))
        append_item(board, segment(front_end, (273.7296, 56.3043),
                                   "RGB_R_22", "0.150", "B.Cu"))
        append_item(board, segment((273.7296, 56.3043), arrow22_b,
                                   "RGB_R_22", "0.150", "B.Cu"))
        replaced += 1

    # In the WKL-left derivative CRGBL27's ground pad is the sole member of a
    # small B.Cu island.  A normal 0.60/0.30 mm stitching via cannot clear the
    # neighbouring sensor and RGB traces on both layers at the automatically
    # sampled points; the position below is the verified local overlap of that
    # island and the main F.Cu ground pour.
    # Limit it to the representative from which the matching permutations are
    # materialized, so other layouts keep their already-clean ground planes.
    if args.board.name == "Symm60HE-wkl-Left.kicad_pcb":
        # The removed layout-only apertures leave one nearly-zero-width cusp
        # at the source zone polygon's first vertex.  A 0.24 mm minimum fill
        # (still much smaller than the surrounding ground area) removes that
        # cusp during refill instead of preserving non-fabricable copper.
        for ground_zone in find(board, "zone"):
            net = first(ground_zone, "net")
            thickness = first(ground_zone, "min_thickness")
            if net and str(net[1]) == "GND" and thickness:
                thickness[1] = Sym("0.24")

        # Open a standards-compliant 0.60/0.30 mm via pocket by moving the
        # three nearby traces only a fraction of a millimetre.  Their original
        # endpoints are preserved, so the surrounding routes do not change.
        def replace_one(net_name, layer_name, old_a, old_b, new_points):
            for candidate in list(board[1:]):
                if not (isinstance(candidate, list) and candidate and
                        str(candidate[0]) == "segment"):
                    continue
                net = first(candidate, "net")
                layer = first(candidate, "layer")
                if (not net or str(net[1]) != net_name or not layer or
                        str(layer[1]) != layer_name):
                    continue
                a = point(first(candidate, "start"))
                b = point(first(candidate, "end"))
                if not ((close(a, old_a) and close(b, old_b)) or
                        (close(a, old_b) and close(b, old_a))):
                    continue
                width = str(first(candidate, "width")[1])
                board.remove(candidate)
                for p, q in zip(new_points, new_points[1:]):
                    append_item(board, segment(p, q, net_name, width,
                                               layer_name))
                return

        replace_one("RGB_L_26", "F.Cu", (13.8595, 82.0981),
                    (25.4209, 82.0981),
                    ((13.8595, 82.0981), (14.0114, 82.2500),
                     (25.2690, 82.2500), (25.4209, 82.0981)))
        replace_one("VBUS", "F.Cu", (18.8268, 79.6405),
                    (20.2547, 81.0684),
                    ((18.8268, 79.6405), (20.2547, 80.9000)))
        replace_one("VBUS", "F.Cu", (20.2547, 81.0684),
                    (24.6616, 81.0684),
                    ((20.2547, 80.9000), (24.4932, 80.9000),
                     (24.6616, 81.0684)))
        replace_one("HE_L32", "B.Cu", (18.0470, 80.3043),
                    (20.7970, 83.0543),
                    ((18.0470, 80.3043), (18.8000, 82.5000),
                     (20.7970, 83.0543)))

        ground_stitch = (20.0625, 81.5660)
        present = False
        for item in board[1:]:
            if not (isinstance(item, list) and item and
                    str(item[0]) == "via"):
                continue
            net = first(item, "net")
            if (net and str(net[1]) == "GND" and
                    close(point(first(item, "at")), ground_stitch)):
                present = True
                break
        if not present:
            append_item(board, compact_via(ground_stitch, "GND"))

    args.output.write_text(dumps(board) + "\n")
    print(f"replaced {replaced} marginal fixed-layout LED route(s)")


if __name__ == "__main__":
    main()
