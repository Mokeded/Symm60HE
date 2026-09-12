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


def prepare(path, ignored, route_only=(), protect_all=False):
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
    path.write_text(text)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dsn", type=Path)
    ap.add_argument("--ignore-net", action="append", default=[])
    ap.add_argument("--route-only", action="append", default=[])
    ap.add_argument("--protect-all-routes", action="store_true")
    args = ap.parse_args()
    if args.ignore_net and args.route_only:
        ap.error("use either --ignore-net or --route-only, not both")
    prepare(args.dsn, set(args.ignore_net), args.route_only,
            args.protect_all_routes)
    scope = (("route only: " + ", ".join(args.route_only)) if args.route_only
             else ("ignored: " + (", ".join(args.ignore_net) or "none")))
    print("prepared", args.dsn, scope,
          "(all existing routes protected)" if args.protect_all_routes else "")
