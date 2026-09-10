"""Mux channel allocation.

Positions that can never be populated together share a channel, exactly as the
FN40HE BOM does with its DNP columns.  Two positions conflict if their caps
overlap, so a channel is a set of mutually-overlapping positions.
"""
from geom import KEYS, BUILDS, U
import math

def rect(k):
    a = math.radians(k["rot"]); c, s = math.cos(a), math.sin(a)
    hw, hh = k["w"] / 2.0, 0.5
    pts = []
    for dx, dy in ((-hw,-hh),(hw,-hh),(hw,hh),(-hw,hh)):
        pts.append((k["cx"] + dx*c - dy*s, k["cy"] + dx*s + dy*c))
    return pts

from shapely.geometry import Polygon
for k in KEYS: k["poly"] = Polygon(rect(k)).buffer(-0.02)

for half in ("L", "R"):
    ks = [k for k in KEYS if k["half"] == half]
    # greedy: group positions that all mutually overlap
    groups = []
    for k in sorted(ks, key=lambda k: -k["w"]):
        for g in groups:
            if all(k["poly"].intersection(o["poly"]).area > 0.05 for o in g):
                g.append(k); break
        else:
            groups.append([k])
    print("%s half: %d positions -> %d mux channels" % (half, len(ks), len(groups)))
    for g in groups:
        if len(g) > 1:
            print("     shared: %s" % " / ".join("%s %gu" % ("|".join(sorted(x["labels"])), x["w"]) for x in g))
    # per-build simultaneous count
    for b in BUILDS:
        n = sum(1 for k in ks if b in k["builds"])
        print("     %-16s %d keys" % (b.replace("doe-", ""), n))
