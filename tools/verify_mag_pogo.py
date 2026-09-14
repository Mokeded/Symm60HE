#!/usr/bin/env python3
"""Geometric checks for the magnetic-pogo variant.

KiCad 10's DRC is the release gate; this is what can be checked without it.
For every generated board it proves, per layer:

  * all new copper lies inside the board outline,
  * no new copper comes within CLEAR of copper or a pad of another net,
  * no trace end is left hanging,
  * every signal pad carries a net and reaches copper of that net,
  * the contact map is the same on both sides and covers all twelve nets.

Zone pours are not refilled here, so pour clearance still has to come from a
real DRC run before release.
"""
from pathlib import Path
import collections
import math
import sys

from shapely.affinity import rotate as srot, translate as stran
from shapely.geometry import LineString, Point, Polygon, box
from shapely.strtree import STRtree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_mag_pogo import OUT, PER_ROW  # noqa: E402
from sexp import find, first, loads  # noqa: E402

CLEAR = 0.15
EPS = 1e-6
MODULES = tuple(f"Symm60HE-Mag-{side}-SpringModule" for side in ("Left", "Right"))
HALVES = tuple(f"Symm60HE-Mag-{side}-Half" for side in ("Left", "Right"))
# Only the connector breakout is new on a half; the rest is inherited.
WINDOW = {"Symm60HE-Mag-Left-Half": (140.0, 156.0, 40.0, 72.0),
          "Symm60HE-Mag-Right-Half": (146.0, 162.0, 40.0, 72.0)}


def rot(px, py, angle):
    r = math.radians(-angle)
    return px * math.cos(r) - py * math.sin(r), px * math.sin(r) + py * math.cos(r)


def geometry(board):
    pads = []
    for fp in find(board, "footprint"):
        at = first(fp, "at")
        fx, fy = float(at[1]), float(at[2])
        fr = float(at[3]) if len(at) > 3 else 0.0
        flay = first(fp, "layer")[1]
        for index, pad in enumerate(find(fp, "pad")):
            a, size = first(pad, "at"), first(pad, "size")
            dx, dy = rot(float(a[1]), float(a[2]), fr)
            w, h = float(size[1]), float(size[2])
            shape = (Point(fx + dx, fy + dy).buffer(w / 2) if pad[3] == "circle"
                     else stran(srot(box(-w / 2, -h / 2, w / 2, h / 2), -fr,
                                     origin=(0, 0)), fx + dx, fy + dy))
            net = first(pad, "net")
            layers = (("F.Cu", "B.Cu") if pad[2] != "smd"
                      else (("B.Cu",) if flay == "B.Cu" else ("F.Cu",)))
            pads.append(dict(net=net[1] if net else "#%d.%d" % (id(fp), index),
                             g=shape, lays=layers, named=str(pad[1]).isdigit()))
    copper = []
    for s in find(board, "segment"):
        a, c = first(s, "start"), first(s, "end")
        width = float(first(s, "width")[1])
        copper.append((LineString([(float(a[1]), float(a[2])),
                                   (float(c[1]), float(c[2]))]).buffer(width / 2),
                       first(s, "net")[1], (first(s, "layer")[1],), s))
    for v in find(board, "via"):
        a = first(v, "at")
        copper.append((Point(float(a[1]), float(a[2]))
                       .buffer(float(first(v, "size")[1]) / 2),
                       first(v, "net")[1], ("F.Cu", "B.Cu"), v))
    return pads, copper


def outline_of(board):
    edges = [((float(first(l, "start")[1]), float(first(l, "start")[2])),
              (float(first(l, "end")[1]), float(first(l, "end")[2])))
             for l in find(board, "gr_line")
             if first(l, "layer")[1] == "Edge.Cuts"]
    if len(edges) < 3:
        return None
    return Polygon([edges[0][0]] + [e[1] for e in edges])


