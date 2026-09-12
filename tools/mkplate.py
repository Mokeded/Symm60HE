"""Generate independent left/right plates with Neo-style side gasket tabs.

Every layout gets two plate files.  The outer contours stay identical so all
variants fit the same tented case; only the switch/stabilizer openings differ.
The universal pair merges mutually exclusive switch openings into durable
slots.  The controller daughterboard mounts independently to the case.
"""
import ezdxf
from shapely.geometry import box
from shapely.ops import unary_union
from shapely.affinity import rotate, translate

from geom import KEYS, U, BUILDS
from outline import (LEFT_PLATE, RIGHT_PLATE, LEFT_GASKET_TABS,
                     RIGHT_GASKET_TABS)

SW_CUT = 14.0
STEPPED_CAPS_OFFSET = 19.05 / 4.0
STAB_X, STAB_CUT = 11.90625, (7.0, 15.6, 0.635)
PLATES = {"L": LEFT_PLATE, "R": RIGHT_PLATE}
TABS = {"L": LEFT_GASKET_TABS, "R": RIGHT_GASKET_TABS}

def placed(k, shape):
    return translate(rotate(shape, k["rot"], origin=(0, 0)),
                     k["cx"] * U, k["cy"] * U)

def cutouts(keys):
    cuts, stabs = [], []
    for k in keys:
        cuts.append(placed(k, box(-SW_CUT/2, -SW_CUT/2,
                                  SW_CUT/2, SW_CUT/2)))
        if k["w"] >= 2.0:
            w, h, dy = STAB_CUT
            for sx in (-STAB_X, STAB_X):
                stabs.append(placed(k, box(sx-w/2, dy-h/2,
                                           sx+w/2, dy+h/2)))
    return cuts, stabs

def stepped_caps_cutout(keys):
    """Return the alternate MX opening for a traditional stepped 1.75u cap."""
    caps = [k for k in keys if k["half"] == "L" and k["label"] == "Caps Lock"]
    if not caps:
        return []
    cap = dict(caps[0])
    # The cap envelope is unchanged; the stepped key's stem is 0.25u left.
    cap["cx"] -= 0.25
    return [placed(cap, box(-SW_CUT/2, -SW_CUT/2, SW_CUT/2, SW_CUT/2))]

def polygons(g):
    return list(g.geoms) if hasattr(g, "geoms") else [g]

def put(msp, poly, layer):
    msp.add_lwpolyline(list(poly.exterior.coords), close=True,
                       dxfattribs={"layer": layer})
    for ring in poly.interiors:
        msp.add_lwpolyline(list(ring.coords), close=True,
                           dxfattribs={"layer": layer})

def write(name, half, cuts, stabs, merge=False):
    plate = PLATES[half]
    doc = ezdxf.new("R2010"); doc.units = ezdxf.units.MM
    msp = doc.modelspace()
    for layer, color in (("PLATE_OUTLINE", 7), ("SWITCH_CUTOUTS", 3),
                         ("STAB_CLEARANCE", 1)):
        doc.layers.add(layer, color=color)
    for p in polygons(plate): put(msp, p, "PLATE_OUTLINE")
    openings = (polygons(unary_union(cuts).buffer(0.6).buffer(-0.6))
                if merge else cuts)
    for p in openings: put(msp, p, "SWITCH_CUTOUTS")
    if stabs:
        for p in polygons(unary_union(stabs)): put(msp, p, "STAB_CLEARANCE")
    doc.saveas("../plate/%s-%s.dxf" %
               (name, "left" if half == "L" else "right"))
    return openings

def check(name, half, cuts):
    plate = PLATES[half]
    bad = sum(1 for c in cuts if not plate.contains(c))
    web = min(plate.exterior.distance(c) for c in cuts)
    print("%-30s %2s | %3d openings | outside %d | edge web %.2f mm" %
          (name, half, len(cuts), bad, web))

def write_gaskets():
    """One discrete Poron pad per Neo-style plate-side suspension tab."""
    doc = ezdxf.new("R2010"); doc.units = ezdxf.units.MM
    msp = doc.modelspace(); doc.layers.add("GASKET_PADS", color=1)
    count = 0
    for tabs in (TABS["L"], TABS["R"]):
        for tab in tabs:
            put(msp, tab.buffer(-0.55, join_style=2), "GASKET_PADS")
            count += 1
    doc.saveas("../plate/Symm60HE-gasket-pads.dxf")
    print("gaskets                       %d discrete Neo-style side Poron pads" % count)

for build in BUILDS:
    stem = "Symm60HE-plate-" + build.replace("doe-", "")
    for half in ("L", "R"):
        keys = [k for k in KEYS if k["half"] == half and build in k["builds"]]
        cuts, stabs = cutouts(keys)
        if half == "L":
            cuts += stepped_caps_cutout(keys)
        out = write(stem, half, cuts, stabs)
        check(stem, half, out)

for half in ("L", "R"):
    keys = [k for k in KEYS if k["half"] == half]
    cuts, stabs = cutouts(keys)
    if half == "L":
        cuts += stepped_caps_cutout(keys)
    out = write("Symm60HE-plate-universal", half, cuts, stabs, merge=True)
    check("universal", half, out)

write_gaskets()
