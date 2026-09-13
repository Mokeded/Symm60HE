"""Board and plate outlines, in millimetres, KiCad orientation (y down)."""
import math, json
from shapely.geometry import Polygon, box, MultiPolygon, LineString
from shapely.affinity import scale, translate
from shapely.ops import unary_union
from geom import KEYS, U, AXIS

WALL      = 6.0     # room for the gasket ledge and M2 frame fasteners
BEZEL     = 0.46 * U   # key field -> case inner edge, as the renders use
PCB_GAP   = 2.0     # clearance between the two half PCBs
PCB_INSET = 1.2     # PCB edge inside the case inner wall
PLATE_OVERHANG = 2.0  # nominal plate rim before discrete Neo-style tabs
# Neo-Ergo-inspired side suspension, adapted to this split plate rather than
# copied onto the Hall PCB.  Each station has a long, straight 20 x 4 mm Poron
# bearing area and a 2 mm smooth shoulder at either end.  This makes two pads
# fit end-to-end in one 80 x 4 mm strip.  The tongue projects 4 mm from the
# continuous plate wall; opposing centre tongues retain 0.5 mm clearance when
# each complete moving half is spread 2.75 mm from the original datum.
NEO_GASKET_LENGTH = 24.0
NEO_GASKET_BEARING = 20.0
NEO_GASKET_PROJECTION = 4.0
GASKET_ROOT_INSET = 0.6
HALF_SPREAD = 2.75


def half_spread(half):
    return -HALF_SPREAD if half in ("L", "left") else HALF_SPREAD

def cap(k, grow=0.0):
    # DOE60 reference direction: the left rows descend toward the centre and
    # the right rows rise away from it; the upper ends of the inner columns
    # therefore lean toward the centre.  Positive Shapely rotation is clockwise
    # on KiCad's y-down board coordinates, matching the stored plate angle.
    a = math.radians(k["rot"]); c, s = math.cos(a), math.sin(a)
    hw, hh = k["w"] / 2.0 + grow, 0.5 + grow
    return Polygon([(k["cx"] + dx*c - dy*s, k["cy"] + dx*s + dy*c)
                    for dx, dy in ((-hw,-hh),(hw,-hh),(hw,hh),(-hw,hh))])

field = unary_union([cap(k) for k in KEYS])          # in u
hull  = field.convex_hull

# Square off the top and sides the way the case drawing does, leaving the swept
# front to follow the hull.
b = hull.bounds
xs = list(hull.exterior.coords)
yl = max(y for x, y in xs if x < b[0] + 0.08)
yr = max(y for x, y in xs if x > b[2] - 0.08)
case_in = hull.union(box(b[0], b[1], b[2], min(yl, yr))).buffer(0.06).buffer(-0.06)
case_in = case_in.buffer(BEZEL / U)                   # case inner face
case_out = case_in.buffer(WALL / U)                   # case outer face

def to_mm(poly):
    return Polygon([(x * U, y * U) for x, y in poly.exterior.coords])

CASE_IN  = to_mm(case_in)
CASE_OUT = to_mm(case_out)
PLATE_OUT = CASE_IN.buffer(PLATE_OVERHANG)
axis_mm  = AXIS * U

def key_cell_mm(k):
    """Actual key-cell rectangle, including non-1u cap width and rotation."""
    a = math.radians(k["rot"]); c, s = math.cos(a), math.sin(a)
    hw, hh = max(k["w"] * U, U) / 2.0, U / 2.0
    x, y = k["cx"] * U, k["cy"] * U
    return Polygon([(x + dx*c - dy*s, y + dx*s + dy*c)
                    for dx, dy in ((-hw,-hh),(hw,-hh),(hw,hh),(-hw,hh))])

def keymap_plate(half):
    """Split plate body that follows the union of the keys on one half."""
    body = unary_union([key_cell_mm(k) for k in KEYS if k["half"] == half])
    body = body.buffer(3.0, join_style=2).buffer(0.05, join_style=2).buffer(-0.05, join_style=2)
    return max(body.geoms, key=lambda p: p.area) if isinstance(body, MultiPolygon) else body

