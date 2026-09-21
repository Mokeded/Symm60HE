#!/usr/bin/env python3
"""Prepare a KiCad Specctra export for deterministic headless routing.

KiCad exports every net in one class.  The half boards already connect GND and
+3V3A with pours and explicit taps, so asking an autorouter to build redundant
spanning trees wastes the switch-field corridors.  This tool moves selected
nets to a dedicated class that Freerouting can skip with ``-inc plane_power``.
It also keeps the exported trace width consistent with this project's 0.20 mm
Default netclass.
"""
import argparse
import re
from pathlib import Path


def matching_paren(text, start):
    depth = 0
    quoted = False
    escaped = False
    for i in range(start, len(text)):
        c = text[i]
        if quoted:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                quoted = False
            continue
        if c == '"':
            quoted = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
    raise ValueError("unterminated class expression")


def remove_network_net(text, net):
    """Remove one unrouted net from the Specctra network section.

    Freerouting 2.4 no longer provides the older command-line net-class
    exclusion switch.  Merely moving a plane net into another class therefore
    still asks the autorouter to build a spanning tree for it.  Removing the
    net from the interchange file reserves that connectivity for KiCad's
    copper-zone fill; it does not alter the source KiCad board or its netlist.
    """
    search_from = text.index("(network")
    match = re.search(r"\(net\s+" + re.escape(net) + r"(?=\s|\))",
                      text[search_from:])
    if match is None:
        raise ValueError("network net not present: " + net)
    start = search_from + match.start()
    end = matching_paren(text, start)
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end < 0:
        line_end = end
    else:
        line_end += 1
    return text[:line_start] + text[line_end:]


def prepare(path, ignored, route_only=(), protect_all=False, omit=(),
            clearance_um=None, width_um=None, omit_non_target=False):
    text = path.read_text()
    start = text.index("(class kicad_default")
    end = matching_paren(text, start)
    block = text[start:end]
    circuit = block.index("(circuit")
    header = block[len("(class kicad_default"):circuit]
    nets = header.split()
    route_only = set(route_only)
    missing_targets = route_only.difference(nets)
    if missing_targets:
        raise ValueError("route-only nets not present in default class: " +
                         ", ".join(sorted(missing_targets)))
    if route_only:
        ignored = set(nets).difference(route_only)
    missing = ignored.difference(nets)
    if missing:
        raise ValueError("ignored nets not present in default class: " + ", ".join(sorted(missing)))
    kept = [net for net in nets if net not in ignored]
    via_start = block.index('(use_via "') + len('(use_via "')
    via_end = block.index('"', via_start)
    via_name = block[via_start:via_end]
    default = "(class kicad_default " + " ".join(kept) + "\n      " + block[circuit:]
    plane = ("\n    (class plane_power " + " ".join(sorted(ignored)) +
             "\n      (circuit (use_via \"" + via_name + "\"))"+
             "\n      (rule (width 200) (clearance 200))\n    )")
    text = text[:start] + default + plane + text[end:]
    for net in ignored:
        # Keep the generator's checked plane taps and stitching fixed.  If they
        # remain ordinary routes, the autorouter may rip them up while solving
        # a signal and leave a pad disconnected from its plane.
        text = text.replace("(net %s)(type route)" % net,
                            "(net %s)(type protect)" % net)
    if protect_all:
        # A repair pass starts from a complete signal route.  Freeze every
        # existing trace and via so the router may only add copper for the
        # selected open power nets; this makes the pass non-destructive.
        text = text.replace("(type route)", "(type protect)")
    omitted = set(omit)
    if omit_non_target:
        if not route_only:
            raise ValueError("--omit-non-target requires --route-only")
        omitted.update(ignored)
    for net in omitted:
        text = remove_network_net(text, net)
    if clearance_um is not None:
        # Preserve KiCad's special fine-pitch SMD-to-SMD allowance while
        # changing the ordinary track/pad and board-cutout clearance.  KiCad
        # exports either the board minimum (150 um here) or a netclass/local
        # override (200 um), so handle both instead of silently leaving the
        # latter unchanged.
        for exported_um in (150, 200):
            text = text.replace("(clearance %d)" % exported_um,
                                "(clearance %d)" % clearance_um)
    if width_um is not None:
        # KiCad repeats the default width in structure and class rules.  The
        # fine-pitch symmetric layout can use the board's documented 0.15 mm
        # minimum when the normal 0.20 mm route cannot clear the switch field.
        text = text.replace("(width 200)", "(width %d)" % width_um)
    path.write_text(text)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dsn", type=Path)
    ap.add_argument("--ignore-net", action="append", default=[])
    ap.add_argument("--route-only", action="append", default=[])
    ap.add_argument("--protect-all-routes", action="store_true")
    ap.add_argument("--omit-net", action="append", default=[],
                    help="omit an unrouted plane net from the DSN network")
    ap.add_argument("--clearance-um", type=int,
                    help="ordinary routing clearance in DSN resolution units")
    ap.add_argument("--width-um", type=int,
                    help="routing width in DSN resolution units")
    ap.add_argument("--omit-non-target", action="store_true",
                    help="with --route-only, omit all other network blocks")
    args = ap.parse_args()
    if args.ignore_net and args.route_only:
        ap.error("use either --ignore-net or --route-only, not both")
    prepare(args.dsn, set(args.ignore_net), args.route_only,
            args.protect_all_routes, args.omit_net, args.clearance_um,
            args.width_um,
            args.omit_non_target)
    scope = (("route only: " + ", ".join(args.route_only)) if args.route_only
             else ("ignored: " + (", ".join(args.ignore_net) or "none")))
    print("prepared", args.dsn, scope,
          "(all existing routes protected)" if args.protect_all_routes else "")
