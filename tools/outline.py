"""Board and plate outlines, in millimetres, KiCad orientation (y down)."""
import math, json
from pathlib import Path
from shapely.geometry import Polygon, box, MultiPolygon, LineString
from shapely.affinity import scale, translate
from shapely.ops import polygonize, unary_union
from geom import KEYS, U, AXIS

WALL      = 6.0     # room for the gasket ledge and M2 frame fasteners
BEZEL     = 0.46 * U   # key field -> case inner edge, as the renders use
PCB_GAP   = 2.0     # clearance between the two half PCBs
PCB_INSET = 1.2     # PCB edge inside the case inner wall
PLATE_OVERHANG = 2.0  # nominal plate rim before discrete FN40-style tabs

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
                    root_half_span=7.0, bearing_half_span=5.0):
    """Create a side tongue with curved, tapered roots.

    The two cubic shoulders leave a continuous vertical plate edge tangentially,
    ease out to the 5 mm projection, and meet its support face tangentially.
    This removes both the square outer corners and the small 90-degree steps at
    the root while preserving a parallel Poron-bearing section.  The default
    dimensions reproduce the short, smooth tongue used by the last complete
    plate revision. Optional spans remain available for future prototypes.
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

    # Sink the root 0.5 mm into the plate so tangent approximation and floating
    # point tolerances cannot leave a detached island.
    shoulder_half_span = bearing_half_span + 1.0
    root_shoulder = root_half_span - 1.0
    projection = GASKET_PROJECTION
    top = bezier(local(-0.5, -root_half_span),
                 local(-0.5, -root_shoulder),
                 local(projection, -shoulder_half_span),
                 local(projection, -bearing_half_span))
    bottom = bezier(local(projection, bearing_half_span),
                    local(projection, shoulder_half_span),
                    local(-0.5, root_shoulder),
                    local(-0.5, root_half_span))
    return Polygon(top + [local(projection, bearing_half_span)] + bottom +
                   [local(-0.5, -root_half_span)])


def _gasket_tabs_direct(poly, half):
    """Two short mounts on each outer and centre-facing plate edge.

    Across the assembled keyboard this produces eight locations: four on the
    outer edges and four on the interior edges. All eight use the same short,
    smooth, tapered tongue from the last complete plate revision. The two
    interior stations are deliberately placed on the new continuous straight
    wall closest to the split axis. The tabs are integral to the plate only;
    gasket compression never loads the Hall-effect PCBs directly.
    """
    _, y0, _, y1 = poly.bounds
    outer_left = half == "L"
    inner_left = not outer_left
    tabs = []
    # Keep the full 14 mm tongue on the uninterrupted straight outside wall.
    for fraction in (0.18, 0.82):
        y = y0 + (y1 - y0) * fraction
        x = edge_x(poly, y, left=outer_left)
        tabs.append(smooth_side_tab(x, y, left=outer_left))
    # Put the interior pair directly on the continuous centre-facing wall.
    for fraction in (0.34, 0.82):
        y = y0 + (y1 - y0) * fraction
        x = edge_x(poly, y, left=inner_left)
        sample = 2.0
        slope = ((edge_x(poly, y + sample, left=inner_left) -
                  edge_x(poly, y - sample, left=inner_left)) /
                 (2.0 * sample))
        tab = smooth_side_tab(x, y, left=inner_left, dx_dy=slope)
        if half == "L":
            tab = tab.intersection(box(-1e4, -1e4, axis_mm - 1.0, 1e4))
        else:
            tab = tab.intersection(box(axis_mm + 1.0, -1e4, 1e4, 1e4))
        tabs.append(tab)
    return tabs


def gasket_tabs(poly, half):
    """Return four tabs, mirroring the right set from the left construction."""
    if half == "L":
        return _gasket_tabs_direct(poly, half)
    if half != "R":
        raise ValueError("plate half must be L or R")
    left_poly = scale(poly, xfact=-1.0, yfact=1.0,
                      origin=(axis_mm, 0.0))
    return [scale(tab, xfact=-1.0, yfact=1.0,
                  origin=(axis_mm, 0.0))
            for tab in _gasket_tabs_direct(left_poly, "L")]

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
PLATE_EDGE_RADIUS = 1.0
GASKET_PROJECTION = 5.0
# Nominal Cherry-profile keycaps are smaller than the 19.05 mm switch pitch.
# Keep every ordinary plate wall under that visible keycap skirt.  Only the
# explicit gasket tongues added after this body is built may project beyond it.
PLATE_KEYCAP_INSET = 0.50
# Extend the outer rail far enough to retain at least 2.0 mm of finished POM
# around the closest stabilizer opening. The 12 mm centre root gap plus the two
# 5 mm tongues preserves the previous nominal 2 mm tip-to-tip tent gap.
PLATE_OUTER_WALL_X = -2.10
PLATE_INNER_WALL_GAP = 12.0
# The plate follows the routed PCB Edge.Cuts everywhere except the two
# straight side rails that carry the gasket tongues.  A 0.26 mm normal offset
# is the smallest rounded value that retains the conservative 2.0 mm POM web
# around the closest stabilizer opening when the plate is derived directly
# from the routed PCB Edge.Cuts.
PLATE_PCB_FOLLOW_MARGIN = 0.26
# The PCB-mounted spacebar stabilizers sit unusually close to the swept lower
# edge.  Use the actual rotated spacebar cell for their local reinforcement
# instead of the former axis-aligned rectangular shelf.  A 0.05 mm inset keeps
# the ordinary support inside the nominal key cell while retaining at least
# 2.0 mm of finished POM around the stabilizer openings.  Most importantly,
# its lower wall is exactly parallel to the 9-degree spacebar/keycap edge.
PLATE_SPACEBAR_SUPPORT_INSET = 0.05
# The extension must carry the complete rotated strip—not only its leading
# corner—to the straight wall on both asymmetric halves.  It is clipped at the
# wall datum below, so the extra overlap cannot reduce the centre gap.
PLATE_SPACEBAR_INNER_EXTENSION = 8.0


def spacebar_plate_support(half):
    spaces = [key for key in KEYS
              if key["half"] == half and key["label"] == "Space"]
    if len(spaces) != 1:
        raise RuntimeError(f"expected one {half} spacebar key")
    space = spaces[0]
    support = key_cell_mm(space).buffer(
        -PLATE_SPACEBAR_SUPPORT_INSET, join_style=2)

    # Continue the same rotated profile through the short centre-wall
    # transition.  Previously the straight wall's horizontal lower edge met
    # the rotated support just before its end, leaving a small mirrored hook on
    # both halves.  A translated overlap carries the angled edge cleanly to the
    # wall datum; clipping there preserves the exact 12 mm centre root gap.
    direction = 1.0 if half == "L" else -1.0
    angle = math.radians(space["rot"])
    support = unary_union([
        support,
        translate(
            support,
            xoff=direction * PLATE_SPACEBAR_INNER_EXTENSION * math.cos(angle),
            yoff=direction * PLATE_SPACEBAR_INNER_EXTENSION * math.sin(angle),
        ),
    ])
    inner_line = (axis_mm - PLATE_INNER_WALL_GAP / 2.0 if half == "L" else
                  axis_mm + PLATE_INNER_WALL_GAP / 2.0)
    limit = (box(-1e4, -1e4, inner_line, 1e4) if half == "L" else
             box(inner_line, -1e4, 1e4, 1e4))
    return support.intersection(limit)


PLATE_SPACEBAR_SUPPORT = {
    half: spacebar_plate_support(half) for half in ("L", "R")
}


def alt_plate_support(half):
    """Retain the full key-cell edge around the standardized bottom Alt."""
    alts = [key for key in KEYS
            if key["half"] == half and key["label"] == "Alt"]
    if len(alts) != 1:
        raise RuntimeError(f"expected one {half} Alt key")
    return key_cell_mm(alts[0])


PLATE_ALT_SUPPORT = {
    half: alt_plate_support(half) for half in ("L", "R")
}
PLATE_BACKSPACE_SUPPORT = {
    "L": Polygon(),
    "R": box(260.0, 0.20, 298.0, 22.0),
}


def round_plate_edges(poly, radius=PLATE_EDGE_RADIUS):
    """Round material-side corners on the completed plate exterior.

    Switch and stabilizer openings are emitted later as independent DXF
    contours, so this operation affects only the perimeter and integral gasket
    tongues.  The opening operation rounds convex corners without filling the
    intended concave transitions at the tongue roots.
    """
    # Gasket tongues can wrap a concave, rotated edge closely enough for their
    # boolean union to enclose a sub-square-millimetre root pocket.  The plate
    # exterior has no intentional holes at this stage; real fabrication
    # openings are emitted later on dedicated DXF layers.
    if poly.geom_type == "Polygon" and poly.interiors:
        poly = Polygon(poly.exterior)
    rounded = poly.buffer(-radius, join_style=1, quad_segs=16).buffer(
        radius, join_style=1, quad_segs=16)
    # 0.01 mm removes buffer-generated micro-segments that showed as staircase
    # pixels in previews while remaining far below machining tolerance.
    rounded = rounded.simplify(0.01, preserve_topology=True)
    if rounded.geom_type != "Polygon" or not rounded.is_valid:
        raise RuntimeError("1 mm plate edge rounding did not produce one valid outline")
    return rounded


def keycap_plate_envelope(keys):
    """Convex perimeter of the physical keycap skirts, not the switch pitch."""
    cap_cells = [key_cell_mm(key).buffer(-PLATE_KEYCAP_INSET, join_style=2)
                 for key in keys]
    return unary_union(cap_cells).convex_hull


def keycap_core_plate(keys):
    """One-piece structural core bounded by the outer keycap envelope.

    Each nominal 19.05 mm key cell is inset before taking the envelope.  Using
    that envelope directly removes the small row-to-row shelves left by the
    former morphological close and fills the two non-switch blocker bays
    between the outer and angled key clusters.  Actual switch, stabilizer and
    M2 apertures are still emitted separately and subtracted from this solid
    core, so the smoother perimeter cannot close a valid opening.
    """
    cells = unary_union([
        key_cell_mm(key).buffer(-PLATE_KEYCAP_INSET, join_style=2)
        for key in keys
    ])
    bounded = cells.convex_hull.buffer(0)
    # The reduced cap cells can leave a small enclosed inter-key ring after the
    # close.  It is structural plate material, not an intentional aperture;
    # all real switch, stabilizer and M2 openings are emitted on their own DXF
    # layers later.
    if bounded.geom_type == "Polygon" and bounded.interiors:
        bounded = Polygon(bounded.exterior)
    if bounded.geom_type != "Polygon" or not bounded.is_valid:
        raise RuntimeError("keycap-bounded plate did not produce one polygon")
    return round_plate_edges(bounded)


def straight_gasket_walls(poly, half):
    """Replace the four stepped side regions with straight gasket walls.

    The outside walls sit at the straight gasket datum (and its exact mirror),
    leaving at least 2 mm around the outer stabilizer. The centre-facing walls
    are symmetric about the split axis with a 12 mm root-to-root gap. Each
    rectangular rail spans only the real top/bottom intersections of material
    10 mm inboard, avoiding artificial feet beyond the swept key field.
    """
    outer_line = (PLATE_OUTER_WALL_X if half == "L" else
                  2.0 * axis_mm - PLATE_OUTER_WALL_X)
    inner_line = (axis_mm - PLATE_INNER_WALL_GAP / 2.0 if half == "L" else
                  axis_mm + PLATE_INNER_WALL_GAP / 2.0)
    def inner_wall_bottom(inner_inboard, inner_line, body_direction):
        """Continue the swept spacebar edge cleanly to the centre wall.

        A rectangular centre rail ended the nine-degree lower perimeter in a
        short flat shelf.  The rounded PCB support then protruded just beyond
        that shelf, producing the tiny rise-and-drop visible in the plate
        preview.  Extend the established lower-edge slope to the wall datum
        so the support and rail share one monotonic fabrication edge.
        """
        sample = 2.0
        body_x = inner_inboard + body_direction * sample
        source_y = edge_y(poly, inner_inboard, top=False)
        body_y = edge_y(poly, body_x, top=False)
        slope = (source_y - body_y) / (inner_inboard - body_x)
        return source_y + slope * (inner_line - inner_inboard)

    if half == "L":
        # Remove the former rotated/stepped material beyond the red-line outer
        # datum, and clip the centre side to its wall datum, before adding one
        # continuous bearing rail on each side.  Clipping both datums prevents
        # a convex keycap envelope from crossing behind the centre wall and
        # splitting its otherwise continuous straight boundary.
        clipped = poly.intersection(
            box(outer_line, -1e4, inner_line, 1e4))
        outer_inboard = outer_line + 10.0
        inner_inboard = min(poly.bounds[2] - 10.0, inner_line - 1.0)
        outer_wall = box(outer_line, edge_y(poly, outer_inboard, top=True),
                         outer_inboard, edge_y(poly, outer_inboard, top=False))
        inner_top = edge_y(poly, inner_inboard, top=True)
        inner_bottom = edge_y(poly, inner_inboard, top=False)
        wall_bottom = inner_wall_bottom(inner_inboard, inner_line, -1.0)
        inner_wall = Polygon(((inner_inboard,
                               inner_top),
                              (inner_line, inner_top),
                              (inner_line, wall_bottom),
                              (inner_inboard, inner_bottom)))
    else:
        clipped = poly.intersection(
            box(inner_line, -1e4, outer_line, 1e4))
        outer_inboard = outer_line - 10.0
        inner_inboard = max(poly.bounds[0] + 10.0, inner_line + 1.0)
        outer_wall = box(outer_inboard, edge_y(poly, outer_inboard, top=True),
                         outer_line, edge_y(poly, outer_inboard, top=False))
        inner_top = edge_y(poly, inner_inboard, top=True)
        inner_bottom = edge_y(poly, inner_inboard, top=False)
        wall_bottom = inner_wall_bottom(inner_inboard, inner_line, 1.0)
        inner_wall = Polygon(((inner_line, inner_top),
                              (inner_inboard,
                               inner_top),
                              (inner_inboard, inner_bottom),
                              (inner_line, wall_bottom)))
    merged = unary_union([clipped, outer_wall, inner_wall]).buffer(0)
    if merged.geom_type == "Polygon" and merged.interiors:
        merged = Polygon(merged.exterior)
    if merged.geom_type != "Polygon" or not merged.is_valid:
        raise RuntimeError("straight gasket walls did not produce one plate body")

    return merged


def _unsymmetrized_keycap_bounded_plate(keys):
    """Build one half before the two supported envelopes are symmetrized."""
    core = keycap_core_plate(keys)
    half = keys[0]["half"]
    if any(key["half"] != half for key in keys):
        raise RuntimeError("plate keys must all belong to the same half")
    core = unary_union([core, PLATE_SPACEBAR_SUPPORT[half],
                        PLATE_BACKSPACE_SUPPORT[half]]).buffer(0)
    return straight_gasket_walls(core, half)


_PCB_FOLLOWING_PLATE_BODIES = None


def pcb_following_plate_bodies():
    """Return plate bodies that track the PCB except at gasket side walls.

    The routed PCB outline is expanded by only the POM web allowance.  The
    existing straight outer and centre-facing rails then replace the PCB's
    stepped side edges so the four gasket tongues retain clean compression
    datums.  The completed right body is mirrored from the left source to keep
    the exterior pair exactly symmetric.

    This function is called only after LEFT_PCB_ENCLOSURE has been built near
    the end of the module.
    """
    global _PCB_FOLLOWING_PLATE_BODIES
    if _PCB_FOLLOWING_PLATE_BODIES is None:
        # The routed masters are the mechanical authority at release time.
        # Reading their line-only Edge.Cuts here prevents a hand-finished PCB
        # perimeter from drifting away from regenerated plate DXFs.  During an
        # initial source-only generation (before a routed board exists), fall
        # back to the analytic enclosure.
        board_path = Path(__file__).resolve().parents[1] / \
            "pcb/Symm60HE-Left.kicad_pcb"
        left_board = None
        if board_path.is_file():
            from sexp import find, first, loads
            board = loads(board_path.read_text())
            edges = []
            for item in find(board, "gr_line"):
                layer = first(item, "layer")
                if not layer or str(layer[1]) != "Edge.Cuts":
                    continue
                start, end = first(item, "start"), first(item, "end")
                edges.append(LineString((
                    (float(start[1]), float(start[2])),
                    (float(end[1]), float(end[2])),
                )))
            polygons = list(polygonize(edges))
            if len(polygons) != 1:
                raise RuntimeError("routed left PCB Edge.Cuts are not one polygon")
            left_board = polygons[0]
        left_pcb_profile = (left_board or LEFT_PCB_ENCLOSURE).buffer(
            PLATE_PCB_FOLLOW_MARGIN, join_style=2)
        left = straight_gasket_walls(left_pcb_profile, "L")
        right = scale(left, xfact=-1.0, yfact=1.0,
                      origin=(axis_mm, 0.0))
        if (left.geom_type != "Polygon" or not left.is_valid or
                right.geom_type != "Polygon" or not right.is_valid):
            raise RuntimeError("PCB-following plate body is not one valid polygon")
        _PCB_FOLLOWING_PLATE_BODIES = {"L": left, "R": right}
    return _PCB_FOLLOWING_PLATE_BODIES


def symmetric_plate_bodies():
    """Compatibility alias for the exact mirrored PCB-following pair."""
    return pcb_following_plate_bodies()


def keycap_bounded_plate(keys):
    """Shared PCB-following body with four deliberate gasket-wall rails."""
    if not keys:
        raise RuntimeError("plate requires at least one key")
    half = keys[0]["half"]
    if any(key["half"] != half for key in keys):
        raise RuntimeError("plate keys must all belong to the same half")
    return pcb_following_plate_bodies()[half]


def inboard_gasket_pads(poly, half):
    """Four Poron contact pads placed inside, rather than beyond, the plate."""
    _, y0, _, y1 = poly.bounds
    inset = poly.buffer(-0.45, join_style=2)
    pads = []
    for left, fraction in (((half == "L"), 0.27),
                           ((half == "L"), 0.66),
                           ((half != "L"), 0.32),
                           ((half != "L"), 0.68)):
        y = y0 + (y1 - y0) * fraction
        x = edge_x(inset, y, left=left)
        candidate = (box(x, y - 4.0, x + 2.6, y + 4.0) if left else
                     box(x - 2.6, y - 4.0, x, y + 4.0))
        clipped = candidate.intersection(inset)
        if clipped.geom_type == "MultiPolygon":
            clipped = max(clipped.geoms, key=lambda part: part.area)
        if (clipped.geom_type != "Polygon" or clipped.area < 12.0 or
                clipped.difference(poly).area > 1e-6):
            raise RuntimeError("inboard gasket pad does not fit plate")
        pads.append(clipped)
    return pads


PCB_EDGE_RADIUS = 1.0
PCB_KEYCAP_INSET = 0.5
PCB_PROFILE_CLOSE = 0.5
SPACEBAR_DRILL_EDGE_CLEARANCE = 1.35

# Global drill centres and finished diameters after flipping the universal 3u
# spacebar stabilizers SL2/SR3 by 180 degrees.  Their larger holes now face the
# PCB interior and the smaller holes face the lower edge.
SPACEBAR_STABILIZER_DRILLS = {
    "L": (
        (130.817170, 100.649151, 3.0480),
        (133.201231, 85.596781, 3.9878),
        (107.297841, 96.924055, 3.0480),
        (109.681902, 81.871685, 3.9878),
    ),
    "R": (
        (192.739159, 96.924055, 3.0480),
        (190.355098, 81.871685, 3.9878),
        (169.219830, 100.649151, 3.0480),
        (166.835769, 85.596781, 3.9878),
    ),
}

# Straight shelves replace the old per-hole circular lobes.  Each rectangle
# includes the complete flipped drill envelope plus 1.35 mm before the final
# 1 mm corner-rounding pass, leaving at least 1.0 mm finished clearance.
SPACEBAR_EDGE_SUPPORT = {
    "L": box(104.40, 79.0, 136.60, 103.55),
    "R": box(163.45, 79.0, 195.65, 103.55),
}


def compact_drill_support(half):
    """Square, local edge support around each finished stabilizer drill."""
    pads = []
    for x, y, diameter in SPACEBAR_STABILIZER_DRILLS[half]:
        # Add 0.05 mm so the later radius/simplification pass cannot erode the
        # nominal 1.35 mm finished clearance by a few microns.
        reach = diameter / 2.0 + SPACEBAR_DRILL_EDGE_CLEARANCE + 0.05
        pads.append(box(x - reach, y - reach, x + reach, y + reach))
    return unary_union(pads)


COMPACT_SPACEBAR_EDGE_SUPPORT = {
    half: compact_drill_support(half) for half in ("L", "R")
}

# Cut between the FPC support and the spacebar.  The short rail beneath the
# connector is horizontal.  The lower shelf at the top of the spacebar tab is
# independently aligned with the 9-degree lower spacebar perimeter.  Keeping
# those two rules separate prevents changes to the spacebar wall from tilting
# the FPC wall again.  The interior segments retain the compact pocket and the
# outer/lower segment rejoins the swept bottom edge without the former
# backtracking vertex that produced a small bump.
SPACEBAR_SIDE_UPPER = (144.009, 70.5)
SPACEBAR_NOTCH_TOP_INNER_X = 131.59403971
SPACEBAR_NOTCH_TOP_ANGLE_DEG = next(
    key["rot"] for key in KEYS
    if key["half"] == "L" and key["label"] == "Space"
)
SPACEBAR_NOTCH_TOP_SLOPE = math.tan(
    math.radians(SPACEBAR_NOTCH_TOP_ANGLE_DEG))
# Shared 0.1 um manufacturing-grid direction used for both finished parallel
# Edge.Cuts segments.  749 / 4729 is 8.99999978 degrees; using integer
# multiples guarantees that KiCad's four-decimal serialization cannot give
# the top and bottom lines slightly different slopes.
SPACEBAR_PARALLEL_GRID_VECTOR = (0.4729, 0.0749)
SPACEBAR_SHELF_VECTOR_MULTIPLE = 15
SPACEBAR_BOTTOM_VECTOR_MULTIPLE = 137
SPACEBAR_NOTCH_TOP_INNER = (
    SPACEBAR_NOTCH_TOP_INNER_X,
    SPACEBAR_SIDE_UPPER[1],
)
SPACEBAR_NOTCH_BOTTOM_INNER = (131.59403971, 82.0)
SPACEBAR_NOTCH_BOTTOM_OUTER_X = 141.78436881
SPACEBAR_NOTCH_BOTTOM_OUTER = (
    SPACEBAR_NOTCH_BOTTOM_OUTER_X,
    SPACEBAR_NOTCH_BOTTOM_INNER[1] +
    (SPACEBAR_NOTCH_BOTTOM_OUTER_X - SPACEBAR_NOTCH_BOTTOM_INNER[0]) *
    SPACEBAR_NOTCH_TOP_SLOPE,
)
SPACEBAR_BOTTOM_EDGE_START = (72.918, 94.75)
SPACEBAR_SIDE_LOWER_SOURCE_JOIN = (139.41273053209386, 104.07625617024446)
SPACEBAR_SIDE_LOWER_JOIN = (
    SPACEBAR_SIDE_LOWER_SOURCE_JOIN[0],
    SPACEBAR_BOTTOM_EDGE_START[1] +
    (SPACEBAR_SIDE_LOWER_SOURCE_JOIN[0] - SPACEBAR_BOTTOM_EDGE_START[0]) *
    SPACEBAR_NOTCH_TOP_SLOPE,
)

# A single inherited key-cell-union vertex reversed 0.93 mm into the board
# between two otherwise collinear points on the swept bottom edge.  Removing
# it eliminates the small triangular bump without changing the intended edge
# angle or any component clearance.
BOTTOM_EDGE_SPIKE = (98.0656, 97.5275)

# Broad, mirrored shoulders matching the older PCB construction, inset 8 mm
# farther into each half so they read as part of the main board instead of a
# centre-seam appendage.  The cable-facing edge still extends 0.8 mm past the
# connector courtyard, while the inward side overlaps the keycap body broadly.
FPC_EDGE_SUPPORT = {
    # Mirror of the right support about the physical FPC/courtyard centreline
    # at X=152.209 mm.  The connector courtyard extents mirror about the same
    # line even though the footprint origins themselves are asymmetric.
    "L": box(130.418, 45.5, 144.009, 70.5),
    "R": box(160.409, 45.5, 174.0, 70.5),
}

# The universal bottom rows contain mutually exclusive footprint groups.  A
# literal union leaves a deep rectangular bite between those groups even
# though no assembled layout has an empty bay there.  These bridges stop at
# the neighbouring 1u-row edge, preserving the bottom-row steps instead of
# replacing the complete lower perimeter with a convex rail.
BOTTOM_LAYOUT_BRIDGE = {
    "L": box(55.0, 74.0, 71.0, 94.75),
    "R": box(227.5, 74.0, 245.0, 94.75),
}

# The former reference-style silhouette added a 2 mm strip outside the
# key-cell envelope to make room for the north-facing RGB footprints.  Those
# perimeter LEDs now move toward their Hall sensors, so the extra strip is no
# longer required.
PCB_TOP_EDGE_EXTENSION = 0.0
PCB_TOP_EXTENSION_DEPTH = 14.0
PCB_ENCLOSURE_TRANSITION_RADIUS = 1.75

# Right-half coordinates reconstructed from the user's black lower-edge sketch.
# The left half is generated only by mirroring this result.  The slightly lower
# middle point keeps the drawn diagonal outside both finished stabilizer drills
# rather than tracing through their required 1.35 mm edge-clearance envelope.
DRAWN_BOTTOM_OUTER = (156.0, 77.0)
# This is the shallowest mirrored lower corner that retains more than 1.0 mm
# of finished laminate outside every flipped 3u stabilizer drill after the
# 1.75 mm outline-rounding pass.
DRAWN_BOTTOM_CORNER = (160.0, 105.0)
DRAWN_BOTTOM_REJOIN = (229.5, 94.75)

# Three sub-millimetre source-geometry discontinuities visible in the rendered
# outline.  Filling them before the radius pass is cleaner than trying to hide
# them with an oversized global fillet.
SIDE_TRANSITION_FILL = Polygon(((156.8232916791408, 29.6989337731170),
                                (158.409, 45.50),
                                (160.00, 46.00),
                                (160.00, 30.00)))
TOP_TRANSITION_FILL = box(239.50, -1.72, 300.20, 0.00)

# With the routing-oriented standoffs no longer occupying the two outer
# shoulders, retain only the material needed by the stabilizer drills.  The
# SL1 side becomes flush with its neighbouring rail.  The SL2 side follows a
# shallow taper so the lower mounting pad still has more than the 0.5 mm edge
# rule after the final radius pass.  The right PCB receives the exact mirror.
LEFT_STABILIZER_SIDE_RAIL = -0.453
LEFT_LOWER_SHOULDER_MASK = Polygon((
    (-1000.0, -1000.0),
    (1000.0, -1000.0),
    (1000.0, 70.50),
    (144.00, 70.50),
    (143.00, 96.00),
    (143.00, 1000.0),
    (-1000.0, 1000.0),
))


def round_pcb_outer_corners(poly, radius=PCB_EDGE_RADIUS):
    """Apply a fabrication-quality radius to convex and concave corners.

    Closing first rounds the recessed row-step corners shown in the PCB side
    walls; opening then rounds material-side outside corners.  Sixty-four
    points per circle keeps the line approximation below normal PCB-plotter
    resolution while retaining compatibility with the gr_line-only outline.
    """
    rounded = poly.buffer(radius, join_style=1, quad_segs=16).buffer(
        -radius, join_style=1, quad_segs=16)
    rounded = rounded.buffer(-radius, join_style=1, quad_segs=16).buffer(
        radius, join_style=1, quad_segs=16)
    # The key-cell close can leave tiny enclosed voids between universal
    # alternatives.  They are not PCB cutouts; Edge.Cuts emits one solid outer
    # contour, so discard those numerical/inter-key interior rings here too.
    if isinstance(rounded, Polygon):
        rounded = Polygon(rounded.exterior)
    # Remove numerical micro-segments produced where a rounded buffer meets
    # nearly collinear key-cell vertices.  A 0.01 mm tolerance is far below
    # normal routing tolerance while avoiding hundreds of micro-segments.
    rounded = rounded.simplify(0.01, preserve_topology=True)
    if rounded.geom_type != "Polygon" or not rounded.is_valid:
        raise RuntimeError("1 mm PCB edge rounding did not produce one valid outline")
    return rounded


def keycap_inset_pcb(half, spacebar_support=None):
    """PCB body 0.5 mm inside the current tilted keycap-cell envelope.

    The small close/open pair joins coincident universal-layout alternatives
    without taking a convex hull, so the DOE row curvature and stepped sides
    remain visible.  Only the spacebar-stabilizer drill envelopes and compact
    centre-edge FPC neck extend it; other edge hardware stays inside.
    """
    cells = unary_union([key_cell_mm(k) for k in KEYS if k["half"] == half])
    body = cells.buffer(PCB_PROFILE_CLOSE, join_style=2).buffer(
        -(PCB_PROFILE_CLOSE + PCB_KEYCAP_INSET), join_style=2)
    if isinstance(body, MultiPolygon):
        body = max(body.geoms, key=lambda p: p.area)
    fpc = FPC_EDGE_SUPPORT[half]
    support = (SPACEBAR_EDGE_SUPPORT[half] if spacebar_support is None
               else spacebar_support)
    body = unary_union((body, fpc, support))
    if isinstance(body, MultiPolygon):
        raise RuntimeError(f"{half}: edge supports did not join the PCB body")
    return body


def extend_top_edge(poly):
    """Move the complete layout-derived top profile outward uniformly."""
    x0, y0, x1, _ = poly.bounds
    top = poly.intersection(box(x0 - 1.0, y0 - 1.0, x1 + 1.0,
                                y0 + PCB_TOP_EXTENSION_DEPTH))
    return unary_union((poly, translate(top, yoff=-PCB_TOP_EDGE_EXTENSION)))


def mirror_about_layout_axis(poly):
    return scale(poly, xfact=-1.0, yfact=1.0, origin=(axis_mm, 0.0))


def apply_drawn_right_bottom(poly):
    """Replace the lower-left staircase with a parallel-sided trapezoid."""
    outer = DRAWN_BOTTOM_OUTER
    corner = DRAWN_BOTTOM_CORNER
    rejoin = DRAWN_BOTTOM_REJOIN
    # Match the upper edge to the exact vector of the drawn lower edge.  Most
    # of this fourth side is swallowed by the existing board body; the exposed
    # portion removes the former triangular cut without creating a new shelf.
    upper_rejoin = (outer[0] + rejoin[0] - corner[0],
                    outer[1] + rejoin[1] - corner[1])
    trapezoid = Polygon((outer, corner, rejoin, upper_rejoin))
    # Add material out to the sketched outer corner, then clip everything below
    # the outer/corner/rejoin polyline.  X >= rejoin is intentionally unmasked
    # so the rest of the layout-derived lower edge remains unchanged.
    left_mask = Polygon((outer, (outer[0], -1000.0),
                         (rejoin[0], -1000.0), rejoin, corner))
    allowed = unary_union((left_mask,
                           box(rejoin[0], -1000.0, 1000.0, 1000.0)))
    return unary_union((poly, trapezoid)).intersection(allowed)


def clean_right_transition_angles(poly):
    """Remove the shallow side and top kinks before corner rounding."""
    # TOP_TRANSITION_FILL belonged to the superseded 2 mm top extension.  It
    # must not recreate the material deliberately removed above the top row.
    return unary_union((poly, SIDE_TRANSITION_FILL))


def trim_left_stabilizer_shoulders(poly):
    """Remove obsolete outer material while preserving drill clearance."""
    side_rail = box(LEFT_STABILIZER_SIDE_RAIL, -1000.0, 1000.0, 1000.0)
    trimmed = poly.intersection(side_rail).intersection(
        LEFT_LOWER_SHOULDER_MASK)
    if trimmed.geom_type != "Polygon" or not trimmed.is_valid:
        raise RuntimeError("stabilizer-shoulder trim did not produce one outline")
    return trimmed


def trim_left_spacebar_border(poly):
    """Follow the 0.5 mm-inset spacebar cell except at stabilizer drills.

    The former centre-side rail stayed nearly vertical all the way past the
    tilted spacebar, leaving a broad wedge outside the key-cell silhouette.
    Keep the board unrestricted above and to the outside of that cell, then
    use the actual rotated 2.25u cell as the lower centre-side limit.  Compact
    square drill envelopes are the only permitted exception: they retain the
    laminate needed above/below the mutually exclusive 3u stabilizer holes
    without recreating the old full-width shelf.
    """
    spacebar = next(k for k in KEYS
                    if k["half"] == "L" and k["label"] == "Space")
    inset_cell = key_cell_mm(spacebar).buffer(
        -PCB_KEYCAP_INSET, join_style=2)
    x_min, y_min, _, _ = inset_cell.bounds
    unrestricted = unary_union((
        box(-1000.0, -1000.0, 1000.0, y_min + 0.001),
        box(-1000.0, -1000.0, x_min, 1000.0),
    ))
    # The universal stabilizer alternatives are not placed as exact left/right
    # mirrors.  The shared symmetric outline must therefore retain both the
    # left envelopes and the right envelopes mirrored onto the left master.
    # Mirroring this finished master back then clears every drill on both PCBs.
    shared_drill_support = unary_union((
        COMPACT_SPACEBAR_EDGE_SUPPORT["L"],
        mirror_about_layout_axis(COMPACT_SPACEBAR_EDGE_SUPPORT["R"]),
    ))
    # Wrap those local exceptions with straight tangents.  This produces the
    # clean spacebar border in the sketch instead of exposing a series of
    # small rectangular drill-support lobes.
    spacebar_profile = unary_union((
        inset_cell,
        shared_drill_support,
    )).convex_hull
    allowed = unary_union((unrestricted, spacebar_profile))
    trimmed = poly.intersection(allowed)
    if trimmed.geom_type != "Polygon" or not trimmed.is_valid:
        raise RuntimeError("spacebar-border trim did not produce one outline")
    return trimmed


def apply_left_spacebar_cutline(poly):
    """Replace the spacebar-side perimeter with the rectangular cutout."""
    coords = list(poly.exterior.coords)[:-1]

    def nearest(target):
        return min(range(len(coords)),
                   key=lambda index: math.dist(coords[index], target))

    bottom_start = nearest(SPACEBAR_BOTTOM_EDGE_START)
    lower = nearest(SPACEBAR_SIDE_LOWER_SOURCE_JOIN)
    upper = nearest(SPACEBAR_SIDE_UPPER)
    if (math.dist(coords[bottom_start], SPACEBAR_BOTTOM_EDGE_START) > 0.01 or
            math.dist(coords[lower], SPACEBAR_SIDE_LOWER_SOURCE_JOIN) > 0.01 or
            math.dist(coords[upper], SPACEBAR_SIDE_UPPER) > 0.01 or
            not (bottom_start < lower < upper)):
        raise RuntimeError("cannot resolve the spacebar hook anchors")
    replacement = (coords[:bottom_start + 1] +
                   [SPACEBAR_SIDE_LOWER_JOIN,
                    SPACEBAR_NOTCH_BOTTOM_OUTER,
                    SPACEBAR_NOTCH_BOTTOM_INNER,
                    SPACEBAR_NOTCH_TOP_INNER] +
                   coords[upper:])
    cleaned = Polygon(replacement)
    if cleaned.geom_type != "Polygon" or not cleaned.is_valid:
        raise RuntimeError("spacebar cut-line replacement did not produce one outline")
    return cleaned


def remove_left_bottom_edge_spike(poly):
    """Delete the lone reversed vertex on the swept lower perimeter."""
    coords = list(poly.exterior.coords)[:-1]
    spike = min(range(len(coords)),
                key=lambda index: math.dist(coords[index], BOTTOM_EDGE_SPIKE))
    if math.dist(coords[spike], BOTTOM_EDGE_SPIKE) > 0.01:
        # The cleanup point belonged to the former -5 degree Alt / displaced
        # spacebar envelope.  Once the bottom row is put on the same -6/-9
        # degree grid as the rest of the left half, that reversed vertex no
        # longer exists and there is nothing to delete.
        return poly
    cleaned = Polygon(coords[:spike] + coords[spike + 1:])
    if cleaned.geom_type != "Polygon" or not cleaned.is_valid:
        raise RuntimeError("lower-edge spike removal did not produce one outline")
    return cleaned


def enforce_left_fpc_lower_wall_horizontal(poly):
    """Keep the finished rounded wall beneath the FPC exactly horizontal."""
    coords = list(poly.exterior.coords)[:-1]
    candidates = []
    for index, (start, end) in enumerate(zip(coords, coords[1:])):
        length = math.dist(start, end)
        if (length > 5.0 and
                130.0 < start[0] < 145.0 and
                130.0 < end[0] < 145.0 and
                65.0 < start[1] < 75.0 and
                65.0 < end[1] < 75.0):
            candidates.append((length, index))
    if len(candidates) != 1:
        raise RuntimeError("cannot resolve the finished spacebar notch rail")
    _, index = candidates[0]
    end = coords[index + 1]
    coords[index + 1] = (end[0], coords[index][1])
    corrected = Polygon(coords)
    if corrected.geom_type != "Polygon" or not corrected.is_valid:
        raise RuntimeError("horizontal FPC wall produced an invalid outline")
    return corrected


def enforce_left_spacebar_bottom_angle(poly):
    """Keep the finished lower spacebar perimeter at exactly +9 degrees."""
    coords = list(poly.exterior.coords)[:-1]
    candidates = []
    for index, (start, end) in enumerate(zip(coords, coords[1:])):
        length = math.dist(start, end)
        if (length > 20.0 and
                65.0 < start[0] < 145.0 and
                65.0 < end[0] < 145.0 and
                90.0 < start[1] < 110.0 and
                90.0 < end[1] < 110.0):
            candidates.append((length, index))
    if len(candidates) != 1:
        raise RuntimeError("cannot resolve the finished lower spacebar edge")
    _, index = candidates[0]
    start = coords[index]
    coords[index + 1] = (
        start[0] + SPACEBAR_PARALLEL_GRID_VECTOR[0] *
        SPACEBAR_BOTTOM_VECTOR_MULTIPLE,
        start[1] + SPACEBAR_PARALLEL_GRID_VECTOR[1] *
        SPACEBAR_BOTTOM_VECTOR_MULTIPLE,
    )
    corrected = Polygon(coords)
    if corrected.geom_type != "Polygon" or not corrected.is_valid:
        raise RuntimeError("exact-angle lower spacebar edge produced an invalid outline")
    return corrected


def enforce_left_spacebar_shelf_angle(poly):
    """Make the indicated upper ledge parallel to the lower spacebar edge."""
    coords = list(poly.exterior.coords)[:-1]
    candidates = []
    for index, (start, end) in enumerate(zip(coords, coords[1:])):
        length = math.dist(start, end)
        if (length > 5.0 and
                128.0 < start[0] < 145.0 and
                128.0 < end[0] < 145.0 and
                78.0 < start[1] < 88.0 and
                78.0 < end[1] < 88.0):
            candidates.append((length, index))
    if len(candidates) != 1:
        raise RuntimeError("cannot resolve the finished spacebar shelf")
    _, index = candidates[0]
    # The exterior is traversed from the shelf's outer/right endpoint toward
    # its inner/left endpoint, so apply the shared vector in reverse.
    start = coords[index]
    coords[index + 1] = (
        start[0] - SPACEBAR_PARALLEL_GRID_VECTOR[0] *
        SPACEBAR_SHELF_VECTOR_MULTIPLE,
        start[1] - SPACEBAR_PARALLEL_GRID_VECTOR[1] *
        SPACEBAR_SHELF_VECTOR_MULTIPLE,
    )
    corrected = Polygon(coords)
    if corrected.geom_type != "Polygon" or not corrected.is_valid:
        raise RuntimeError("parallel spacebar shelf produced an invalid outline")
    return corrected


def enclosure_required_pcb(half):
    """Per-half material required before enforcing mirrored Edge.Cuts."""
    body = keycap_inset_pcb(half)
    body = unary_union((body, BOTTOM_LAYOUT_BRIDGE[half]))
    return body


def enclosure_style_pcb(half):
    """Uniform-edge, exactly mirrored layout envelope.

    The master left outline is the union of the left-side requirements and a
    mirrored copy of every right-side requirement.  Mirroring that master back
    produces two geometrically symmetric halves while guaranteeing that no
    asymmetric universal-layout option, FPC courtyard, LED, or stabilizer is
    clipped.  The complete top profile is raised uniformly, and the broad
    straight spacebar support keeps the lower stabilizer edge even.
    """
    left_required = enclosure_required_pcb("L")
    right_required_on_left = mirror_about_layout_axis(
        enclosure_required_pcb("R"))
    left_master = unary_union((left_required, right_required_on_left))
    right_master = mirror_about_layout_axis(left_master)
    right_master = apply_drawn_right_bottom(right_master)
    right_master = clean_right_transition_angles(right_master)
    left_body = trim_left_spacebar_border(
        trim_left_stabilizer_shoulders(
            mirror_about_layout_axis(right_master)))
    body = (left_body if half == "L" else
            mirror_about_layout_axis(left_body))
    # Remove the remaining 0.13 mm two-vertex jog where mirrored tilted-row
    # envelopes meet.  The tolerance is well below routing/outline clearance
    # and leaves every intentional layout step intact.
    body = body.simplify(0.15, preserve_topology=True)
    if isinstance(body, MultiPolygon):
        raise RuntimeError(f"{half}: reference-style supports did not join the PCB body")
    return body


LEFT_PCB_UNROUNDED = keycap_inset_pcb("L")
RIGHT_PCB_UNROUNDED = keycap_inset_pcb("R")
LEFT_PCB = round_pcb_outer_corners(LEFT_PCB_UNROUNDED)
RIGHT_PCB = round_pcb_outer_corners(RIGHT_PCB_UNROUNDED)

# Approval-only alternative.  Keeping these separate prevents a visual
# proposal from silently replacing the current placement candidate.
LEFT_PCB_ENCLOSURE_UNROUNDED = enclosure_style_pcb("L")
RIGHT_PCB_ENCLOSURE_UNROUNDED = mirror_about_layout_axis(
    LEFT_PCB_ENCLOSURE_UNROUNDED)
# The standardized bottom row is generated directly from the same -6/-9
# degree key grid used by the rest of the half.  Its envelope no longer needs
# the former coordinate-specific hook, shelf, or spike corrections; applying
# those old fixes would reintroduce the small asymmetric steps they were meant
# to remove.  Round the generated perimeter once, then mirror that finished
# left outline exactly for the right half.
LEFT_PCB_ENCLOSURE = round_pcb_outer_corners(
    LEFT_PCB_ENCLOSURE_UNROUNDED, PCB_ENCLOSURE_TRANSITION_RADIUS)
RIGHT_PCB_ENCLOSURE = mirror_about_layout_axis(LEFT_PCB_ENCLOSURE)

# Build the production plate perimeter only after the routed PCB reference
# outline exists.  The top, bottom, and stepped centre contours now follow the
# PCB; only the straight side rails and their gasket tongues intentionally
# differ.  All layout variants reuse this exterior and change only apertures.
LEFT_PLATE_BODY = keycap_bounded_plate(
    [key for key in KEYS if key["half"] == "L"])
RIGHT_PLATE_BODY = keycap_bounded_plate(
    [key for key in KEYS if key["half"] == "R"])
# Use eight short integral side-suspension mounts on four straight gasket-wall
# rails. They belong to the plate, never to the Hall PCB, so compression cannot
# bend the sensor board.
LEFT_GASKET_TABS = gasket_tabs(LEFT_PLATE_BODY, "L")
RIGHT_GASKET_TABS = gasket_tabs(RIGHT_PLATE_BODY, "R")
LEFT_PLATE = round_plate_edges(
    unary_union([LEFT_PLATE_BODY] + LEFT_GASKET_TABS))
# Mirror the completed, rounded left exterior instead of independently
# buffering the right side.  GEOS can choose slightly different arc
# tessellation vertices for two mathematically mirrored buffer operations;
# mirroring the finished contour guarantees a zero-error fabrication pair.
RIGHT_PLATE = scale(
    LEFT_PLATE, xfact=-1.0, yfact=1.0, origin=(axis_mm, 0.0))


def finished_plate_outline(half):
    if half == "L":
        return LEFT_PLATE
    if half == "R":
        return RIGHT_PLATE
    raise ValueError("plate half must be L or R")

# Compact mixed-side controller daughterboard. The routed core fits in
# 55 x 28 mm. An extra 1.0 mm at each short side lets the two C20111 cable
# mouths face outward while retaining the full hold-down lands and 0.25 mm
# copper-edge clearance.
DB_W, DB_H = 57.0, 28.0
top = CASE_IN.bounds[1]
# Keep the complete controller on the right side of the hinge so its two plate
# screws cannot turn the split plates into a rigid bridge.
DB = round_pcb_outer_corners(
    box(axis_mm + 3.5, top + 1.0, axis_mm + 3.5 + DB_W, top + 1.0 + DB_H))

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