def edge_y(poly, x, top=True):
    hit = poly.intersection(LineString([(x, -1e4), (x, 1e4)]))
    ys = []
    for g in (hit.geoms if hasattr(hit, "geoms") else (hit,)):
        ys.extend(p[1] for p in getattr(g, "coords", ()))
    return min(ys) if top else max(ys)

def edge_x(poly, y, left=True):
    """Return the extreme plate X coordinate intersected by a horizontal ray."""
    hit = poly.intersection(LineString([(-1e4, y), (1e4, y)]))
    xs = []
    for geometry in (hit.geoms if hasattr(hit, "geoms") else (hit,)):
        xs.extend(point[0] for point in getattr(geometry, "coords", ()))
    if not xs:
        raise RuntimeError("gasket station does not intersect the plate")
    return min(xs) if left else max(xs)


def smooth_side_tab(x, y, left=True, dx_dy=0.0,
                    projection=NEO_GASKET_PROJECTION,
                    root_inset=GASKET_ROOT_INSET,
                    length=NEO_GASKET_LENGTH,
                    bearing=NEO_GASKET_BEARING):
    """Create a side tongue with curved, tapered roots.

    The two cubic shoulders leave a continuous vertical plate edge tangentially,
    ease out to the 4.0 mm projection, and meet the straight support face
    tangentially.  The complete tongue is 24.0 mm long, with a 20.0 mm bearing
    face sized for the user's 4 mm-wide Neo-style Poron strips.
    """
    direction = -1.0 if left else 1.0
    # Follow the local plate-edge tangent. This matters on the sloped centre
    # edges: a vertical-root tongue there leaves triangular slivers after the
    # boolean union even though the tongue itself is curved.
    tangent_length = math.hypot(dx_dy, 1.0)
    tangent = (dx_dy / tangent_length, 1.0 / tangent_length)
    normal = (tangent[1] * direction, -tangent[0] * direction)

    def local(u, v):
        return (x + normal[0] * u + tangent[0] * v,
                y + normal[1] * u + tangent[1] * v)

    def bezier(p0, p1, p2, p3, count=16):
        points = []
        for index in range(count + 1):
            t = index / count
            u = 1.0 - t
            points.append((
                u**3 * p0[0] + 3 * u*u*t * p1[0] +
                3 * u*t*t * p2[0] + t**3 * p3[0],
                u**3 * p0[1] + 3 * u*u*t * p1[1] +
                3 * u*t*t * p2[1] + t**3 * p3[1],
            ))
        return points

    # Sink the root into the plate so tangent approximation and floating-point
    # tolerances cannot leave a detached island.  The 2 mm end transitions are
    # deliberately broad enough to avoid the jagged rectangular shoulders of
    # the earlier plate previews.
    root_half = length / 2.0
    bearing_half = bearing / 2.0
    transition = root_half - bearing_half
    top = bezier(local(-root_inset, -root_half),
                 local(-root_inset, -root_half + transition / 2.0),
                 local(projection, -bearing_half - transition / 2.0),
                 local(projection, -bearing_half))
    bottom = bezier(local(projection, bearing_half),
                    local(projection, bearing_half + transition / 2.0),
                    local(-root_inset, root_half - transition / 2.0),
                    local(-root_inset, root_half))
    return Polygon(top + [local(projection, bearing_half)] + bottom +
                   [local(-root_inset, -root_half)])


