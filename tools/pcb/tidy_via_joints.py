#!/usr/bin/env python3
"""Merge same-net vias that land on each other and pull track ends onto centres.

Grid retries and repeated repair passes can leave two vias of one net a few
microns -- or a couple of tenths -- apart, and track ends that stop just short
of the via they are meant to land on.  KiCad reports those as co-located or
too-close drills and as endpoints not centred on a via.  Both are bookkeeping
faults rather than routing mistakes, so they are fixed in place: the later via
is dropped, every track end that referenced it is moved to the survivor, and
any end within `--snap` of a same-net via centre is snapped onto it.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import re
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sexp import Sym, dumps, find, first, loads


# An endpoint KiCad calls off-centre has to be moved onto the via; a joint it
# calls too narrow is already touching, and moving that segment would swing it
# across its neighbours, so it is met with a stub instead.
FLAGGED = {"track_not_centered_on_via": "move", "connection_width": "stub"}
ITEM = re.compile(r"@\(([-0-9.]+) mm, ([-0-9.]+) mm\): Via \[([^]]+)\]")


def flagged_vias(report):
    """Via positions KiCad named in a joint complaint: (x, y, net, how)."""
    lines = Path(report).read_text().splitlines()
    out = []
    for index, line in enumerate(lines):
        how = next((action for name, action in FLAGGED.items()
                    if line.startswith(f"[{name}]")), None)
        if how is None:
            continue
        for item_line in lines[index + 1:index + 5]:
            match = ITEM.search(item_line)
            if match:
                x, y, net = match.groups()
                out.append((float(x), float(y), net, how))
    return out


def point_of(item, name):
    node = first(item, name)
    return (float(node[1]), float(node[2]))


def set_point(item, name, point):
    node = first(item, name)
    node[1:3] = [Sym(f"{point[0]:.6f}"), Sym(f"{point[1]:.6f}")]


def net_of(item):
    net = first(item, "net")
    return str(net[1]) if net and len(net) > 1 else ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("board")
    parser.add_argument("output")
    parser.add_argument("--merge", type=float, default=0.55,
                        help="merge same-net vias closer than this (mm); the "
                             "default keeps 0.30 mm drills outside the "
                             "0.25 mm hole-to-hole rule")
    parser.add_argument("--report",
                        help="a DRC report; joints it names are also pulled "
                             "together, however far apart they are")
    parser.add_argument("--report-snap", type=float, default=0.6,
                        help="how far a flagged joint may be pulled (mm)")
    parser.add_argument("--snap", type=float, default=0.15,
                        help="snap track ends within this of a via centre "
                             "(mm); the default is the drill radius, so an end "
                             "that clearly terminates on the via is centred "
                             "while copper merely passing by is left alone")
    args = parser.parse_args()

    board = loads(Path(args.board).read_text())
    vias = [item for item in board[1:]
            if isinstance(item, list) and item and str(item[0]) == "via"]
    tracks = [item for item in board[1:]
              if isinstance(item, list) and item and str(item[0]) == "segment"]

    dropped = set()
    moves = []
    for index, via in enumerate(vias):
        if id(via) in dropped:
            continue
        for other in vias[index + 1:]:
            if id(other) in dropped or net_of(other) != net_of(via):
                continue
            if math.dist(point_of(via, "at"), point_of(other, "at")) < args.merge:
                dropped.add(id(other))
                moves.append((point_of(other, "at"), point_of(via, "at"),
                              net_of(via)))

    for track in tracks:
        for source, target, net in moves:
            if net_of(track) != net:
                continue
            for name in ("start", "end"):
                if math.dist(point_of(track, name), source) < 0.005:
                    set_point(track, name, target)

    snapped = 0
    live = [via for via in vias if id(via) not in dropped]
    for track in tracks:
        for via in live:
            if net_of(via) != net_of(track):
                continue
            centre = point_of(via, "at")
            for name in ("start", "end"):
                distance = math.dist(point_of(track, name), centre)
                if 0 < distance < args.snap:
                    set_point(track, name, centre)
                    snapped += 1

    extended = []
    if args.report:
        # A track that stops just outside its via still counts as connected,
        # but the sliver of overlap is narrower than the copper either side of
        # it.  Reach the centre with a short stub rather than by moving the
        # track: swinging a whole segment across its neighbours is how a fixed
        # joint turns into a clearance error somewhere else.
        for x, y, net, how in flagged_vias(args.report):
            via = min((item for item in live if net_of(item) == net),
                      key=lambda item: math.dist(point_of(item, "at"), (x, y)),
                      default=None)
            if via is None or math.dist(point_of(via, "at"), (x, y)) > 0.05:
                continue
            centre = point_of(via, "at")
            best = None
            for track in tracks:
                if net_of(track) != net:
                    continue
                for name in ("start", "end"):
                    distance = math.dist(point_of(track, name), centre)
                    if 0 < distance < args.report_snap:
                        if best is None or distance < best[0]:
                            best = (distance, track, name)
            if best is None:
                continue
            _, track, name = best
            if how == "move":
                set_point(track, name, centre)
                snapped += 1
                continue
            end = point_of(track, name)
            stub = [Sym("segment"),
                    [Sym("start"), Sym(f"{end[0]:.6f}"), Sym(f"{end[1]:.6f}")],
                    [Sym("end"), Sym(f"{centre[0]:.6f}"),
                     Sym(f"{centre[1]:.6f}")],
                    first(track, "width"),
                    first(track, "layer"),
                    first(track, "net"),
                    [Sym("uuid"), str(uuid.uuid4())]]
            extended.append(stub)
            snapped += 1

    kept = [item for item in board[1:]
            if not (isinstance(item, list) and id(item) in dropped)]
    kept = [item for item in kept
            if not (isinstance(item, list) and item and
                    str(item[0]) == "segment" and
                    point_of(item, "start") == point_of(item, "end"))]
    # New copper goes before the file's last element, the way every other
    # tool here emits it; appended after it, KiCad does not pick it up.
    if extended:
        kept = kept[:-1] + extended + kept[-1:]
    Path(args.output).write_text(dumps([Sym("kicad_pcb")] + kept) + "\n")
    print(f"merged {len(dropped)} duplicate vias; snapped {snapped} track "
          f"end(s), {len(extended)} of them reached with a stub")


if __name__ == "__main__":
    main()