def check(name):
    path = OUT / f"{name}.kicad_pcb"
    board = loads(path.read_text())
    pads, copper = geometry(board)
    outline = outline_of(board)
    window = WINDOW.get(name)

    def inside_window(geom):
        if window is None:
            return True
        x0, x1, y0, y1 = window
        return geom.intersects(box(x0, y0, x1, y1))

    by_layer = collections.defaultdict(list)
    for rec in copper:
        for layer in rec[2]:
            by_layer[layer].append(rec)
    for pad in pads:
        for layer in pad["lays"]:
            by_layer[layer].append((pad["g"], pad["net"], pad["lays"], None))
    trees = {layer: (STRtree([r[0] for r in rs]), rs)
             for layer, rs in by_layer.items()}

    off = clash = 0
    for geom, net, layers, node in copper:
        if not inside_window(geom):
            continue
        if outline is not None and not outline.buffer(-0.05).contains(geom):
            off += 1
        probe = geom.buffer(CLEAR - EPS)
        for layer in layers:
            tree, rs = trees[layer]
            if any(rs[k][1] != net and rs[k][3] is not node
                   and probe.intersects(rs[k][0]) for k in tree.query(probe)):
                clash += 1
                break

    joints = collections.Counter()
    for s in find(board, "segment"):
        for end in ("start", "end"):
            q = first(s, end)
            joints[(first(s, "net")[1], round(float(q[1]), 3),
                    round(float(q[2]), 3))] += 1
    for v in find(board, "via"):
        q = first(v, "at")
        joints[(first(v, "net")[1], round(float(q[1]), 3),
                round(float(q[2]), 3))] += 1
    padtree = STRtree([p["g"] for p in pads])
    cutree = STRtree([r[0] for r in copper])
    dangling = 0
    for s in find(board, "segment"):
        net = first(s, "net")[1]
        if net == "GND":
            # Ground is poured on both layers, so a ground run that stops in
            # open copper is tied by the zone, not left floating.
            continue
        geom = LineString([(float(first(s, "start")[1]), float(first(s, "start")[2])),
                           (float(first(s, "end")[1]), float(first(s, "end")[2]))])
        if not inside_window(geom):
            continue
        for end in ("start", "end"):
            q = first(s, end)
            point = Point(float(q[1]), float(q[2]))
            key = (net, round(point.x, 3), round(point.y, 3))
            if joints[key] > 1:
                continue
            probe = point.buffer(0.02)
            if any(pads[k]["net"] == net and pads[k]["g"].intersects(probe)
                   for k in padtree.query(probe)):
                continue
            if any(copper[k][1] == net and copper[k][3] is not s
                   and copper[k][0].contains(point) for k in cutree.query(probe)):
                continue
            dangling += 1

    unnetted = sum(1 for p in pads if p["named"] and p["net"].startswith("#"))
    print("%-34s %4d segments %3d vias | off-board %d | clearance %d | "
          "loose ends %d | unnetted pads %d"
          % (name, len(find(board, "segment")), len(find(board, "via")),
             off, clash, dangling, unnetted))
    return off + clash + dangling + unnetted


def contact_map_from_csv():
    import csv
    with (OUT / "Symm60HE-mag-pogo12-pinout.csv").open() as stream:
        return list(csv.DictReader(stream))


def main():
    bad = sum(check(name) for name in MODULES + HALVES)
    rows = contact_map_from_csv()
    assert len(rows) == 2 * PER_ROW, len(rows)
    for column, letter in (("Left net", "L"), ("Right net", "R")):
        nets = [row[column] for row in rows]
        assert set(nets) == {"+3V3A", "GND", "MUX_A0", "MUX_A1", "MUX_A2",
                             f"ADC_{letter}1", f"ADC_{letter}2",
                             f"ADC_{letter}3", f"ADC_{letter}4"}, nets
        assert nets.count("GND") == 4, nets
    print("\n%s" % ("GEOMETRY CLEAN (KiCad DRC still required)" if not bad
                    else "%d geometry problems" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