def gasket_tabs(poly, half):
    """Side suspension: two outer and two centre-side tabs per half.

    Across the assembled keyboard this produces eight locations: four
    outer/corner pads and four pads beside the centre kernel.  The
    tabs are integral to the plate only.  No gasket feature or clamp is added
    to either Hall-effect PCB, so gasket compression cannot bend the sensor
    board directly.
    """
    _, y0, _, y1 = poly.bounds
    outer_left = half == "L"
    inner_left = not outer_left
    tabs = []
    # Keep the full Neo-style tongue on uninterrupted vertical portions of the
    # sculpted keymap edge.  Placing a tongue across a row-to-row outline step
    # makes the union look jagged even when the tongue itself is rounded.
    for fraction in (0.27, 0.66):
        y = y0 + (y1 - y0) * fraction
        x = edge_x(poly, y, left=outer_left)
        tabs.append(smooth_side_tab(x, y, left=outer_left))
    # The upper station sits on the centre's long vertical section; the lower
    # one sits on its uninterrupted diagonal. Match that diagonal rather than
    # forcing a vertical tongue root across it.
    for fraction in (0.32, 0.68):
        y = y0 + (y1 - y0) * fraction
        x = edge_x(poly, y, left=inner_left)
        sample = 2.0
        slope = ((edge_x(poly, y + sample, left=inner_left) -
                  edge_x(poly, y - sample, left=inner_left)) / (2.0 * sample))
        # The two complete moving halves are spread symmetrically below.  This
        # lets the centre tongues use the same 4.0 mm projection and 0.6 mm
        # root inset as the outer tongues while retaining a 0.5 mm split.
        tabs.append(smooth_side_tab(x, y, left=inner_left, dx_dy=slope))
    return tabs

LEFT_KEYMAP_PROFILE = keymap_plate("L")
RIGHT_KEYMAP_PROFILE = keymap_plate("R")
# A real hinge gap is required: buffered rotated key cells otherwise overlap by
# a fraction of a millimetre at the inner tips and make two DXFs that cannot
# occupy opposing tent planes.
LEFT_KEYMAP_PROFILE = LEFT_KEYMAP_PROFILE.intersection(
    box(-1e4, -1e4, axis_mm - 1.5, 1e4))
RIGHT_KEYMAP_PROFILE = RIGHT_KEYMAP_PROFILE.intersection(
    box(axis_mm + 1.5, -1e4, 1e4, 1e4))
# Fill only the marked bottom-row U recess.  Every other step and slope remains
# keymap-following; the unfilled profile is retained for the cosmetic top lip.
LEFT_BLOCKER_FILL = Polygon([(59.1980, 98.2500), (59.1980, 79.2016),
                             (67.9842, 79.2062), (67.3962, 98.1466)]).buffer(
                                 0.02, join_style=2)
RIGHT_BLOCKER_FILL = Polygon([(232.6408, 98.1456), (232.0529, 79.2062),
                              (240.8395, 79.2016), (240.8395, 98.2500)]).buffer(
                                  0.02, join_style=2)
# Move the entire plate source for each half, not merely the gasket tongues.
# Switch openings and all other moving-half members receive this same datum in
# their generators so their local alignment is unchanged.
LEFT_KEYMAP_PROFILE = translate(
    LEFT_KEYMAP_PROFILE, xoff=half_spread("L"))
RIGHT_KEYMAP_PROFILE = translate(
    RIGHT_KEYMAP_PROFILE, xoff=half_spread("R"))
LEFT_BLOCKER_FILL = translate(LEFT_BLOCKER_FILL, xoff=half_spread("L"))
RIGHT_BLOCKER_FILL = translate(RIGHT_BLOCKER_FILL, xoff=half_spread("R"))
LEFT_PLATE_BODY = unary_union([LEFT_KEYMAP_PROFILE, LEFT_BLOCKER_FILL])
RIGHT_PLATE_BODY = unary_union([RIGHT_KEYMAP_PROFILE, RIGHT_BLOCKER_FILL])


def flatten_plate_side_wall(poly, side):
    """Fill side steps without creating square end caps at top or bottom.

    The wall runs only between the real plate intersections 10 mm inboard of
    that side.  Using the polygon's complete Y bounds here created the former
    rectangular feet beyond the sloped bottom contour.
    """
    x0, y0, x1, y1 = poly.bounds
    if side == "left":
        inner_x = x0 + 10.0
        wall = box(x0, edge_y(poly, inner_x, top=True),
                   inner_x, edge_y(poly, inner_x, top=False))
    else:
        inner_x = x1 - 10.0
        wall = box(inner_x, edge_y(poly, inner_x, top=True),
                   x1, edge_y(poly, inner_x, top=False))
    merged = unary_union([poly, wall])
    # The fill can enclose a narrow remnant of the old stepped boundary.  A
    # plate body has no intentional holes at this stage (switch openings are
    # emitted separately), so discard those obsolete interior rings.
    if isinstance(merged, Polygon):
        return Polygon(merged.exterior)
    return unary_union([Polygon(part.exterior) for part in merged.geoms])


