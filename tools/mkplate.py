"""Generate symmetric independent left/right plates for every layout.

Every layout gets two plate files with one exactly mirrored exterior derived
from the routed PCB outline.  The top, bottom, and stepped centre contours
follow the PCB, while the straight side rails remain dedicated gasket walls.
Only the switch/stabilizer openings differ between layout variants.
The universal pair merges mutually exclusive switch openings into durable
slots.  The controller daughterboard mounts independently to the case.
"""
import ezdxf
from shapely.geometry import box, Point
from shapely.ops import unary_union
from shapely.affinity import rotate, translate

from geom import KEYS, U, AXIS
from layouts.make_layout_pcbs import LAYOUTS, source_layout
from mechanics import PLATE_STANDOFFS
from outline import (finished_plate_outline, gasket_tabs,
                     keycap_bounded_plate, keycap_core_plate,
                     keycap_plate_envelope)

SW_CUT = 14.0
STEPPED_CAPS_OFFSET = 19.05 / 4.0
STAB_X, STAB_CUT = 11.90625, (7.0, 15.6, 0.635)
# Four matching PCB/plate M2 mounts per half. The halves use independently
# optimized patterns because mirrored points collide with the asymmetric FPC
# and mux placement. Use non-magnetic nylon spacers no larger than 4.0 mm OD.
PLATE_STANDOFF_DIAMETER = 2.2
STANDOFF_BODY_RADIUS = 2.0
STANDOFF_OPENING_CLEARANCE = 1.75
STANDOFF_EDGE_CLEARANCE = 2.0
MOUNT_OPENING_CLEARANCE = 2.0
POM_MIN_WEB = 2.0

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
            # SL2/SR3 are rotated 180 degrees on the PCB so their larger
            # retention holes face the board interior.  Rotate the matching
            # plate clearances with the stabilizer bodies; the symmetric
            # +/-STAB_X stem spacing remains centred on the key switch.
            stab_key = k
            if k["label"] == "Space":
                stab_key = dict(k, rot=k["rot"] + 180.0)
            for sx in (-STAB_X, STAB_X):
                stabs.append(placed(stab_key, box(sx-w/2, dy-h/2,
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


def standoff_holes(half):
    radius = PLATE_STANDOFF_DIAMETER / 2.0
    return [Point(x, y).buffer(radius, quad_segs=32)
            for x, y in PLATE_STANDOFFS[half]]


def put(msp, poly, layer):
    msp.add_lwpolyline(list(poly.exterior.coords), close=True,
                       dxfattribs={"layer": layer})
    for ring in poly.interiors:
        msp.add_lwpolyline(list(ring.coords), close=True,
                           dxfattribs={"layer": layer})

def write(name, half, plate, cuts, stabs, mounts, merge=False):
    doc = ezdxf.new("R2010"); doc.units = ezdxf.units.MM
    msp = doc.modelspace()
    for layer, color in (("PLATE_OUTLINE", 7), ("SWITCH_CUTOUTS", 3),
                         ("STAB_CLEARANCE", 1),
                         ("STANDOFF_HOLES", 5)):
        doc.layers.add(layer, color=color)
    for p in polygons(plate): put(msp, p, "PLATE_OUTLINE")
    openings = (polygons(unary_union(cuts).buffer(0.6).buffer(-0.6))
                if merge else cuts)
    for p in openings: put(msp, p, "SWITCH_CUTOUTS")
    if stabs:
        for p in polygons(unary_union(stabs)): put(msp, p, "STAB_CLEARANCE")
    for mount in mounts:
        put(msp, mount, "STANDOFF_HOLES")
    doc.saveas("../plate/%s-%s.dxf" %
               (name, "left" if half == "L" else "right"))
    return openings

def check(name, half, plate, plate_body, gasket_mounts, keys, cuts, stabs,
          mounts):
    cap_hull = keycap_plate_envelope(keys)
    # The legacy keycap core remains bounded even though the finished body now
    # deliberately follows the routed PCB profile plus straight gasket rails.
    outside = keycap_core_plate(keys).difference(cap_hull).area
    all_openings = cuts + stabs + mounts
    bad = sum(1 for opening in all_openings
              if not plate.buffer(1e-6).contains(opening))
    web = min(plate.exterior.distance(opening) for opening in cuts + stabs)
    obstacle = unary_union(cuts + stabs)
    mount_clearance = min(obstacle.distance(mount) for mount in mounts)
    mount_body_clearance = min(
        obstacle.distance(Point(x, y).buffer(STANDOFF_BODY_RADIUS))
        for (x, y) in PLATE_STANDOFFS[half])
    mount_edge_clearance = min(
        plate.exterior.distance(Point(x, y).buffer(STANDOFF_BODY_RADIUS))
        for (x, y) in PLATE_STANDOFFS[half])
    material = plate.difference(unary_union(all_openings))
    one_piece = material.geom_type == "Polygon" and material.is_valid
    gasket_good = (
        len(gasket_mounts) == 4 and
        all(tab.intersects(plate_body) for tab in gasket_mounts) and
        plate.symmetric_difference(finished_plate_outline(half)).area < 0.01)
    if (outside > 0.01 or bad or web < POM_MIN_WEB or
            len(mounts) != 4 or not gasket_good or
            mount_clearance < MOUNT_OPENING_CLEARANCE or
            mount_body_clearance < STANDOFF_OPENING_CLEARANCE or
            mount_edge_clearance < STANDOFF_EDGE_CLEARANCE or not one_piece):
        raise RuntimeError(
            f"{name} {half}: outside keycaps={outside}, bad openings={bad}, "
            f"minimum web={web}, mount clearance={mount_clearance}, "
            f"gasket mounts={gasket_good}, one piece={one_piece}")
    print("%-38s %2s | %3d openings | PCB-following exterior | "
          "minimum web %.2f mm | 4 M2 mounts | solid pre-flex-cut structure" %
          (name, half, len(cuts), web))

def write_gaskets(name, mounts_by_half, legacy=False):
    """One Poron pad per integral plate-side suspension mount."""
    doc = ezdxf.new("R2010"); doc.units = ezdxf.units.MM
    msp = doc.modelspace(); doc.layers.add("GASKET_PADS", color=1)
    count = 0
    for tabs in (mounts_by_half["L"], mounts_by_half["R"]):
        for tab in tabs:
            put(msp, tab.buffer(-0.55, join_style=2), "GASKET_PADS")
            count += 1
    path = "../plate/Symm60HE-gasket-pads-%s.dxf" % name
    doc.saveas(path)
    if legacy:
        doc.saveas("../plate/Symm60HE-gasket-pads.dxf")
    print("%-38s %d integral-mount Poron pads" % ("gaskets-" + name, count))

def main():
    for layout in LAYOUTS:
        stem = "Symm60HE-plate-" + layout
        layout_gaskets = {}
        for half in ("L", "R"):
            build = "doe-" + source_layout(
                layout, "Left" if half == "L" else "Right")
            keys = [k for k in KEYS
                    if k["half"] == half and build in k["builds"]]
            plate_body = keycap_bounded_plate(keys)
            gasket_mounts = gasket_tabs(plate_body, half)
            plate = finished_plate_outline(half)
            cuts, stabs = cutouts(keys)
            if half == "L":
                cuts += stepped_caps_cutout(keys)
            mounts = standoff_holes(half)
            out = write(stem, half, plate, cuts, stabs, mounts)
            check(stem, half, plate, plate_body, gasket_mounts, keys, out,
                  stabs, mounts)
            layout_gaskets[half] = gasket_mounts
        write_gaskets(layout, layout_gaskets)

    universal_gaskets = {}
    for half in ("L", "R"):
        keys = [k for k in KEYS if k["half"] == half]
        plate_body = keycap_bounded_plate(keys)
        gasket_mounts = gasket_tabs(plate_body, half)
        plate = finished_plate_outline(half)
        cuts, stabs = cutouts(keys)
        if half == "L":
            cuts += stepped_caps_cutout(keys)
        mounts = standoff_holes(half)
        out = write("Symm60HE-plate-universal", half, plate, cuts, stabs,
                    mounts, merge=True)
        check("universal", half, plate, plate_body, gasket_mounts, keys, out,
              stabs, mounts)
        universal_gaskets[half] = gasket_mounts

    write_gaskets("universal", universal_gaskets, legacy=True)


if __name__ == "__main__":
    main()