# Unlike the PCB, the plate does not need to trace every shifted key-cell edge.
# Straight outside walls give both outer gasket tongues one clean datum and
# eliminate the stacked rectangular shelves visible in earlier previews.
# Both outside and centre-facing sides use one continuous wall.  The inner
# tongues therefore become the outermost material at the tent gap instead of
# emerging from a staircase of key-cell offsets.
LEFT_PLATE_BODY = flatten_plate_side_wall(LEFT_PLATE_BODY, "left")
LEFT_PLATE_BODY = flatten_plate_side_wall(LEFT_PLATE_BODY, "right")
RIGHT_PLATE_BODY = flatten_plate_side_wall(RIGHT_PLATE_BODY, "right")
RIGHT_PLATE_BODY = flatten_plate_side_wall(RIGHT_PLATE_BODY, "left")
LEFT_TOP_PROFILE = LEFT_KEYMAP_PROFILE
RIGHT_TOP_PROFILE = RIGHT_KEYMAP_PROFILE
KEYCAP_CLEARANCE = 0.5
LEFT_KEYCAP_ENVELOPE = unary_union(
    [key_cell_mm(k) for k in KEYS if k["half"] == "L"]).buffer(
        KEYCAP_CLEARANCE, join_style=2)
RIGHT_KEYCAP_ENVELOPE = unary_union(
    [key_cell_mm(k) for k in KEYS if k["half"] == "R"]).buffer(
        KEYCAP_CLEARANCE, join_style=2)
LEFT_KEYCAP_ENVELOPE = translate(
    LEFT_KEYCAP_ENVELOPE, xoff=half_spread("L"))
RIGHT_KEYCAP_ENVELOPE = translate(
    RIGHT_KEYCAP_ENVELOPE, xoff=half_spread("R"))
LEFT_GASKET_TABS = gasket_tabs(LEFT_PLATE_BODY, "L")
RIGHT_GASKET_TABS = gasket_tabs(RIGHT_PLATE_BODY, "R")

PLATE_EDGE_RADIUS = 1.0


def round_plate_edges(poly, radius=PLATE_EDGE_RADIUS):
    """Round material-side corners on the completed plate exterior.

    Switch and stabilizer openings are emitted later as independent DXF
    contours, so this operation affects only the perimeter and integral gasket
    tongues.  The opening operation rounds convex corners without filling the
    intended concave transitions at the tongue roots.
    """
    rounded = poly.buffer(-radius, join_style=1, quad_segs=16).buffer(
        radius, join_style=1, quad_segs=16)
    rounded = rounded.simplify(0.0001, preserve_topology=True)
    if rounded.geom_type != "Polygon" or not rounded.is_valid:
        raise RuntimeError("1 mm plate edge rounding did not produce one valid outline")
    return rounded


LEFT_PLATE = round_plate_edges(
    unary_union([LEFT_PLATE_BODY] + LEFT_GASKET_TABS))
RIGHT_PLATE = round_plate_edges(
    unary_union([RIGHT_PLATE_BODY] + RIGHT_GASKET_TABS))

# The split plates are independently gasket-mounted and must never become a
# rigid bridge at their symmetric inner suspension tongues.
if LEFT_PLATE.intersects(RIGHT_PLATE):
    raise RuntimeError("left/right plate outlines intersect at inner gasket mounts")
if LEFT_PLATE.distance(RIGHT_PLATE) < 0.45:
    raise RuntimeError("inner gasket mount clearance is below 0.45 mm")

# Recovered keymap-following PCB contours from the final routed two-layer
# candidate.  Keep these explicit: rebuilding from CASE_IN's convex hull is
# what accidentally erased the sculpted perimeter.  Only the four-point U
# recess on each half is filled below.
LEFT_PCB_BASE = Polygon([
    (-7.7153,55.1500),(-7.7153,81.1750),(-2.9530,81.1750),
    (-2.9530,97.2500),(58.1980,97.2500),(58.1980,78.2011),
    (69.0157,78.2067),(68.4268,97.1781),(98.5295,98.1125),
    (98.2339,100.9468),(144.8435,105.8087),(147.5435,79.9241),
    (137.6242,78.8894),(138.8023,68.5000),(151.2090,68.5000),
    (151.2090,43.5000),(148.4525,43.5000),(150.2090,28.0837),
    (150.2090,23.0908),(140.7219,22.0098),(142.8646,3.2038),
    (121.6741,0.7894),(121.6768,0.7589),(120.5041,0.6561),
    (119.9628,0.5944),(119.9611,0.6085),(100.2172,-1.1231),
    (100.2180,-1.1442),(99.7896,-1.1606),(98.7149,-1.2548),
    (98.7103,-1.2017),(80.1514,-1.9098),(80.1515,-1.9554),
    (78.8857,-1.9581),(77.1848,-2.0230),(77.1824,-1.9618),
    (61.0550,-1.9961),(61.0550,-2.0000),(59.2215,-2.0000),
    (57.1016,-2.0045),(57.1016,-2.0000),(-0.0950,-2.0000),
    (-0.0950,17.0500),(-1.9995,17.0500),(-1.9995,36.1000),
    (-2.9527,36.1000),(-2.9527,55.1500)])
RIGHT_PCB_BASE = Polygon([
    (152.2090,22.8197),(152.2090,46.0188),(152.2090,68.5000),
    (161.2367,68.5000),(162.4150,78.8912),(152.4935,79.9261),
    (155.1935,105.8107),(201.8031,100.9488),(201.5072,98.1116),
    (231.6102,97.1771),(231.0214,78.2067),(241.8395,78.2011),
    (241.8395,97.2500),(302.9905,97.2500),(302.9905,81.1750),
    (307.7523,81.1750),(307.7523,55.1500),(302.9898,55.1500),
    (302.9898,36.1000),(302.0375,36.1000),(302.0375,17.0500),
    (300.1330,17.0500),(300.1330,-2.0000),(242.9364,-2.0000),
    (242.9364,-2.0045),(240.8165,-2.0000),(238.9830,-2.0000),
    (238.9830,-1.9961),(222.8565,-1.9618),(222.8542,-2.0220),
    (221.1811,-1.9582),(219.8865,-1.9554),(219.8866,-1.9088),
    (201.3269,-1.2007),(201.3221,-1.2558),(200.2055,-1.1579),
    (199.8210,-1.1432),(199.8217,-1.1242),(180.0757,0.6075),
    (180.0742,0.5944),(179.5711,0.6517),(178.3602,0.7579),
    (178.3630,0.7894),(157.1724,3.2038),(159.3151,22.0101)])
LEFT_PCB_NOTCH_FILL = Polygon([(58.1980,97.2500),(58.1980,78.2011),
                               (69.0157,78.2067),(68.4268,97.1781)])
RIGHT_PCB_NOTCH_FILL = Polygon([(231.6102,97.1771),(231.0214,78.2067),
                                (241.8395,78.2011),(241.8395,97.2500)])
PCB_EDGE_RADIUS = 1.0


def round_pcb_outer_corners(poly, radius=PCB_EDGE_RADIUS):
    """Apply a fabrication-quality radius to the PCB's convex perimeter.

    The erosion/dilation pair is a geometric opening: it rounds material-side
    outside corners without filling the intentional keymap-following concave
    steps.  Sixty-four points per circle keeps the line approximation below
    normal PCB-plotter resolution while retaining compatibility with the
    existing gr_line-only outline and validation tooling.
    """
    rounded = poly.buffer(-radius, join_style=1, quad_segs=16).buffer(
        radius, join_style=1, quad_segs=16)
    # Remove numerical micro-segments produced where a rounded buffer meets
    # nearly collinear recovered outline vertices.  The 0.1 um tolerance is
    # far below fabrication resolution but avoids malformed-outline warnings.
    rounded = rounded.simplify(0.0001, preserve_topology=True)
    if rounded.geom_type != "Polygon" or not rounded.is_valid:
        raise RuntimeError("1 mm PCB edge rounding did not produce one valid outline")
    return rounded


LEFT_PCB_REQUIRED = unary_union([LEFT_PCB_BASE, LEFT_PCB_NOTCH_FILL])
RIGHT_PCB_REQUIRED = unary_union([RIGHT_PCB_BASE, RIGHT_PCB_NOTCH_FILL])
# The universal right half has a few extra alternative-layout positions. Use
# the union of both required envelopes as one half-template, then mirror it.
# This preserves every required drill/component while making the finished PCB
# edges exactly symmetric about the keyboard's tent axis.
LEFT_PCB_UNROUNDED = unary_union([
    LEFT_PCB_REQUIRED,
    scale(RIGHT_PCB_REQUIRED, xfact=-1, yfact=1, origin=(axis_mm, 0)),
])
LEFT_PCB = round_pcb_outer_corners(LEFT_PCB_UNROUNDED)
RIGHT_PCB = scale(LEFT_PCB, xfact=-1, yfact=1, origin=(axis_mm, 0))
RIGHT_PCB_UNROUNDED = scale(
    LEFT_PCB_UNROUNDED, xfact=-1, yfact=1, origin=(axis_mm, 0))

# Compact mixed-side controller daughterboard. The routed core fits in
# 55 x 28 mm. An extra 1.0 mm at each short side lets the two C20111 cable
# mouths face outward while retaining the full hold-down lands and 0.25 mm
# copper-edge clearance.
DB_W, DB_H = 57.0, 28.0
top = CASE_IN.bounds[1]
# Keep the complete controller on the right side of the hinge so its two plate
# screws cannot turn the split plates into a rigid bridge.
DB_REAR_Y = top + 1.0
DB_USB_OVERHANG = 1.0
DB_USB_CENTRE_X = axis_mm + 3.5 + 37.5
DB_USB_NOTCH_HALF_WIDTH = 7.0
DB_BASE = box(axis_mm + 3.5, DB_REAR_Y,
              axis_mm + 3.5 + DB_W, DB_REAR_Y + DB_H)
# Set back only the edge underneath the 9.1 mm-wide USB-C shell.  The 14 mm
# opening leaves generous side clearance while allowing the connector mouth to
# project 1.0 mm beyond its local PCB edge, like the unified daughterboard.
DB_USB_NOTCH = box(DB_USB_CENTRE_X - DB_USB_NOTCH_HALF_WIDTH, DB_REAR_Y,
                   DB_USB_CENTRE_X + DB_USB_NOTCH_HALF_WIDTH,
                   DB_REAR_Y + DB_USB_OVERHANG)
DB = round_pcb_outer_corners(DB_BASE.difference(DB_USB_NOTCH))

# The USB-C receptacle does not sit on the board's centre line: it goes beside
# the MCU's USB pins, which are on that package's right-hand side.  Both the
# board keep-out and the case cutout are placed from this one number.
USB_X_OFF = 9.0

if __name__ == "__main__":
    for nm, p in (("case outer", CASE_OUT), ("case inner", CASE_IN),
                  ("left PCB", LEFT_PCB), ("right PCB", RIGHT_PCB),
                  ("left plate", LEFT_PLATE), ("right plate", RIGHT_PLATE),
                  ("daughterboard", DB)):
        bb = p.bounds
        print("%-14s %7.1f x %6.1f mm   area %7.1f cm2   x %.1f..%.1f  y %.1f..%.1f"
              % (nm, bb[2]-bb[0], bb[3]-bb[1], p.area/100, bb[0], bb[2], bb[1], bb[3]))
    print("centre axis x = %.2f mm" % axis_mm)
    print("left/right PCBs overlap DB area:",
          LEFT_PCB.intersects(DB) or RIGHT_PCB.intersects(DB))
